---
name: squad-prophet
description: Prophet Codex Management
allowed-tools: Bash
---

# Prophet Codex Management

Manages (re)starting Prophet Codex in a dedicated tmux session.

## Launch/Relaunch Prophet Codex

```bash
./restart-prophet-codex.sh
```

The absolute path allows launching from any folder.

This script:
1. Generates `settings.json` from context-cli with the prophet-claude role
2. Kills the old tmux session if it exists
3. Starts a new `prophet-codex` session with Codex
4. Sends the initialization prompt

## Useful Commands

```bash
# Check if Prophet Codex is running
tmux has-session -t prophet-codex 2>/dev/null && echo "Running" || echo "Not running"

# Attach to the session
tmux attach -t prophet-codex

# View state without attaching
tmux capture-pane -t prophet-codex -p | tail -20

# Kill the session
tmux kill-session -t prophet-codex
```

## Architecture

```
You (normal terminal)
  └── codex (this conversation = Prophet)
        ├── /squad:spawn → codex-neon-spark tmux session
        ├── /squad:spawn → codex-solar-forge tmux session
        └── /squad:spawn → codex-bright-orbit tmux session
```

Prophet Codex can also run in tmux for long autonomous sessions.
