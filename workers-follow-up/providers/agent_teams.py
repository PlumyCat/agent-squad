#!/usr/bin/env python3
"""Agent Teams provider — reads Claude Code Agent Teams data instead of tmux.

Data sources (all under ~/.claude):
- teams/{team}/config.json   — team membership: members[].{name, agentId, agentType, model, cwd}
- tasks/{team}/*.json        — tasks: {id, subject, description, status, owner, blocks, blockedBy}
- projects/{slug}/{session}/subagents/agent-{id}.jsonl — per-teammate transcripts

A directory under ~/.claude/tasks/ is a *team* only when a matching
~/.claude/teams/{name}/config.json exists. The other task directories are
plain session UUIDs and are ignored here.

The transcript file id is NOT the config.json agentId ("name@team"); it is a
short id assigned inside the JSONL. The reliable way to map a member to its
transcript is the sibling ``agent-{id}.meta.json`` file, whose ``agentType``
field holds the member *name*.

Integration boundaries
-----------------------
Two sibling modules are written in parallel by teammates and imported lazily:

- providers.transcript_logs (nova, task #3)
    read_log_entries(path: str, state: dict | None) -> (entries, new_state)
      entries: list[{"id", "time", "kind", "text"}]  (kind in cmd/info/ok/warn/err/dim)
    Used to turn a teammate transcript JSONL into UI log lines. If absent, a
    minimal inline fallback returns no log lines.

- providers.tasks_map (echo, task #4)
    task_to_ticket(task: dict, *, team: str) -> dict
      returns a UI ticket {id, title, body, status, assigned_to, created_at,
      updated_at, history, comments, labels, priority, linear_url?}
    Used to map an Agent Teams task to a dashboard ticket. If absent, a
    minimal inline fallback performs a basic status/field mapping.

Both are optional: this provider works (with reduced richness) before they land.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


CLAUDE_HOME = Path(os.environ.get("CLAUDE_HOME", Path.home() / ".claude"))
TEAMS_DIR = CLAUDE_HOME / "teams"
TASKS_DIR = CLAUDE_HOME / "tasks"
PROJECTS_DIR = CLAUDE_HOME / "projects"

# Task status -> dashboard ticket status (also reused for worker derivation).
_TASK_STATUS_ALIASES = {
    "pending": "open",
    "in_progress": "in-progress",
    "in-progress": "in-progress",
    "completed": "done",
    "done": "done",
}

_LINEAR_RE = re.compile(r"\b([A-Z]{2,}-\d+)\b")

# A team is pruned from the aggregated view when its lead session is gone OR its
# most recent transcript is older than this (lead's decision: wide 24h window so
# merely-idle teams stay visible). Hide-only; no files are ever deleted.
DEAD_TEAM_MAX_AGE_SECONDS = 86400


# ── time helpers ──────────────────────────────────────────────────────────
def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_from_mtime(path: Path) -> str | None:
    try:
        ts = path.stat().st_mtime
    except OSError:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# ── lazy integration imports (nova / echo modules) ────────────────────────
try:  # logs from transcripts (task #3, nova)
    from .transcript_logs import read_log_entries as _read_log_entries  # type: ignore
except Exception:  # ImportError or any load-time failure -> minimal fallback
    _read_log_entries = None


def _logs_for_transcript(path: Path) -> list[dict]:
    """Return UI log entries for a transcript, or [] when the module is absent.

    providers.transcript_logs.read_log_entries(path, offset=0) -> (entries, new_offset)
    where ``offset`` is an integer byte position (0 = read from start). We do a
    full read here (offset 0); incremental tailing belongs to the /logs route,
    which can persist the returned offset per worker.
    """
    if _read_log_entries is None or path is None or not path.exists():
        return []
    try:
        entries, _offset = _read_log_entries(str(path), 0)
        return entries or []
    except Exception:
        return []


try:  # task -> ticket mapping (task #4, echo)
    from .tasks_map import task_to_ticket as _task_to_ticket  # type: ignore
except Exception:
    _task_to_ticket = None


try:  # waiting detection (task #5, atlas)
    from . import waiting_detect as _waiting_detect  # type: ignore
except Exception:
    _waiting_detect = None


try:  # dead-team pruning (task #7, nova)
    from . import team_health as _team_health  # type: ignore
except Exception:
    _team_health = None


def _task_to_ticket_fallback(task: dict, *, team: str) -> dict:
    """Minimal inline task->ticket mapping used until tasks_map lands."""
    subject = task.get("subject", "")
    description = task.get("description", "")
    raw_status = task.get("status", "pending")
    status = _TASK_STATUS_ALIASES.get(raw_status, "open")
    if task.get("blockedBy"):
        status = "blocked"

    linear = None
    match = _LINEAR_RE.search(subject) or _LINEAR_RE.search(description)
    if match:
        linear = match.group(1)

    ticket = {
        "id": str(task.get("id", "")),
        "title": subject or f"Task {task.get('id', '?')}",
        "body": description,
        "status": status,
        "assigned_to": task.get("owner"),
        "created_at": task.get("created_at") or utc_now(),
        "updated_at": task.get("updated_at") or task.get("created_at") or utc_now(),
        "history": [],
        "comments": [],
        "labels": [team] if team else [],
        "priority": "medium",
    }
    if linear:
        ticket["linear_url"] = f"https://linear.app/mylinearwk/issue/{linear}"
    return ticket


def map_task_to_ticket(task: dict, *, team: str) -> dict:
    if _task_to_ticket is not None:
        try:
            return _task_to_ticket(task, team=team)
        except TypeError:
            # Be tolerant of a slightly different signature during integration.
            try:
                return _task_to_ticket(task)
            except Exception:
                pass
        except Exception:
            pass
    return _task_to_ticket_fallback(task, team=team)


# ── team / task discovery ─────────────────────────────────────────────────
def discover_teams() -> list[str]:
    """Return the names of valid, *alive* teams.

    A team is a ~/.claude/teams/{name}/config.json that exists. Dead teams
    (lead session gone / no recent activity) are pruned via
    providers.team_health.prune_dead_teams when available; if the module is
    absent it fails open and every discovered team is returned. Output order is
    stable (sorted by name).
    """
    if not TEAMS_DIR.exists():
        return []
    teams = []
    for entry in sorted(TEAMS_DIR.iterdir()):
        if entry.is_dir() and (entry / "config.json").is_file():
            teams.append(entry.name)

    if _team_health is not None:
        try:
            # Dead = lead session gone OR no transcript activity for >24h
            # (lead's decision). We only hide; files are never deleted.
            teams = _team_health.prune_dead_teams(
                teams, load_config=load_team_config, max_age_seconds=DEAD_TEAM_MAX_AGE_SECONDS
            )
        except Exception:
            pass  # fail open: keep all discovered teams on any pruning error
    return teams


def load_team_config(team: str) -> dict:
    config = read_json(TEAMS_DIR / team / "config.json")
    return config or {}


def load_team_tasks(team: str) -> list[dict]:
    """Load tasks for a team, sorted by numeric id when possible."""
    task_dir = TASKS_DIR / team
    if not task_dir.is_dir():
        return []
    tasks = []
    for path in task_dir.glob("*.json"):
        raw = read_json(path)
        if raw and "id" in raw:
            tasks.append(raw)

    def sort_key(task: dict):
        tid = str(task.get("id", ""))
        return (0, int(tid)) if tid.isdigit() else (1, tid)

    return sorted(tasks, key=sort_key)


# ── transcript resolution ─────────────────────────────────────────────────
def project_slug(cwd: str) -> str:
    """Turn an absolute cwd into the ~/.claude/projects slug.

    /Users/ericfer/projects/agent-squad -> -Users-ericfer-projects-agent-squad
    """
    return cwd.replace("/", "-")


def _subagent_dirs(cwd: str):
    """Yield every subagents/ directory under the project slug for ``cwd``."""
    slug_dir = PROJECTS_DIR / project_slug(cwd)
    if not slug_dir.is_dir():
        return
    for session_dir in slug_dir.iterdir():
        sub = session_dir / "subagents"
        if sub.is_dir():
            yield sub


def transcript_index(cwd: str) -> dict[str, Path]:
    """Map member name -> most recent transcript path for a project cwd.

    The member name is read from each ``agent-{id}.meta.json`` (field
    ``agentType``). When several transcripts exist for the same name (across
    sessions), the one with the newest mtime wins.
    """
    index: dict[str, Path] = {}
    best_mtime: dict[str, float] = {}
    for sub in _subagent_dirs(cwd):
        for meta_path in sub.glob("agent-*.meta.json"):
            meta = read_json(meta_path)
            if not meta:
                continue
            name = meta.get("agentType")
            if not name:
                continue
            jsonl = meta_path.with_name(meta_path.name.replace(".meta.json", ".jsonl"))
            if not jsonl.is_file():
                continue
            try:
                mtime = jsonl.stat().st_mtime
            except OSError:
                continue
            if name not in best_mtime or mtime > best_mtime[name]:
                best_mtime[name] = mtime
                index[name] = jsonl
    return index


# ── worker assembly ───────────────────────────────────────────────────────
# A transcript whose mtime is within this many seconds is considered "active".
ACTIVE_WINDOW_SECONDS = 60


def _transcript_age_seconds(transcript: Path | None) -> float | None:
    """Seconds since the transcript was last written, or None if unavailable."""
    if transcript is None or not transcript.is_file():
        return None
    try:
        mtime = transcript.stat().st_mtime
    except OSError:
        return None
    return max(0.0, datetime.now(timezone.utc).timestamp() - mtime)


def derive_status(
    *,
    in_config: bool,
    owned_tasks: list[dict],
    transcript: Path | None,
) -> str:
    """Fine-grained worker status (task #2).

    Precedence:
    - member absent from config.json                  -> exited
    - has an in_progress task:
          transcript active (mtime < 60s)             -> running
          transcript inactive                         -> waiting
    - has tasks, all completed                        -> done
    - has a task with non-empty blockedBy             -> blocked
    - otherwise (no tasks / only pending)             -> idle
    """
    if not in_config:
        return "exited"

    in_progress = [t for t in owned_tasks if t.get("status") == "in_progress"]
    if in_progress:
        age = _transcript_age_seconds(transcript)
        if age is not None and age < ACTIVE_WINDOW_SECONDS:
            return "running"
        return "waiting"

    if owned_tasks and all(t.get("status") == "completed" for t in owned_tasks):
        return "done"

    if any(t.get("blockedBy") for t in owned_tasks):
        return "blocked"

    return "idle"


def build_workers(team: str, config: dict, tasks: list[dict]):
    """Return (workers, logs) for a single team."""
    members = config.get("members", []) or []
    # Group tasks by owner once.
    tasks_by_owner: dict[str, list[dict]] = {}
    for task in tasks:
        owner = task.get("owner")
        if owner:
            tasks_by_owner.setdefault(owner, []).append(task)

    workers: list[dict] = []
    logs: dict[str, list[dict]] = {}

    # Build the transcript index once per team cwd (cheap on small teams; the
    # index walks subagents/ dirs, not the transcript bodies).
    team_cwd = config.get("cwd") or (
        members[0].get("cwd") if members else None
    ) or str(Path.cwd())
    index = transcript_index(team_cwd)

    config_names: set[str] = set()
    for member in members:
        name = member.get("name")
        if not name:
            continue
        # The lead is not a worker on the board.
        if member.get("agentType") == "team-lead":
            continue
        config_names.add(name)

        owned = tasks_by_owner.get(name, [])
        transcript = index.get(name)

        worker = _make_worker(
            team=team,
            name=name,
            owned=owned,
            transcript=transcript,
            in_config=True,
            created_iso=_member_joined_iso(member),
        )
        workers.append(worker)
        logs[worker["id"]] = _logs_for_transcript(transcript) if transcript else []

    # Task owners that are no longer members of the team config -> exited.
    for name, owned in tasks_by_owner.items():
        if name in config_names:
            continue
        transcript = index.get(name)
        worker = _make_worker(
            team=team,
            name=name,
            owned=owned,
            transcript=transcript,
            in_config=False,
            created_iso=None,
        )
        workers.append(worker)
        logs[worker["id"]] = _logs_for_transcript(transcript) if transcript else []

    return workers, logs


def _make_worker(
    *,
    team: str,
    name: str,
    owned: list[dict],
    transcript: Path | None,
    in_config: bool,
    created_iso: str | None,
) -> dict:
    active = next((t for t in owned if t.get("status") == "in_progress"), None)
    ticket_id = str(active["id"]) if active else (
        str(owned[0]["id"]) if owned else None
    )

    last_activity = iso_from_mtime(transcript) if transcript else None
    worker_id = f"{name}@{team}"
    status = derive_status(in_config=in_config, owned_tasks=owned, transcript=transcript)
    created = created_iso or last_activity or utc_now()

    # Waiting detection (S5): a teammate that ended its turn with a question to
    # the lead is "waiting", regardless of whether its task is still in_progress
    # or all-completed. Never override a terminal exited state.
    waiting_question = None
    if status != "exited":
        detected = _detect_waiting(transcript)
        if detected:
            status = "waiting"
            waiting_question = detected.get("question")

    return {
        "id": worker_id,
        "name": name,
        "agent": "claude",
        "session": worker_id,
        "status": status,
        "role": "Worker",
        "ticket_id": ticket_id,
        "created_at": created,
        "last_activity_at": last_activity or created,
        "exit_code": 0 if status == "done" else None,
        "output": _last_output(transcript),
        "waiting_question": waiting_question,
        "team": team,
    }


def _detect_waiting(transcript: Path | None) -> dict | None:
    """Run the waiting-detection module, or None when it is unavailable."""
    if _waiting_detect is None or transcript is None:
        return None
    try:
        return _waiting_detect.detect_waiting(
            transcript, idle_after=ACTIVE_WINDOW_SECONDS
        )
    except Exception:
        return None


def _member_joined_iso(member: dict) -> str:
    joined = member.get("joinedAt")
    if isinstance(joined, (int, float)):
        # joinedAt is epoch milliseconds in config.json.
        seconds = joined / 1000 if joined > 1e12 else joined
        return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return utc_now()


def _last_output(transcript: Path | None) -> str:
    """Best-effort short last-line summary without the full logs module.

    Reads the final assistant text line of the transcript. Kept intentionally
    small; the rich rendering belongs to providers.transcript_logs.
    """
    if transcript is None or not transcript.is_file():
        return ""
    try:
        # Read the tail cheaply; transcripts can be several MB.
        with transcript.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            chunk = min(size, 65536)
            fh.seek(size - chunk)
            tail = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return ""

    for line in reversed(tail.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("type") != "assistant":
            continue
        content = record.get("message", {}).get("content")
        text = _extract_text(content)
        if text:
            return text[:280]
    return ""


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return " ".join(p.strip() for p in parts if p).strip()
    return ""


def worker_logs(worker_id: str) -> list[dict]:
    """Return UI log entries for a worker id ("name@team").

    Resolves the worker's transcript across all teams (the worker id encodes the
    team) and delegates to providers.transcript_logs. Returns [] when the worker,
    team, or transcript can't be found.
    """
    if "@" not in worker_id:
        return []
    name, _, team = worker_id.partition("@")
    if not name or team not in set(discover_teams()):
        return []

    config = load_team_config(team)
    members = config.get("members", []) or []
    cwd = next(
        (m.get("cwd") for m in members if m.get("name") == name and m.get("cwd")),
        None,
    ) or config.get("cwd") or str(Path.cwd())

    transcript = transcript_index(cwd).get(name)
    return _logs_for_transcript(transcript) if transcript else []


# ── public entry point ────────────────────────────────────────────────────
def build_state() -> dict:
    """Assemble the /api/state payload from all valid Agent Teams.

    Returns the same contract as the legacy provider. When no team exists,
    every collection is empty and no error is raised.
    """
    all_workers: list[dict] = []
    all_tickets: list[dict] = []
    all_logs: dict[str, list[dict]] = {}

    for team in discover_teams():
        config = load_team_config(team)
        tasks = load_team_tasks(team)

        workers, logs = build_workers(team, config, tasks)
        all_workers.extend(workers)
        all_logs.update(logs)

        for task in tasks:
            all_tickets.append(map_task_to_ticket(task, team=team))

    return {
        "workers": all_workers,
        "tickets": all_tickets,
        "logs": all_logs,
        "signals": {"waiting": [], "responses": []},
        "generated_at": utc_now(),
    }


if __name__ == "__main__":
    print(json.dumps(build_state(), ensure_ascii=False, indent=2))
