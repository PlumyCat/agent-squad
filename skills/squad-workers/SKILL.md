---
name: squad-workers
description: Workers Management
allowed-tools: Bash
---

# Workers Management

Lists and manages active workers.

## Commands

### List active workers
```bash
./squad list
```

### View all tmux sessions
```bash
tmux list-sessions 2>/dev/null || echo "No active tmux sessions"
```

## Output Format

For each worker, display:
- Session name
- Status (running/stopped)
- Activity duration

## Quick Actions

1. Capture output: `/squad:capture <name>`
2. Kill a worker: `/squad:kill <name>`
3. Kill all: `./squad kill-all`
4. New worker: `/squad:spawn`

## Notes

- Codex sessions prefixed with `codex-` unless explicitly named
- Squad Orchestrator: `squad-orchestrator` session
