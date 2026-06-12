#!/usr/bin/env python3
"""Worker lifecycle actions — kill capability for split-panes vs in-process.

Background
----------
The dashboard's "Tuer" (kill) button used to map 1:1 onto ``tmux kill-session``:
every worker was a codex/claude process running in its own tmux session, named
``codex-*`` / ``claude-*``. With Claude Code **Agent Teams**, teammates run
*in-process* inside the team lead's session — there is no per-worker tmux pane to
kill, so a blind ``kill-session`` would either fail or, worse, target the wrong
session.

This module decides, per worker, whether a kill is even possible:

* **split-panes (legacy)** — a tmux session whose name matches the strict
  ``SESSION_RE`` pattern exists for the worker → killable; ``kill_worker`` runs
  ``tmux kill-session``.
* **in-process (Agent Teams)** — no such tmux session → **not** killable;
  ``kill_worker`` returns ``{"ok": False, "reason": "in-process", ...}`` cleanly
  (the caller should surface this as a 409, never a 500).

The module is intentionally self-contained: stdlib only, no import from
server.py or providers/agent_teams.py (both owned by another worker). It shells
out to ``tmux`` directly and validates every identifier before it reaches the
shell.

Public surface
--------------
* :func:`can_kill(worker)` — bool; for enriching the ``/api/state`` worker dict
  with a ``can_kill`` field the UI reads to enable/disable the button.
* :func:`kill_worker(team, worker_name)` — perform (or refuse) the kill, return
  a structured result dict.
* :data:`SESSION_RE` — the strict tmux-session validation pattern (kept in sync
  with server.py's own pattern so behaviour matches the legacy path exactly).
"""

from __future__ import annotations

import re
import subprocess

# Strict tmux session name: codex-<token> / claude-<token>. Mirrors the pattern
# server.py uses so the legacy kill path behaves identically. Anything with a
# shell metacharacter, space, slash or '@' fails this — nothing unsafe reaches
# ``tmux -t``.
SESSION_RE = re.compile(r"^(codex|claude)-[A-Za-z0-9_.-]+$")

# Agent Teams worker identifier: ``name@team`` (e.g. ``nova@workers-follow-up``).
# Used only to recognise/parse an in-process id; these are never passed to tmux.
TEAMS_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+$")


def _run_tmux(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a tmux command, capturing output. Never raises on non-zero exit."""
    try:
        return subprocess.run(["tmux", *args], capture_output=True, text=True)
    except FileNotFoundError:
        # tmux not installed (pure Agent Teams host) — emulate a failed command.
        return subprocess.CompletedProcess(args=["tmux", *args], returncode=127, stdout="", stderr="tmux not found")


def validate_session(session: str) -> bool:
    """True iff *session* is a safe, well-formed tmux worker session name."""
    return isinstance(session, str) and bool(SESSION_RE.match(session))


def tmux_session_exists(session: str) -> bool:
    """True iff a tmux session with this exact name currently exists.

    The name is validated first; an invalid name never reaches tmux.
    """
    if not validate_session(session):
        return False
    return _run_tmux("has-session", "-t", session).returncode == 0


def _worker_session_name(worker: dict) -> str | None:
    """Return the tmux session name for a worker, if it has one.

    Legacy workers carry their tmux session in ``session`` / ``id`` (e.g.
    ``codex-w1``). Agent Teams workers carry ``name@team`` there, which is not a
    tmux session — those return ``None``.
    """
    if not isinstance(worker, dict):
        return None
    for key in ("session", "id"):
        value = worker.get(key)
        if isinstance(value, str) and validate_session(value):
            return value
    return None


def can_kill(worker: dict) -> bool:
    """Whether the dashboard kill action is supported for *worker*.

    True only when the worker maps to a live tmux session (split-panes mode).
    In-process Agent Teams workers always return False. Safe to call on any
    worker dict; never raises.
    """
    session = _worker_session_name(worker)
    if session is None:
        return False
    return tmux_session_exists(session)


def kill_worker(team: str, worker_name: str) -> dict:
    """Kill a worker's tmux pane/session, or refuse cleanly if in-process.

    Args:
        team: Team name (used to build the Agent Teams id and for messages).
        worker_name: The worker's name (Agent Teams) or full tmux session name
            (legacy). Both forms are accepted; the function figures out which.

    Returns a structured dict (never raises, never a bare 500 for the caller):

    * killed:  ``{"ok": True,  "killed": True, "session": <name>, "mode": "tmux"}``
    * refused: ``{"ok": False, "reason": "in-process", "mode": "in-process",
                  "worker": <id>, "message": ...}``
    * invalid: ``{"ok": False, "reason": "invalid", "message": ...}``
    * missing: ``{"ok": False, "reason": "not-found", "session": <name>, ...}``
    * error:   ``{"ok": False, "reason": "tmux-error", "message": <stderr>}``

    The caller (server.py) maps ``reason`` to an HTTP status: ``invalid`` → 400,
    ``in-process`` → 409, ``not-found`` → 404, ``tmux-error`` → 500.
    """
    if not isinstance(worker_name, str) or not worker_name:
        return {"ok": False, "reason": "invalid", "message": "missing worker identifier"}

    # Resolve the candidate tmux session name.
    #
    # 1. A bare legacy session name passed directly (``codex-w1``).
    # 2. An Agent Teams id ``name@team`` — in-process, never has a tmux session.
    # 3. A plain worker name — only killable if a tmux session literally named
    #    that exists (it won't for Agent Teams, which is the point).
    if validate_session(worker_name):
        session = worker_name
    elif "@" in worker_name:
        # Agent Teams id; reject anything that isn't a clean name@team.
        if not TEAMS_ID_RE.match(worker_name):
            return {"ok": False, "reason": "invalid", "message": "malformed worker identifier"}
        return {
            "ok": False,
            "reason": "in-process",
            "mode": "in-process",
            "worker": worker_name,
            "message": "Worker runs in-process (Agent Teams); no tmux pane to kill.",
        }
    else:
        # Plain name — only valid as a tmux target if it forms a real session
        # name. We never fabricate a ``codex-``/``claude-`` prefix, so a plain
        # Agent Teams name falls through to in-process here.
        return {
            "ok": False,
            "reason": "in-process",
            "mode": "in-process",
            "worker": f"{worker_name}@{team}" if team else worker_name,
            "message": "Worker runs in-process (Agent Teams); no tmux pane to kill.",
        }

    # We have a validated tmux session name. Confirm it exists, then kill it.
    if not tmux_session_exists(session):
        return {
            "ok": False,
            "reason": "not-found",
            "session": session,
            "message": f"No live tmux session '{session}'.",
        }

    result = _run_tmux("kill-session", "-t", session)
    if result.returncode != 0:
        return {
            "ok": False,
            "reason": "tmux-error",
            "session": session,
            "message": result.stderr.strip() or "tmux kill-session failed",
        }

    return {"ok": True, "killed": True, "session": session, "mode": "tmux"}


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 3:
        print("usage: python3 worker_actions.py <team> <worker_name_or_session>", file=sys.stderr)
        sys.exit(2)

    outcome = kill_worker(sys.argv[1], sys.argv[2])
    print(json.dumps(outcome, indent=2, ensure_ascii=False))
    sys.exit(0 if outcome.get("ok") else 1)
