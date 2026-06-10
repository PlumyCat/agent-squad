---
name: squad-orchestrator
description: Squad Orchestrator Management
allowed-tools: Bash
---

# Squad Orchestrator Management

Manages (re)starting Squad Orchestrator in a dedicated tmux session.

## Launch/Relaunch Squad Orchestrator

```bash
./restart-squad-orchestrator.sh
```

The absolute path allows launching from any folder.

This script:
1. Generates `settings.json` from context-cli with the orchestrator role
2. Kills the old tmux session if it exists
3. Starts a new `squad-orchestrator` session with Codex
4. Sends the initialization prompt

## Useful Commands

```bash
# Check if Squad Orchestrator is running
tmux has-session -t squad-orchestrator 2>/dev/null && echo "Running" || echo "Not running"

# Attach to the session
tmux attach -t squad-orchestrator

# View state without attaching
tmux capture-pane -t squad-orchestrator -p | tail -20

# Kill the session
tmux kill-session -t squad-orchestrator
```

## Architecture

```
You (normal terminal)
  └── codex (this conversation = Squad Orchestrator)
        ├── /squad:spawn → codex-neon-spark tmux session
        ├── /squad:spawn → codex-solar-forge tmux session
        └── /squad:spawn → codex-bright-orbit tmux session
```

Squad Orchestrator can also run in tmux for long autonomous sessions.
