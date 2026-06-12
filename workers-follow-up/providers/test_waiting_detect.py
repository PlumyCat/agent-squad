#!/usr/bin/env python3
"""Standalone tests for providers.waiting_detect (S5/MYL-74).

Run: python3 providers/test_waiting_detect.py   (exit 0 = all pass)
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from providers import waiting_detect as wd  # noqa: E402


def _make(records: list[dict], age_seconds: float) -> Path:
    fh = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w")
    for record in records:
        fh.write(json.dumps(record) + "\n")
    fh.close()
    path = Path(fh.name)
    mtime = time.time() - age_seconds
    os.utime(path, (mtime, mtime))
    return path


_QUESTION = {
    "type": "assistant",
    "message": {
        "content": [
            {
                "type": "tool_use",
                "name": "SendMessage",
                "input": {
                    "to": "team-lead",
                    "summary": "Migrer les anciens enregistrements ?",
                    "message": "J'ai besoin d'une décision.",
                },
            }
        ]
    },
}
_END_TURN = {
    "type": "assistant",
    "message": {"content": [{"type": "text", "text": "J'attends ta confirmation."}]},
}
_TOOL_RESULT = {
    "type": "user",
    "message": {"content": [{"type": "tool_result", "content": "ok"}]},
}
_PLAN_APPROVAL = {
    "type": "assistant",
    "message": {
        "content": [
            {
                "type": "tool_use",
                "name": "SendMessage",
                "input": {
                    "to": "team-lead",
                    "message": {"type": "plan_approval_request", "request_id": "x"},
                },
            }
        ]
    },
}

IDLE = 60


def run() -> int:
    failures = 0

    def check(label: str, got, want_truthy: bool, want_question: str | None = None):
        nonlocal failures
        ok = bool(got) == want_truthy
        if ok and want_question is not None:
            ok = got and got.get("question") == want_question
        status = "OK" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"  [{status}] {label} -> {got}")

    # Ended turn + idle + outgoing question -> waiting.
    p = _make([_QUESTION, _END_TURN], age_seconds=120)
    check("waiting: ended+idle+question", wd.detect_waiting(p, idle_after=IDLE), True,
          "Migrer les anciens enregistrements ?")
    os.unlink(p)

    # Same content but transcript still active -> not waiting.
    p = _make([_QUESTION, _END_TURN], age_seconds=5)
    check("running: ended+ACTIVE+question", wd.detect_waiting(p, idle_after=IDLE), False)
    os.unlink(p)

    # Ended turn, idle, but no outgoing question -> not waiting.
    p = _make([_END_TURN], age_seconds=120)
    check("not-waiting: no question in tail", wd.detect_waiting(p, idle_after=IDLE), False)
    os.unlink(p)

    # Last record is a tool_result (mid-turn) -> not waiting.
    p = _make([_QUESTION, _TOOL_RESULT], age_seconds=120)
    check("not-waiting: mid-turn tool_result", wd.detect_waiting(p, idle_after=IDLE), False)
    os.unlink(p)

    # Plan approval request -> waiting.
    p = _make([_PLAN_APPROVAL, _END_TURN], age_seconds=120)
    check("waiting: plan_approval_request", wd.detect_waiting(p, idle_after=IDLE), True)
    os.unlink(p)

    # Missing / None transcript -> not waiting, no crash.
    check("safe: None transcript", wd.detect_waiting(None, idle_after=IDLE), False)

    # Piste 2 signal augmentation.
    root = Path(tempfile.mkdtemp())
    wdir = root / "signals" / "waiting"
    wdir.mkdir(parents=True)
    (wdir / "orion.json").write_text(json.dumps({"session": "orion", "message": "Décision ?"}))
    check("signal: present", wd.signal_waiting(root, "orion"), True, "Décision ?")
    check("signal: absent", wd.signal_waiting(root, "nobody"), False)
    import shutil

    shutil.rmtree(root)

    print("ALL PASS" if failures == 0 else f"{failures} FAILED")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
