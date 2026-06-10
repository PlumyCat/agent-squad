---
name: squad-kill
description: Kill Workers
allowed-tools: Bash
---

# Kill Workers

Terminates one or more workers.

## Commands

### Kill a specific worker
```bash
./squad kill <worker-name>
```

### Kill all workers
```bash
./squad kill-all
# Skip confirmation:
./squad kill-all --force
```

## Before Killing

1. Check active workers:
   ```bash
   ./squad list
   ```

2. Capture output if needed:
   ```bash
   ./squad capture <worker-name> --lines 1000
   ```

3. Update ticket if applicable:
   ```bash
   ./tickets update <ticket-id> --status blocked
   ```

## Use Cases

- **Blocked worker**: No longer responding or in a loop
- **Wrong task**: Incorrect instructions
- **Cleanup**: End of session
- **Error**: Worker in error state

## Notes

- `kill` does not delete associated tickets
- Workers should clearly report completion; the orchestrator can then kill the tmux session if it remains open
- `kill-all` does NOT kill `prophet-codex`
