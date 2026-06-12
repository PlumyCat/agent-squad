#!/usr/bin/env python3
"""Map Agent Teams tasks to the dashboard ticket shape.

Autonomous module: stdlib only, no import from server.py. Agent Teams stores
one task per JSON file under ~/.claude/tasks/{team}/*.json with the shape::

    {id, subject, description, status, owner, blocks, blockedBy, activeForm}

``task_to_ticket`` converts such a task into the ticket dict the UI expects
(same contract as server.load_tickets), adding two fields the Agent Teams
backend can populate: ``linear_url`` (clickable Linear identifier) and
``blocked_by`` (list of blocking task ids still open).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


# pending / in_progress / completed are the Agent Teams statuses; a task with a
# non-empty blockedBy (whose blockers are not yet completed) is surfaced as
# "blocked" so it lands in the dedicated UI column.
STATUS_MAP = {
    "pending": "open",
    "in_progress": "in-progress",
    "completed": "done",
}

LINEAR_RE = re.compile(r"\b([A-Z]{2,}-\d+)\b")
LINEAR_WORKSPACE = "mylinearwk"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_from_epoch(value: float | int | None) -> str:
    if not value:
        return utc_now()
    return datetime.fromtimestamp(float(value), tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def detect_linear_id(task: dict) -> str | None:
    """Return the first Linear identifier found in subject then description."""
    for field in ("subject", "description"):
        match = LINEAR_RE.search(task.get(field) or "")
        if match:
            return match.group(1)
    return None


def linear_url(identifier: str) -> str:
    return f"https://linear.app/{LINEAR_WORKSPACE}/issue/{identifier}"


def derive_status(task: dict, blocked_by: list[str]) -> str:
    """Map the Agent Teams status, overriding to "blocked" when still blocked.

    A task is only "blocked" if it is not already done and has at least one
    blocker that is not completed (see ``open_blockers``).
    """
    raw = task.get("status", "pending")
    mapped = STATUS_MAP.get(raw, "open")
    if mapped != "done" and blocked_by:
        return "blocked"
    return mapped


def open_blockers(task: dict, tasks_by_id: dict[str, dict] | None) -> list[str]:
    """Blocking task ids that are not yet completed.

    Without the full task set (``tasks_by_id`` is None) we cannot tell which
    blockers are still open, so we conservatively return the raw blockedBy ids.
    """
    blockers = [str(b) for b in task.get("blockedBy", []) if str(b).strip()]
    if not blockers or tasks_by_id is None:
        return blockers
    return [
        bid
        for bid in blockers
        if (tasks_by_id.get(bid) or {}).get("status") != "completed"
    ]


def task_to_ticket(
    task: dict,
    *,
    team: str | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
    tasks_by_id: dict[str, dict] | None = None,
) -> dict:
    """Convert one Agent Teams task into a dashboard ticket dict.

    ``team`` (when given) is added as a label so the multi-team board can group
    tickets — this matches the call made by ``providers.agent_teams``.
    ``created_at`` / ``updated_at`` default to now when not supplied (e.g. from
    the file mtime/ctime in ``load_tickets_from_dir``). ``tasks_by_id`` lets the
    blocked-status derivation ignore blockers that are already completed.
    """
    blocked_by = open_blockers(task, tasks_by_id)
    status = derive_status(task, blocked_by)

    identifier = detect_linear_id(task)
    labels: list[str] = []
    if team:
        labels.append(team)
    owner = task.get("owner") or None
    if owner:
        labels.append(owner)

    ticket = {
        "id": str(task.get("id", "")),
        "title": task.get("subject", "") or str(task.get("id", "")),
        "body": task.get("description", "") or "",
        "status": status,
        "assigned_to": owner,
        "created_at": created_at or utc_now(),
        "updated_at": updated_at or created_at or utc_now(),
        "history": [],
        "comments": [],
        "labels": labels,
        "priority": "medium",
        "linear_url": linear_url(identifier) if identifier else None,
        "blocked_by": blocked_by,
    }
    return ticket


def load_tickets_from_dir(tasks_dir: Path) -> list[dict]:
    """Read every task file in ``tasks_dir`` and return mapped tickets.

    First pass indexes the raw tasks so blocked-status derivation can see which
    blockers are completed; second pass maps each task, using the file mtime as
    updated_at and ctime as created_at.
    """
    tasks_dir = Path(tasks_dir)
    if not tasks_dir.exists():
        return []

    raw_by_id: dict[str, dict] = {}
    files: list[tuple[Path, dict]] = []
    for path in sorted(tasks_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        raw_by_id[str(data.get("id", path.stem))] = data
        files.append((path, data))

    tickets = []
    for path, data in files:
        try:
            stat = path.stat()
            created_at = iso_from_epoch(stat.st_ctime)
            updated_at = iso_from_epoch(stat.st_mtime)
        except OSError:
            created_at = updated_at = utc_now()
        tickets.append(
            task_to_ticket(
                data,
                created_at=created_at,
                updated_at=updated_at,
                tasks_by_id=raw_by_id,
            )
        )
    return tickets


if __name__ == "__main__":
    import os

    team_dir = Path(os.path.expanduser("~/.claude/tasks/workers-follow-up"))
    print(f"Mapping tasks from {team_dir}\n")
    tickets = load_tickets_from_dir(team_dir)
    for tk in tickets:
        print(
            f"  #{tk['id']:<2} {tk['status']:<12} "
            f"linear={tk['linear_url'] or '-'}  "
            f"blocked_by={tk['blocked_by']}  "
            f"assigned_to={tk['assigned_to']}"
        )
        print(f"      {tk['title']}")
    print(f"\n{len(tickets)} ticket(s) mapped.")

    # Standalone sanity check on synthetic tasks (independent of real files).
    sample = {
        "id": "42",
        "subject": "S4 (MYL-73) — mapping",
        "description": "voir MYL-73 et ABC-9",
        "status": "in_progress",
        "owner": "echo",
        "blocks": ["7"],
        "blockedBy": ["1"],
    }
    blockers_open = {"1": {"id": "1", "status": "pending"}}
    blockers_done = {"1": {"id": "1", "status": "completed"}}
    print("\nSynthetic checks:")
    t_open = task_to_ticket(sample, tasks_by_id=blockers_open)
    t_done = task_to_ticket(sample, tasks_by_id=blockers_done)
    assert t_open["status"] == "blocked", t_open["status"]
    assert t_open["linear_url"].endswith("/MYL-73"), t_open["linear_url"]
    assert t_open["blocked_by"] == ["1"], t_open["blocked_by"]
    assert t_done["status"] == "in-progress", t_done["status"]
    assert t_done["blocked_by"] == [], t_done["blocked_by"]
    assert task_to_ticket({"id": "9", "status": "completed"})["status"] == "done"
    assert task_to_ticket({"id": "9", "status": "pending"})["status"] == "open"
    print("  OK")
