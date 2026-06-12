#!/usr/bin/env python3
"""Tests for transcript_logs — run with: python3 -m providers.test_transcript_logs

Stdlib only; no pytest dependency. Builds synthetic JSONL transcripts in a temp
dir to cover the parsing, classification, truncation, and incremental-offset
behaviour of read_log_entries without depending on any real transcript.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from providers.transcript_logs import (
    MAX_TEXT_LEN,
    _classify_result,
    _truncate,
    read_log_entries,
)


def _record(content, *, role="assistant", timestamp="2026-06-12T07:54:15.639Z"):
    return {"timestamp": timestamp, "message": {"role": role, "content": content}}


def _write_jsonl(records: list[dict]) -> Path:
    tmp = Path(tempfile.mkdtemp()) / "agent-test.jsonl"
    with tmp.open("w", encoding="utf-8") as handle:
        for rec in records:
            handle.write(json.dumps(rec) + "\n")
    return tmp


def test_truncate_caps_and_flattens():
    assert _truncate("a\nb\tc") == "a b c"
    long = _truncate("x" * 500)
    assert len(long) == MAX_TEXT_LEN
    assert long.endswith("…")


def test_classify_result():
    assert _classify_result("Exit code 1\nboom") == "err"
    assert _classify_result("Traceback (most recent call last)") == "err"
    assert _classify_result("Warning: deprecated") == "warn"
    assert _classify_result("  ✓ all good") == "ok"
    # Large file dumps that merely contain the word "error" must stay dim.
    assert _classify_result("def f():\n    # handle error case\n    pass") == "dim"
    assert _classify_result("total 0\ndrwxr-xr-x") == "dim"


def test_bash_command_becomes_cmd():
    path = _write_jsonl([_record([{"type": "tool_use", "name": "Bash",
                                   "input": {"command": "ls -la /tmp"}}])])
    entries, _ = read_log_entries(path)
    assert entries[0]["kind"] == "cmd"
    assert entries[0]["text"] == "$ ls -la /tmp"


def test_file_tool_becomes_dim_with_basename():
    path = _write_jsonl([_record([{"type": "tool_use", "name": "Edit",
                                   "input": {"file_path": "/a/b/server.py"}}])])
    entries, _ = read_log_entries(path)
    assert entries[0]["kind"] == "dim"
    assert entries[0]["text"] == "Edit server.py"


def test_assistant_text_first_line_only():
    path = _write_jsonl([_record([{"type": "text", "text": "summary line\nmore detail\nextra"}])])
    entries, _ = read_log_entries(path)
    assert entries[0]["kind"] == "info"
    assert entries[0]["text"] == "summary line"


def test_error_tool_result():
    path = _write_jsonl([_record(
        [{"type": "tool_result", "tool_use_id": "t1", "is_error": True,
          "content": "EISDIR: illegal operation"}],
        role="user")])
    entries, _ = read_log_entries(path)
    assert entries[0]["kind"] == "err"
    assert "EISDIR" in entries[0]["text"]


def test_string_content_kickoff_prompt():
    path = _write_jsonl([_record("Tu es atlas, worker de la team.", role="user")])
    entries, _ = read_log_entries(path)
    assert entries[0]["kind"] == "info"
    assert entries[0]["text"].startswith("Tu es atlas")


def test_incremental_offset_resumes_at_eof():
    path = _write_jsonl([
        _record([{"type": "text", "text": "first"}]),
        _record([{"type": "text", "text": "second"}]),
    ])
    first, offset = read_log_entries(path)
    assert len(first) == 2
    resumed, offset2 = read_log_entries(path, offset=offset)
    assert resumed == []
    assert offset2 == offset

    # Append a new line; resuming from the saved offset must yield only the new entry.
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_record([{"type": "text", "text": "third"}])) + "\n")
    new, offset3 = read_log_entries(path, offset=offset)
    assert len(new) == 1
    assert new[0]["text"] == "third"
    assert offset3 > offset


def test_unique_ids_and_max_entries():
    records = [_record([{"type": "text", "text": f"line {i}"}]) for i in range(200)]
    path = _write_jsonl(records)
    entries, _ = read_log_entries(path, max_entries=50)
    assert len(entries) == 50  # most recent kept
    assert entries[-1]["text"] == "line 199"
    assert len({e["id"] for e in entries}) == 50  # ids unique


def test_missing_file_preserves_offset():
    entries, offset = read_log_entries(Path("/no/such/file.jsonl"), offset=99)
    assert entries == []
    assert offset == 99


def _run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except AssertionError as exc:  # noqa: PERF203 - test harness
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return failures


if __name__ == "__main__":
    raise SystemExit(1 if _run() else 0)
