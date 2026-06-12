#!/usr/bin/env python3
"""End-to-end validation harness for the Claude Squad dashboard backend.

Boots the real HTTP server (server.Handler) in-process on an isolated, ephemeral
port — never 8787 (held by the LaunchAgent) — and exercises the live API the UI
depends on:

* ``GET /api/state``         — contract shape + multi-team aggregation
* ``POST /api/workers/{id}/kill`` — kill flow for both modes:
    - in-process Agent Teams id (``name@team``) → refused 409, never a 500
    - malformed / injection id                  → rejected 400, no tmux call

It imports the server module directly rather than shelling out, so no change to
server.py (port is hardcoded there) is needed and the test is hermetic. stdlib
only; safe to run anytime — it kills nothing real (only in-process/invalid ids).

Run:  python3 -m providers.test_e2e
"""

from __future__ import annotations

import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer

# Import the real server handler + provider. Support running as a module
# (providers.test_e2e) or as a script from the workers-follow-up dir.
try:
    import server  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - path shim
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import server  # type: ignore


def _boot_server() -> tuple[ThreadingHTTPServer, str]:
    """Start server.Handler on an ephemeral localhost port. Returns (srv, base_url)."""
    # Port 0 => OS picks a free ephemeral port; guaranteed not to clash with 8787.
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, f"http://127.0.0.1:{port}"


def _get_json(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _post_json(url: str) -> tuple[int, dict]:
    req = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, (json.loads(body) if body else {})


# ── checks ────────────────────────────────────────────────────────────────

def check_state_contract(base: str) -> list[str]:
    """GET /api/state returns the full UI contract. Returns failure messages."""
    fails: list[str] = []
    status, payload = _get_json(base + "/api/state")
    if status != 200:
        return [f"/api/state status {status} != 200"]

    for key in ("workers", "tickets", "logs", "generated_at"):
        if key not in payload:
            fails.append(f"/api/state missing key '{key}'")
    if not isinstance(payload.get("workers"), list):
        fails.append("workers is not a list")
    if not isinstance(payload.get("logs"), dict):
        fails.append("logs is not a dict")

    # Per-worker contract (only if any worker present — empty is valid).
    for w in payload.get("workers", []):
        for key in ("id", "name", "status", "team"):
            if key not in w:
                fails.append(f"worker {w.get('id', '?')} missing '{key}'")
                break
        # killable is enriched by server.build_state() and read by the UI to
        # enable/disable the kill button; it must be present and boolean.
        if not isinstance(w.get("killable"), bool):
            fails.append(f"worker {w.get('id')} killable missing or not bool ({w.get('killable')!r})")
    return fails


def check_multi_team_aggregation(base: str) -> list[str]:
    """Workers/tickets carry a team and aggregate across discovered teams."""
    fails: list[str] = []
    _, payload = _get_json(base + "/api/state")
    workers = payload.get("workers", [])
    teams = {w.get("team") for w in workers if w.get("team")}
    # We can't assume >1 team on every host, but every worker must name its team
    # so the aggregated view can group them.
    for w in workers:
        if not w.get("team"):
            fails.append(f"worker {w.get('id')} has no team (breaks multi-team grouping)")
            break
    # Informational, not a failure: report how many teams aggregated.
    print(f"  [info] aggregated workers={len(workers)} across teams={sorted(teams) or '∅'}")
    return fails


_VALID_LOG_KINDS = {"cmd", "info", "ok", "warn", "err", "dim"}


def check_logs_contract(base: str) -> list[str]:
    """logs is a dict keyed by worker id; entries match {id, time, kind, text}."""
    fails: list[str] = []
    _, payload = _get_json(base + "/api/state")
    logs = payload.get("logs")
    if not isinstance(logs, dict):
        return ["logs is not a dict"]
    total = 0
    for worker_id, entries in logs.items():
        if not isinstance(entries, list):
            fails.append(f"logs[{worker_id}] is not a list")
            continue
        for e in entries[:5]:  # spot-check the first few of each
            total += 1
            for key in ("id", "time", "kind", "text"):
                if key not in e:
                    fails.append(f"log entry in {worker_id} missing '{key}'")
                    break
            if e.get("kind") not in _VALID_LOG_KINDS:
                fails.append(f"log entry in {worker_id} has invalid kind {e.get('kind')!r}")
    print(f"  [info] logs for {len(logs)} workers, {total} entries spot-checked")
    return fails


def check_linear_url_on_tickets(base: str) -> list[str]:
    """Tickets expose a clickable linear_url pointing at linear.app."""
    fails: list[str] = []
    _, payload = _get_json(base + "/api/state")
    tickets = payload.get("tickets", [])
    if not tickets:
        print("  [info] no tickets to check linear_url on")
        return fails
    with_url = [t for t in tickets if t.get("linear_url")]
    for t in with_url:
        url = t["linear_url"]
        if not (isinstance(url, str) and url.startswith("https://linear.app/")):
            fails.append(f"ticket {t.get('id')} linear_url malformed: {url!r}")
    print(f"  [info] {len(with_url)}/{len(tickets)} tickets carry a linear_url")
    return fails


def check_kill_in_process_refused(base: str) -> list[str]:
    """An Agent Teams id is refused with 409, structured body, never 500."""
    fails: list[str] = []
    status, payload = _post_json(base + "/api/workers/nova@workers-follow-up/kill")
    if status != 409:
        fails.append(f"in-process kill status {status} != 409")
    if payload.get("ok") is not False:
        fails.append("in-process kill ok should be False")
    if payload.get("reason") != "in-process":
        fails.append(f"in-process kill reason={payload.get('reason')} != in-process")
    return fails


def check_kill_injection_rejected(base: str) -> list[str]:
    """A malformed/injection id is rejected (400/404), never executed."""
    fails: list[str] = []
    # URL-encode the nasty bits so it reaches the handler as one path segment.
    import urllib.parse

    bad = urllib.parse.quote("nova@team; rm -rf /", safe="")
    status, payload = _post_json(base + f"/api/workers/{bad}/kill")
    if status >= 500:
        fails.append(f"injection id caused {status} (should be 4xx)")
    if payload.get("ok") is not False:
        fails.append("injection id should be refused (ok False)")
    return fails


def _run() -> int:
    httpd, base = _boot_server()
    print(f"E2E server on {base} (ephemeral port, not 8787)")
    checks = [
        ("state contract", check_state_contract),
        ("multi-team aggregation", check_multi_team_aggregation),
        ("logs contract", check_logs_contract),
        ("linear_url on tickets", check_linear_url_on_tickets),
        ("kill in-process refused (409)", check_kill_in_process_refused),
        ("kill injection rejected (4xx)", check_kill_injection_rejected),
    ]
    total_fails = 0
    try:
        for name, fn in checks:
            try:
                fails = fn(base)
            except Exception as exc:  # noqa: BLE001 - report, don't crash the run
                fails = [f"exception: {exc!r}"]
            if fails:
                total_fails += len(fails)
                print(f"FAIL {name}")
                for f in fails:
                    print(f"     - {f}")
            else:
                print(f"PASS {name}")
    finally:
        httpd.shutdown()

    print(f"\n{len(checks)} checks run, {total_fails} failures")
    return total_fails


if __name__ == "__main__":
    raise SystemExit(1 if _run() else 0)
