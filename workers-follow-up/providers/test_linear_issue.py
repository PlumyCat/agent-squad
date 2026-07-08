#!/usr/bin/env python3
"""Tests for the worker <-> Linear issue link — run: python3 -m providers.test_linear_issue

Covers:
- .squad-runs/<session>.meta.json persistence/read (as written by
  `claude-cli spawn --linear`) via server.session_meta / server.linear_issue_for.
- Linear ID extraction from a ticket title via server.linear_issue_from_title.
- Priority of meta.json over the title regex, and the linear_url builder.

Stdlib only. server.RUNS_DIR is monkeypatched to a temp dir so no real
.squad-runs/ files are read or written.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

try:
    import server  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - path shim
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import server  # type: ignore


def _with_runs_dir(runs_dir: Path):
    original = server.RUNS_DIR
    server.RUNS_DIR = runs_dir
    return original


# ----- linear_issue_from_title ---------------------------------------------


def test_linear_issue_from_title_matches():
    assert server.linear_issue_from_title("MYL-181 S-01: Do the thing") == "MYL-181"


def test_linear_issue_from_title_no_match():
    assert server.linear_issue_from_title("Just a plain title") is None


def test_linear_issue_from_title_none_input():
    assert server.linear_issue_from_title(None) is None


def test_linear_issue_from_title_respects_letter_bound():
    # {2,6} letters: a 7-letter prefix before the dash must not match.
    assert server.linear_issue_from_title("ABCDEFG-123 not a valid id") is None


def test_linear_issue_from_title_two_letter_min():
    assert server.linear_issue_from_title("AB-1 short prefix") == "AB-1"


# ----- session_meta / linear_issue_for --------------------------------------


def test_session_meta_reads_persisted_file():
    with tempfile.TemporaryDirectory() as tmp:
        runs_dir = Path(tmp)
        original = _with_runs_dir(runs_dir)
        try:
            (runs_dir / "claude-w1.meta.json").write_text(
                json.dumps(
                    {
                        "session": "claude-w1",
                        "linear_issue": "MYL-167",
                        "ticket_id": "52750936",
                    }
                ),
                encoding="utf-8",
            )
            meta = server.session_meta("claude-w1")
            assert meta is not None
            assert meta["linear_issue"] == "MYL-167"
            assert meta["ticket_id"] == "52750936"
        finally:
            server.RUNS_DIR = original


def test_session_meta_missing_file_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        original = _with_runs_dir(Path(tmp))
        try:
            assert server.session_meta("claude-does-not-exist") is None
        finally:
            server.RUNS_DIR = original


def test_session_meta_no_session_returns_none():
    assert server.session_meta(None) is None
    assert server.session_meta("") is None


def test_linear_issue_for_prefers_meta_over_title():
    with tempfile.TemporaryDirectory() as tmp:
        runs_dir = Path(tmp)
        original = _with_runs_dir(runs_dir)
        try:
            (runs_dir / "claude-w2.meta.json").write_text(
                json.dumps(
                    {
                        "session": "claude-w2",
                        "linear_issue": "MYL-200",
                        "ticket_id": None,
                    }
                ),
                encoding="utf-8",
            )
            # Title regex would resolve to MYL-181; meta.json must win.
            issue = server.linear_issue_for("claude-w2", "MYL-181 S-01: Do the thing")
            assert issue == "MYL-200"
        finally:
            server.RUNS_DIR = original


def test_linear_issue_for_falls_back_to_title():
    with tempfile.TemporaryDirectory() as tmp:
        original = _with_runs_dir(Path(tmp))
        try:
            issue = server.linear_issue_for(
                "claude-no-meta", "MYL-181 S-01: Do the thing"
            )
            assert issue == "MYL-181"
        finally:
            server.RUNS_DIR = original


def test_linear_issue_for_no_meta_no_title_match():
    with tempfile.TemporaryDirectory() as tmp:
        original = _with_runs_dir(Path(tmp))
        try:
            assert server.linear_issue_for("claude-no-meta", "no id here") is None
        finally:
            server.RUNS_DIR = original


# ----- linear_url ------------------------------------------------------------


def test_linear_url_builds_expected_link():
    assert server.linear_url("MYL-181") == "https://linear.app/mylinearwk/issue/MYL-181"


def test_linear_url_none_when_no_issue():
    assert server.linear_url(None) is None


def _run() -> int:
    tests = [
        v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)
    ]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return failures


if __name__ == "__main__":
    raise SystemExit(1 if _run() else 0)
