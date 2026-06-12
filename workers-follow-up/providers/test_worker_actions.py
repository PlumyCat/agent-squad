#!/usr/bin/env python3
"""Tests for worker_actions — run: python3 -m providers.test_worker_actions

Stdlib only. tmux is stubbed via monkeypatching the module's ``_run_tmux`` so
the suite runs deterministically with or without tmux installed, and never
kills a real session.
"""

from __future__ import annotations

import subprocess

from providers import worker_actions as wa


class _FakeTmux:
    """Replacement for _run_tmux. Records calls; answers from a session set."""

    def __init__(self, existing: set[str]):
        self.existing = set(existing)
        self.calls: list[tuple[str, ...]] = []
        self.kill_fails: set[str] = set()

    def __call__(self, *args: str) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if args and args[0] == "has-session":
            target = args[2] if len(args) > 2 else ""
            rc = 0 if target in self.existing else 1
            return subprocess.CompletedProcess(args, rc, "", "")
        if args and args[0] == "kill-session":
            target = args[2] if len(args) > 2 else ""
            if target in self.kill_fails:
                return subprocess.CompletedProcess(args, 1, "", "can't find session")
            self.existing.discard(target)
            return subprocess.CompletedProcess(args, 0, "", "")
        return subprocess.CompletedProcess(args, 0, "", "")


def _install(existing):
    fake = _FakeTmux(existing)
    wa._run_tmux = fake  # type: ignore[assignment]
    return fake


# ----- validate_session / injection ---------------------------------------

def test_validate_session_accepts_legacy_names():
    assert wa.validate_session("codex-w1")
    assert wa.validate_session("claude-abc.123_x")


def test_validate_session_rejects_injection_and_teams_ids():
    for bad in [
        "nova@workers-follow-up",         # Agent Teams id
        "codex-x; rm -rf /",              # shell injection
        "codex-$(whoami)",                # command substitution
        "../etc/passwd",                  # path traversal
        "codex w1",                       # space
        "plain",                          # no prefix
        "",                               # empty
    ]:
        assert not wa.validate_session(bad), bad


# ----- can_kill ------------------------------------------------------------

def test_can_kill_true_for_live_tmux_worker():
    _install({"codex-w1"})
    assert wa.can_kill({"id": "codex-w1", "session": "codex-w1"}) is True


def test_can_kill_false_for_in_process_worker():
    _install({"codex-w1"})  # session exists, but this worker isn't it
    assert wa.can_kill({"id": "nova@workers-follow-up", "session": "nova@workers-follow-up"}) is False


def test_can_kill_false_when_session_absent():
    _install(set())
    assert wa.can_kill({"id": "codex-gone", "session": "codex-gone"}) is False


def test_can_kill_handles_non_dict_and_missing_keys():
    _install(set())
    assert wa.can_kill({}) is False
    assert wa.can_kill({"id": "nova@team"}) is False


# ----- kill_worker ---------------------------------------------------------

def test_kill_worker_kills_live_tmux_session():
    fake = _install({"codex-w1"})
    res = wa.kill_worker("team", "codex-w1")
    assert res["ok"] is True
    assert res["killed"] is True
    assert res["mode"] == "tmux"
    assert ("kill-session", "-t", "codex-w1") in fake.calls
    assert "codex-w1" not in fake.existing


def test_kill_worker_refuses_in_process_teams_id():
    fake = _install({"codex-w1"})
    res = wa.kill_worker("workers-follow-up", "nova@workers-follow-up")
    assert res["ok"] is False
    assert res["reason"] == "in-process"
    assert res["mode"] == "in-process"
    # No tmux command must have been issued for an in-process worker.
    assert fake.calls == []


def test_kill_worker_refuses_plain_name_as_in_process():
    fake = _install(set())
    res = wa.kill_worker("workers-follow-up", "nova")
    assert res["ok"] is False
    assert res["reason"] == "in-process"
    assert res["worker"] == "nova@workers-follow-up"
    assert fake.calls == []


def test_kill_worker_rejects_malformed_teams_id():
    fake = _install(set())
    res = wa.kill_worker("team", "nova@a@b")
    assert res["ok"] is False
    assert res["reason"] == "invalid"
    assert fake.calls == []


def test_kill_worker_rejects_injection_via_at_sign_path():
    # Contains '@' so routed as Agent Teams id; must be rejected as malformed,
    # never reaching tmux.
    fake = _install(set())
    res = wa.kill_worker("team", "nova@team; rm -rf /")
    assert res["ok"] is False
    assert res["reason"] == "invalid"
    assert fake.calls == []


def test_kill_worker_not_found_for_valid_but_dead_session():
    fake = _install(set())
    res = wa.kill_worker("team", "codex-ghost")
    assert res["ok"] is False
    assert res["reason"] == "not-found"
    assert res["session"] == "codex-ghost"
    # has-session probed, but no kill issued.
    assert ("has-session", "-t", "codex-ghost") in fake.calls
    assert not any(c[0] == "kill-session" for c in fake.calls)


def test_kill_worker_reports_tmux_error():
    fake = _install({"codex-w1"})
    fake.kill_fails.add("codex-w1")
    res = wa.kill_worker("team", "codex-w1")
    assert res["ok"] is False
    assert res["reason"] == "tmux-error"


def test_kill_worker_empty_identifier_invalid():
    fake = _install(set())
    res = wa.kill_worker("team", "")
    assert res["ok"] is False
    assert res["reason"] == "invalid"
    assert fake.calls == []


def _run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    original = wa._run_tmux
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
        finally:
            wa._run_tmux = original  # restore between tests
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return failures


if __name__ == "__main__":
    raise SystemExit(1 if _run() else 0)
