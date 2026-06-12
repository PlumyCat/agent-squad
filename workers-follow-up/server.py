#!/usr/bin/env python3
"""Local Claude Squad monitoring server.

Serves the exported UI and exposes a read-only API backed by tmux sessions,
ticket JSON files, and waiting/response signal files.
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import subprocess
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

try:
    from providers import agent_teams, worker_actions
except ImportError:  # running from a different cwd
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from providers import agent_teams, worker_actions


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = Path(__file__).resolve().parent
TICKETS_DIR = ROOT / "tickets-cli" / "tickets"
WAITING_DIR = ROOT / "signals" / "waiting"
RESPONSES_DIR = ROOT / "signals" / "responses"
WORKER_PREFIXES = ("codex-", "claude-")
SESSION_RE = re.compile(r"^(codex|claude)-[A-Za-z0-9_.-]+$")

mimetypes.add_type("text/babel; charset=utf-8", ".jsx")


def active_provider() -> str:
    """Return the configured provider name (``agent_teams`` or ``codex``)."""
    return os.environ.get("WFU_PROVIDER", "agent_teams").strip().lower()


# Map a worker_actions.kill_worker ``reason`` to an HTTP status code.
_KILL_STATUS_BY_REASON = {
    "invalid": 400,      # malformed / missing identifier
    "in-process": 409,   # Agent Teams worker — no tmux pane to kill
    "not-found": 404,    # valid session name but no live tmux session
    "tmux-error": 500,   # tmux ran but failed
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_from_epoch(value: str | int | None) -> str:
    if not value:
        return utc_now()
    return datetime.fromtimestamp(int(value), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_tmux(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["tmux", *args], capture_output=True, text=True)


def session_exists(session: str) -> bool:
    return run_tmux("has-session", "-t", session).returncode == 0


def validate_worker_session(session: str) -> bool:
    return bool(SESSION_RE.match(session))


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_tickets() -> list[dict]:
    tickets = []
    if not TICKETS_DIR.exists():
        return tickets

    for path in sorted(TICKETS_DIR.glob("*.json")):
        raw = read_json(path)
        if not raw:
            continue

        history = []
        for item in raw.get("history", []):
            timestamp = item.get("timestamp") or item.get("t") or raw.get("updated_at") or utc_now()
            action = item.get("action", "updated")
            if action == "status_change":
                text = f"Statut -> {item.get('to', 'unknown')}"
            else:
                text = item.get("details") or item.get("text") or action
            history.append({"t": timestamp, "who": item.get("who", "squad"), "text": text})

        tickets.append(
            {
                "id": raw.get("id", path.stem),
                "title": raw.get("title", path.stem),
                "body": raw.get("body", ""),
                "status": raw.get("status", "open"),
                "assigned_to": raw.get("assigned_to"),
                "created_at": raw.get("created_at") or utc_now(),
                "updated_at": raw.get("updated_at") or raw.get("created_at") or utc_now(),
                "history": history,
                "comments": raw.get("comments", []),
                "labels": raw.get("labels", []),
                "priority": raw.get("priority", "medium"),
            }
        )

    return tickets


def ticket_by_worker(tickets: list[dict]) -> dict[str, dict]:
    return {
        ticket["assigned_to"]: ticket
        for ticket in tickets
        if ticket.get("assigned_to")
    }


def waiting_signals() -> dict[str, dict]:
    signals = {}
    if not WAITING_DIR.exists():
        return signals
    for path in WAITING_DIR.glob("*.json"):
        data = read_json(path)
        if data:
            signals[data.get("session") or path.stem] = data
    return signals


def response_signals() -> dict[str, dict]:
    signals = {}
    if not RESPONSES_DIR.exists():
        return signals
    for path in RESPONSES_DIR.glob("*.json"):
        data = read_json(path)
        if data:
            signals[data.get("session") or path.stem] = data
    return signals


def capture_lines(session: str, lines: int = 80) -> list[str]:
    result = run_tmux("capture-pane", "-t", session, "-p")
    if result.returncode != 0:
        return []
    output = result.stdout.splitlines()
    return output[-lines:]


def classify_log_line(line: str) -> str:
    lowered = line.lower()
    if "error" in lowered or "failed" in lowered or "traceback" in lowered:
        return "err"
    if "warning" in lowered or "warn" in lowered or "blocked" in lowered:
        return "warn"
    if "✓" in line or "done" in lowered or "success" in lowered:
        return "ok"
    if line.strip().startswith(("$", ">")):
        return "cmd"
    return "info"


def log_entries(session: str, lines: int = 120) -> list[dict]:
    captured = capture_lines(session, lines)
    stamp = utc_now()
    return [
        {"id": f"{session}-{index}", "time": stamp, "kind": classify_log_line(line), "text": line}
        for index, line in enumerate(captured)
        if line.strip()
    ]


def parse_exit_code(lines: list[str]) -> int | None:
    for line in reversed(lines):
        marker = "[squad] Agent exited with status "
        if marker in line:
            value = line.split(marker, 1)[1].split(".", 1)[0].strip()
            try:
                return int(value)
            except ValueError:
                return None
    return None


def load_workers(tickets: list[dict]) -> tuple[list[dict], dict[str, list[dict]]]:
    result = run_tmux(
        "list-sessions",
        "-F",
        "#{session_name}\t#{session_created}\t#{session_activity}",
    )
    if result.returncode != 0:
        return [], {}

    by_worker = ticket_by_worker(tickets)
    waiting = waiting_signals()
    workers = []
    logs = {}

    for raw in result.stdout.splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t")
        session = parts[0]
        if not session.startswith(WORKER_PREFIXES):
            continue

        created = iso_from_epoch(parts[1] if len(parts) > 1 else None)
        activity = iso_from_epoch(parts[2] if len(parts) > 2 else None)
        agent = "claude" if session.startswith("claude-") else "codex"
        ticket = by_worker.get(session)
        signal = waiting.get(session)
        lines = capture_lines(session, 80)
        output = next((line for line in reversed(lines) if line.strip()), "")
        exit_code = parse_exit_code(lines)

        if signal:
            status = "waiting"
        elif ticket and ticket.get("status") in {"waiting", "blocked"}:
            status = ticket["status"]
        elif exit_code is not None:
            status = "done" if exit_code == 0 else "exited"
        else:
            status = "running"

        workers.append(
            {
                "id": session,
                "name": session,
                "agent": agent,
                "session": session,
                "status": status,
                "role": "Worker",
                "ticket_id": (signal or {}).get("ticket_id") or (ticket or {}).get("id"),
                "created_at": created,
                "last_activity_at": activity,
                "exit_code": exit_code,
                "output": output,
                "waiting_question": (signal or {}).get("message"),
            }
        )
        logs[session] = [
            {"id": f"{session}-{index}", "time": activity, "kind": classify_log_line(line), "text": line}
            for index, line in enumerate(lines)
            if line.strip()
        ]

    return workers, logs


def build_state_codex() -> dict:
    """Legacy provider: tmux sessions + ticket JSON files + signal files."""
    tickets = load_tickets()
    workers, logs = load_workers(tickets)
    return {
        "workers": workers,
        "tickets": tickets,
        "logs": logs,
        "signals": {
            "waiting": list(waiting_signals().values()),
            "responses": list(response_signals().values()),
        },
        "generated_at": utc_now(),
    }


def build_state(provider: str | None = None) -> dict:
    """Dispatch to the requested provider.

    ``provider`` (per-request, e.g. ``?provider=codex``) wins over the
    WFU_PROVIDER env default. Both pages can therefore be served by one
    process: ``/`` polls agent_teams, ``/codex`` polls the legacy backend.

    WFU_PROVIDER=agent_teams (default) -> Claude Code Agent Teams.
    WFU_PROVIDER=codex                 -> legacy tmux/codex backend above.
    """
    resolved = provider if provider in {"codex", "agent_teams"} else active_provider()
    if resolved == "codex":
        state = build_state_codex()
    else:
        state = agent_teams.build_state()
    state["provider"] = resolved
    # Enrich each worker with killable so the UI can enable/disable the kill
    # button per worker (true only for live tmux sessions; in-process Agent
    # Teams workers get false). Done centrally so the provider modules stay
    # independent of worker_actions. Field name "killable" is the canonical
    # contract read by the frontend (worker-panel.jsx / app.jsx).
    for worker in state.get("workers", []):
        worker["killable"] = worker_actions.can_kill(worker)
    return state


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, data: object, status: int = 200):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/state":
            query = parse_qs(parsed.query)
            provider = (query.get("provider", [""])[0] or "").strip().lower() or None
            self.send_json(build_state(provider))
            return

        if path.startswith("/api/workers/") and path.endswith("/logs"):
            session = path.removeprefix("/api/workers/").removesuffix("/logs").strip("/")
            # Dispatch by identifier shape, not by global provider: Agent Teams
            # workers are "name@team" (transcript JSONL), legacy codex workers
            # are tmux session names (capture-pane). Both pages work at once.
            if "@" in session:
                entries = agent_teams.worker_logs(session)
            else:
                entries = log_entries(session)
            self.send_json({"worker": session, "logs": entries})
            return

        # "/" serves the Claude Agent Teams page; "/codex" serves the same SPA,
        # which switches its data source to the legacy codex/tmux provider by
        # reading its own URL path (see app/app.jsx).
        if path in {"/", "", "/codex", "/codex/"}:
            self.path = "/Claude%20Squad.html"
            return super().do_GET()

        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path.startswith("/api/workers/") and path.endswith("/kill"):
            worker_id = path.removeprefix("/api/workers/").removesuffix("/kill").strip("/")
            # Delegate to providers.worker_actions, which decides per identifier
            # whether a kill is possible: legacy tmux sessions (codex-*/claude-*)
            # are killed; in-process Agent Teams workers ("name@team") are
            # refused cleanly. The worker id already carries its team via "@team",
            # so no separate team argument is needed here.
            outcome = worker_actions.kill_worker("", worker_id)
            status = _KILL_STATUS_BY_REASON.get(outcome.get("reason"), 200 if outcome.get("ok") else 500)
            self.send_json(outcome, status=status)
            return

        self.send_json({"ok": False, "error": "not found"}, status=404)

    def guess_type(self, path):
        guessed = super().guess_type(path)
        if guessed == "application/octet-stream":
            return mimetypes.guess_type(path)[0] or guessed
        return guessed


def main():
    host = "127.0.0.1"
    port = 8787
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Claude Squad UI: http://{host}:{port}")
    print("API state:       http://127.0.0.1:8787/api/state")
    server.serve_forever()


if __name__ == "__main__":
    main()
