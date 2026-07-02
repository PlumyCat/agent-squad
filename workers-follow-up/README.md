# Workers Follow-Up

Local Claude Squad monitoring UI exported from Claude Design.

## Run

```bash
./workers-follow-up/run.sh
```

Then open:

```text
http://127.0.0.1:8787
```

## Data sources

By default the backend reads **Claude Code Agent Teams** data under `~/.claude`:

- `teams/<team>/config.json` — team membership (the teammates shown as workers).
- `tasks/<team>/*.json` — tasks, mapped to dashboard tickets.
- `projects/<slug>/<session>/subagents/agent-*.jsonl` — per-teammate transcripts,
  parsed into worker status and log lines.

A legacy tmux/codex backend remains available behind `WFU_PROVIDER=codex` for the
older split-panes setup.

## API

- `GET /api/state` returns workers, tickets, logs, and signals.
- `GET /api/workers/<id>/logs` returns recent log lines for one worker.
- `POST /api/workers/<id>/kill` kills a worker — only effective for legacy
  split-panes tmux sessions; in-process Agent Teams teammates are not killable.

The backend is read-only for state; UI actions still update local browser state only.

Browser notifications use the local Claude Squad icon bundled at
`assets/claude-pet-icon.png`.

## Install On macOS

```bash
./workers-follow-up/install-launch-agent.sh
```

The LaunchAgent (`com.$USER.claude-squad-ui`) starts the UI at login and
restarts it if it exits.

> Migrating from the old `codex-squad-ui` service is automatic: the install
> script detects a loaded `com.$USER.codex-squad-ui` service, boots it out,
> and removes its plist before installing the renamed service.

If a previous instance is already holding port 8787, reload the service so it
picks up new code:

```bash
launchctl kickstart -k "gui/$(id -u)/com.$USER.claude-squad-ui"
```

To uninstall:

```bash
./workers-follow-up/uninstall-launch-agent.sh
```
