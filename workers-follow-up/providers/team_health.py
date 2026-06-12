#!/usr/bin/env python3
"""Detect and prune dead Agent Teams for the aggregated multi-team view.

``providers/agent_teams.discover_teams()`` returns every team that has a
``~/.claude/teams/{name}/config.json``. Those configs are never deleted when a
team's run ends, so the aggregated dashboard would otherwise accumulate stale
("dead") teams forever. This module decides whether a team is still alive so the
provider can filter them out.

Liveness signal
---------------
A team's ``config.json`` records ``leadSessionId`` (the lead's Claude session)
and the members' ``cwd``. The lead session's transcripts live at::

    ~/.claude/projects/{slug(cwd)}/{leadSessionId}/

A team is considered **alive** when that session directory exists. Optionally a
recency window can also be required: the most recent transcript activity under
the session directory must be within ``max_age_seconds``. With the default
``max_age_seconds=None`` only existence is checked, which is the safe default —
a team that simply went idle is still a real team and should stay on the board.

The module is self-contained: stdlib only, no import from agent_teams.py or
server.py. It re-derives the few paths it needs (mirroring agent_teams) so it can
be unit-tested and integrated via a one-line change in ``discover_teams``.
"""

from __future__ import annotations

import os
from pathlib import Path

CLAUDE_HOME = Path(os.environ.get("CLAUDE_HOME", Path.home() / ".claude"))
TEAMS_DIR = CLAUDE_HOME / "teams"
PROJECTS_DIR = CLAUDE_HOME / "projects"


def project_slug(cwd: str) -> str:
    """Turn an absolute cwd into its ~/.claude/projects slug.

    ``/Users/ericfer/projects/agent-squad`` -> ``-Users-ericfer-projects-agent-squad``.
    Kept identical to agent_teams.project_slug so paths resolve the same way.
    """
    return cwd.replace("/", "-")


def _team_cwd(config: dict) -> str | None:
    """Best-effort working directory for a team from its config.

    Prefer a top-level ``cwd``; otherwise fall back to the first member that has
    one (the lead is usually first and always carries a cwd).
    """
    if not isinstance(config, dict):
        return None
    cwd = config.get("cwd")
    if isinstance(cwd, str) and cwd:
        return cwd
    for member in config.get("members", []) or []:
        if isinstance(member, dict):
            mcwd = member.get("cwd")
            if isinstance(mcwd, str) and mcwd:
                return mcwd
    return None


def _session_dir(config: dict) -> Path | None:
    """Path to the lead session's transcript directory, or None if unresolvable."""
    session_id = config.get("leadSessionId") if isinstance(config, dict) else None
    cwd = _team_cwd(config)
    if not session_id or not cwd:
        return None
    return PROJECTS_DIR / project_slug(cwd) / str(session_id)


def _latest_activity_age(session_dir: Path) -> float | None:
    """Age in seconds of the most recently modified .jsonl under *session_dir*.

    Returns None when the directory has no transcripts. Walks the session dir
    (including subagents/) but only stats files — never reads transcript bodies.
    """
    newest: float | None = None
    try:
        for path in session_dir.rglob("*.jsonl"):
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if newest is None or mtime > newest:
                newest = mtime
    except OSError:
        return None
    if newest is None:
        return None
    import time

    return max(0.0, time.time() - newest)


def is_team_alive(config: dict, *, max_age_seconds: float | None = None) -> bool:
    """Whether a team (given its parsed config.json) is still alive.

    Args:
        config: Parsed ``~/.claude/teams/{name}/config.json``.
        max_age_seconds: When set, also require recent transcript activity
            within this many seconds. When None (default), only the existence of
            the lead session directory is required — an idle team stays alive.

    A config we cannot resolve (missing leadSessionId / cwd) is treated as
    **alive**: we prefer showing a team we are unsure about over hiding a real
    one. Never raises.
    """
    session_dir = _session_dir(config)
    if session_dir is None:
        # Can't determine — fail open (keep the team visible).
        return True
    if not session_dir.is_dir():
        return False
    if max_age_seconds is None:
        return True
    age = _latest_activity_age(session_dir)
    if age is None:
        # Session dir exists but no transcripts yet — treat as alive (just spun up).
        return True
    return age <= max_age_seconds


def prune_dead_teams(
    teams: list[str],
    *,
    load_config,
    max_age_seconds: float | None = None,
) -> list[str]:
    """Filter *teams* down to the ones that are still alive.

    Args:
        teams: Team names (e.g. from ``discover_teams()``).
        load_config: Callable ``name -> dict`` returning a team's parsed
            config.json (pass ``agent_teams.load_team_config``). Injected rather
            than imported to keep this module dependency-free and testable.
        max_age_seconds: Forwarded to :func:`is_team_alive`.

    Order is preserved. A team whose config fails to load is kept (fail open).
    """
    alive: list[str] = []
    for name in teams:
        try:
            config = load_config(name)
        except Exception:
            config = None
        if not config:
            alive.append(name)  # can't judge -> keep
            continue
        if is_team_alive(config, max_age_seconds=max_age_seconds):
            alive.append(name)
    return alive


if __name__ == "__main__":
    import json
    import sys

    # Standalone: report liveness of every team under ~/.claude/teams.
    max_age = float(sys.argv[1]) if len(sys.argv) > 1 else None

    def _load(name: str) -> dict | None:
        try:
            return json.loads((TEAMS_DIR / name / "config.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    if not TEAMS_DIR.is_dir():
        print(f"no teams dir at {TEAMS_DIR}")
        sys.exit(0)

    for entry in sorted(TEAMS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        config = _load(entry.name)
        alive = is_team_alive(config or {}, max_age_seconds=max_age)
        session_dir = _session_dir(config or {})
        print(f"{'ALIVE' if alive else 'DEAD ':5}  {entry.name:30}  session_dir={session_dir}")
