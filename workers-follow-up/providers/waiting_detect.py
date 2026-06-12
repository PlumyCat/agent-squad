#!/usr/bin/env python3
"""Detect whether a teammate is *waiting* for a reply from the lead (S5/MYL-74).

Two approaches were considered:

Piste 1 — parse the tail of the teammate transcript (chosen).
    A teammate is "waiting" when:
      - its turn has ended (the last transcript record is an ``assistant`` text
        message with no pending tool_use — i.e. it is not mid-tool-call), AND
      - the transcript is idle (mtime older than the active window), AND
      - the last outgoing action toward the lead in the recent tail is a
        question (a ``SendMessage`` to "team-lead", or a plan_approval_request).
    Rationale: works on existing data with zero extra moving parts, no hook to
    install, and degrades gracefully (no signal -> simply not "waiting").

Piste 2 — a TeammateIdle hook writing signals/waiting/*.json.
    Rejected as the primary mechanism: it requires installing and maintaining a
    Claude Code hook, only fires going forward (blind to already-idle agents),
    and adds a second source of truth. We still *read* signals/waiting/*.json
    when present (see ``signal_waiting``) so a hook can augment detection later,
    but the transcript parser is authoritative and self-sufficient.

Public API
----------
    detect_waiting(transcript: Path | None, *, idle_after: float) -> dict | None
        Returns {"question": str} when the teammate appears to be waiting,
        else None. ``idle_after`` is the inactivity threshold in seconds
        (reuse the provider's ACTIVE_WINDOW_SECONDS).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


# How many trailing transcript records to scan for an outgoing question.
_TAIL_RECORDS = 12
_MAX_QUESTION_LEN = 280


def _read_tail_records(transcript: Path, limit: int) -> list[dict]:
    """Return up to ``limit`` last JSON records of a transcript (cheap tail read)."""
    try:
        with transcript.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            # 12 records of teammate chat fit comfortably in 256 KB.
            chunk = min(size, 262144)
            fh.seek(size - chunk)
            blob = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return []

    records: list[dict] = []
    for line in blob.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records[-limit:]


def _is_turn_ended(record: dict) -> bool:
    """True when the record is an assistant turn that ended (text, no tool_use).

    A trailing ``user``/``tool_result`` record means a tool just returned and the
    agent is mid-turn (still working) -> not waiting.
    """
    if record.get("type") != "assistant":
        return False
    content = record.get("message", {}).get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        has_text = any(
            isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip()
            for b in content
        )
        has_tool_use = any(
            isinstance(b, dict) and b.get("type") == "tool_use" for b in content
        )
        return has_text and not has_tool_use
    return False


def _outgoing_question(records: list[dict]) -> str | None:
    """Find the most recent outgoing question toward the lead in the tail.

    Recognises a ``SendMessage`` tool_use addressed to "team-lead" and an
    explicit ``plan_approval_request``. Returns the question text or None.
    """
    for record in reversed(records):
        content = record.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") == "SendMessage":
                inp = block.get("input", {}) or {}
                to = (inp.get("to") or inp.get("recipient") or "").lower()
                if "team-lead" in to or "lead" in to:
                    return _question_text(inp)
            # An explicit plan-approval request, however it surfaces in content.
            blob = json.dumps(block, ensure_ascii=False).lower()
            if "plan_approval_request" in blob:
                return "Demande d'approbation de plan en attente."
    return None


def _question_text(send_input: dict) -> str:
    msg = send_input.get("message")
    if isinstance(msg, dict):
        # Structured protocol messages (e.g. plan approval) — use a label.
        if msg.get("type"):
            return f"En attente : {msg.get('type')}"
        msg = msg.get("content") or msg.get("text") or ""
    text = (send_input.get("summary") or "").strip()
    body = (msg if isinstance(msg, str) else "").strip()
    # Prefer the human-readable summary; fall back to the message body.
    chosen = text or body
    return chosen[:_MAX_QUESTION_LEN] if chosen else "Question en attente d'une réponse."


def _idle_seconds(transcript: Path) -> float | None:
    try:
        mtime = transcript.stat().st_mtime
    except OSError:
        return None
    return max(0.0, datetime.now(timezone.utc).timestamp() - mtime)


def detect_waiting(transcript: Path | None, *, idle_after: float) -> dict | None:
    """Return {"question": str} when the teammate is waiting, else None."""
    if transcript is None or not transcript.is_file():
        return None

    idle = _idle_seconds(transcript)
    if idle is None or idle < idle_after:
        # Recently active -> running, not waiting.
        return None

    records = _read_tail_records(transcript, _TAIL_RECORDS)
    if not records or not _is_turn_ended(records[-1]):
        return None

    question = _outgoing_question(records)
    if not question:
        return None
    return {"question": question}


def signal_waiting(team_root: Path, worker_name: str) -> dict | None:
    """Optional Piste 2 augmentation: read a hook-written waiting signal.

    Looks for ``{team_root}/signals/waiting/{worker_name}.json`` (the existing
    signal format) and returns {"question": message} when present. Returns None
    when no such signal exists. The transcript parser remains authoritative.
    """
    path = team_root / "signals" / "waiting" / f"{worker_name}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    question = data.get("message") or data.get("question")
    return {"question": str(question)[:_MAX_QUESTION_LEN]} if question else None
