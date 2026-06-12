#!/usr/bin/env python3
"""Read Claude Agent Teams teammate transcripts into dashboard log entries.

With Agent Teams, teammates run in-process rather than in tmux split-panes, so
their activity is no longer reachable via ``capture-pane``. Instead each
teammate writes a JSONL transcript at::

    ~/.claude/projects/{project-slug}/{sessionId}/subagents/agent-{agentId}.jsonl

Every line is one JSON object (an assistant message, a user/tool-result turn,
an attachment, ...). This module turns those lines into the log-entry shape the
existing dashboard UI consumes::

    {"id": str, "time": str, "kind": str, "text": str}

where ``kind`` is one of ``cmd | info | ok | warn | err | dim`` (see app/data.js
and server.py for the UI contract).

The module is intentionally self-contained: stdlib only, no import from
server.py. The main entry point :func:`read_log_entries` reads incrementally
from a byte offset so a multi-megabyte transcript is never re-read in full.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Truncate any rendered log line to this many characters (UI is a narrow
# terminal column; long pastes/results would blow out the layout).
MAX_TEXT_LEN = 200

# Tools that operate on a file; we render them dimmed with the target path.
_FILE_TOOLS = {
    "Read",
    "Write",
    "Edit",
    "NotebookEdit",
    "MultiEdit",
}


def _truncate(text: str, limit: int = MAX_TEXT_LEN) -> str:
    """Collapse a value to a single line and cap its length with an ellipsis."""
    if not isinstance(text, str):
        text = str(text)
    # Flatten newlines/tabs so one log line stays one line.
    flat = " ".join(text.split())
    if len(flat) > limit:
        return flat[: limit - 1].rstrip() + "…"
    return flat


def _result_text(content) -> str:
    """Extract a plain-text payload from a tool_result ``content`` field.

    ``content`` may be a string or a list of content blocks (``{"type":
    "text", "text": ...}``), depending on the tool.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts)
    return ""


def _tool_target(tool_input: dict) -> str:
    """Best-effort human label for the thing a tool acted on."""
    if not isinstance(tool_input, dict):
        return ""
    path = tool_input.get("file_path") or tool_input.get("path") or tool_input.get("notebook_path")
    if path:
        # Show just the basename to keep lines short; full path is rarely useful here.
        return Path(str(path)).name
    return ""


def _classify_result(text: str) -> str:
    """Pick a kind for a (non-error) tool_result based on its content.

    Tool results are frequently large file dumps or directory listings, so a
    naive substring search for "error"/"warning" produces many false positives
    (e.g. the word appearing inside read file content). We only escalate on
    signals that reliably mean a status: a shell exit code, or a success/error
    marker at the very start of the (flattened) output. Everything else stays
    ``dim`` — the explicit ``is_error`` flag already covers real tool failures.
    """
    head = " ".join(text.split())[:80].lower()
    if head.startswith(("exit code 1", "traceback", "error:", "fatal")):
        return "err"
    if head.startswith(("warning", "⚠")):
        return "warn"
    if "✓" in text or head.startswith("success"):
        return "ok"
    return "dim"


def _entries_from_record(record: dict, seq: int) -> list[dict]:
    """Convert one parsed JSONL record into zero or more UI log entries.

    ``seq`` is the line index, used only to build stable, unique ids.
    """
    time = record.get("timestamp", "")
    message = record.get("message")
    if not isinstance(message, dict):
        return []

    content = message.get("content")
    entries: list[dict] = []

    # Some messages carry content as a bare string (e.g. the kickoff prompt).
    if isinstance(content, str):
        text = content.strip()
        if text:
            entries.append({"id": f"{seq}-0", "time": time, "kind": "info", "text": _truncate(text)})
        return entries

    if not isinstance(content, list):
        return entries

    for block_index, block in enumerate(content):
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        entry = None

        if btype == "text":
            text = (block.get("text") or "").strip()
            if text:
                # Render only the first line / short summary for assistant prose.
                first_line = text.splitlines()[0]
                entry = {"kind": "info", "text": _truncate(first_line)}

        elif btype == "tool_use":
            name = block.get("name") or "tool"
            tool_input = block.get("input") or {}
            if name == "Bash":
                command = (tool_input.get("command") or "").strip()
                if command:
                    entry = {"kind": "cmd", "text": _truncate(f"$ {command}")}
            else:
                target = _tool_target(tool_input)
                label = f"{name} {target}".strip() if target else name
                entry = {"kind": "dim", "text": _truncate(label)}

        elif btype == "tool_result":
            text = _result_text(block.get("content"))
            stripped = text.strip()
            if block.get("is_error"):
                entry = {"kind": "err", "text": _truncate(stripped or "(tool error)")}
            elif stripped:
                entry = {"kind": _classify_result(stripped), "text": _truncate(stripped)}

        if entry is not None:
            entry = {"id": f"{seq}-{block_index}", "time": time, **entry}
            entries.append(entry)

    return entries


def read_log_entries(
    path: Path,
    offset: int = 0,
    max_entries: int = 120,
) -> tuple[list[dict], int]:
    """Read new log entries from a teammate transcript, incrementally.

    Args:
        path: Path to the ``agent-{agentId}.jsonl`` transcript.
        offset: Byte offset to start reading from (e.g. the value returned by a
            previous call). ``0`` reads from the start.
        max_entries: Cap on the number of UI entries returned. When the file
            yields more than this, the **most recent** ``max_entries`` are kept.

    Returns:
        A ``(entries, new_offset)`` tuple. ``new_offset`` is the byte position
        at end of file after this read; pass it back on the next call to resume
        without re-reading. On a missing file, returns ``([], offset)``.
    """
    path = Path(path)
    if not path.exists():
        return [], offset

    entries: list[dict] = []
    try:
        with path.open("rb") as handle:
            handle.seek(offset)
            seq = offset  # use byte position prefix to keep ids unique across reads
            for raw in handle:
                # Track the seq off the running byte position so ids stay unique
                # even though we read incrementally across calls.
                line_start = seq
                seq += len(raw)
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    # A partial trailing line (writer mid-flush) — skip; the next
                    # read picks it up once complete via the unchanged offset below.
                    continue
                entries.extend(_entries_from_record(record, line_start))
            new_offset = handle.tell()
    except OSError:
        return [], offset

    if len(entries) > max_entries:
        entries = entries[-max_entries:]

    return entries, new_offset


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python3 transcript_logs.py <transcript.jsonl>", file=sys.stderr)
        sys.exit(2)

    target = Path(sys.argv[1]).expanduser()
    log_entries, end_offset = read_log_entries(target)
    for item in log_entries:
        print(f"[{item['kind']:>4}] {item['text']}")
    print(f"\n-- {len(log_entries)} entries, new offset = {end_offset} bytes --", file=sys.stderr)
