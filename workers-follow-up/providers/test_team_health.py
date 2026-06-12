#!/usr/bin/env python3
"""Tests for team_health — run: python3 -m providers.test_team_health

Stdlib only. Builds a fake ~/.claude tree under a temp dir and points the module
at it via CLAUDE_HOME-derived paths (patched directly on the module).
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from providers import team_health as th


def _setup(tmp: Path):
    """Repoint the module's PROJECTS_DIR/TEAMS_DIR at a temp tree."""
    th.PROJECTS_DIR = tmp / "projects"
    th.TEAMS_DIR = tmp / "teams"
    th.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    th.TEAMS_DIR.mkdir(parents=True, exist_ok=True)


def _make_session(tmp: Path, cwd: str, session_id: str, *, with_transcript=False, age_seconds=0.0):
    slug = th.project_slug(cwd)
    sdir = th.PROJECTS_DIR / slug / session_id
    sdir.mkdir(parents=True, exist_ok=True)
    if with_transcript:
        sub = sdir / "subagents"
        sub.mkdir(exist_ok=True)
        t = sub / "agent-abc.jsonl"
        t.write_text('{"x":1}\n', encoding="utf-8")
        if age_seconds:
            old = time.time() - age_seconds
            import os
            os.utime(t, (old, old))
    return sdir


CWD = "/Users/test/projects/demo"


def test_alive_when_session_dir_exists():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _setup(tmp)
        _make_session(tmp, CWD, "sess-1")
        cfg = {"leadSessionId": "sess-1", "cwd": CWD}
        assert th.is_team_alive(cfg) is True


def test_dead_when_session_dir_absent():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _setup(tmp)
        cfg = {"leadSessionId": "sess-missing", "cwd": CWD}
        assert th.is_team_alive(cfg) is False


def test_cwd_fallback_to_member():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _setup(tmp)
        _make_session(tmp, CWD, "sess-2")
        cfg = {"leadSessionId": "sess-2", "members": [{"name": "lead", "cwd": CWD}]}
        assert th.is_team_alive(cfg) is True


def test_fail_open_when_unresolvable():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _setup(tmp)
        # No leadSessionId / no cwd -> can't judge -> alive.
        assert th.is_team_alive({}) is True
        assert th.is_team_alive({"leadSessionId": "x"}) is True  # no cwd
        assert th.is_team_alive({"cwd": CWD}) is True            # no session id


def test_recency_window_alive_for_fresh_transcript():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _setup(tmp)
        _make_session(tmp, CWD, "sess-3", with_transcript=True, age_seconds=5)
        cfg = {"leadSessionId": "sess-3", "cwd": CWD}
        assert th.is_team_alive(cfg, max_age_seconds=3600) is True


def test_recency_window_dead_for_stale_transcript():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _setup(tmp)
        _make_session(tmp, CWD, "sess-4", with_transcript=True, age_seconds=7200)
        cfg = {"leadSessionId": "sess-4", "cwd": CWD}
        assert th.is_team_alive(cfg, max_age_seconds=3600) is False


def test_recency_window_alive_when_dir_exists_no_transcript():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _setup(tmp)
        _make_session(tmp, CWD, "sess-5", with_transcript=False)
        cfg = {"leadSessionId": "sess-5", "cwd": CWD}
        # Dir exists but empty -> just spun up -> alive even with a window.
        assert th.is_team_alive(cfg, max_age_seconds=3600) is True


def test_prune_dead_teams_preserves_order_and_filters():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _setup(tmp)
        _make_session(tmp, CWD, "live-1")
        _make_session(tmp, CWD, "live-2")
        configs = {
            "alpha": {"leadSessionId": "live-1", "cwd": CWD},
            "beta": {"leadSessionId": "dead-x", "cwd": CWD},   # no dir -> dead
            "gamma": {"leadSessionId": "live-2", "cwd": CWD},
        }
        result = th.prune_dead_teams(
            ["alpha", "beta", "gamma"], load_config=configs.get
        )
        assert result == ["alpha", "gamma"]


def test_prune_keeps_team_with_unloadable_config():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _setup(tmp)

        def loader(name):
            if name == "boom":
                raise RuntimeError("read error")
            return None  # falsy -> keep

        result = th.prune_dead_teams(["boom", "none"], load_config=loader)
        assert result == ["boom", "none"]  # both kept (fail open)


def _run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    # snapshot module globals to restore between tests
    orig = (th.PROJECTS_DIR, th.TEAMS_DIR)
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
        finally:
            th.PROJECTS_DIR, th.TEAMS_DIR = orig
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return failures


if __name__ == "__main__":
    raise SystemExit(1 if _run() else 0)
