---
name: squad-done
description: Done - Task Completion
allowed-tools: Bash
---

# Done - Task Completion

Signals the completion of a task assigned to a worker.

## Usage

This skill is intended for **workers** to signal that they have completed their task.

## Actions to Perform

### 1. Ask for ticket ID (if not known)

### 2. Update the ticket
```bash
./tickets update <ticket-id> --status done
./tickets comment <ticket-id> "Task completed by worker"
```

### 3. Report completion

IMPORTANT: Always make the completion state explicit so Prophet Codex can capture the result and clean up the tmux session if needed.

## Workflow

```
Worker completes its task
       │
       ▼
   /squad:done <ticket-id>
       │
       ├─► tickets update → done
       ├─► tickets comment → "Completed"
       │
       ▼
   Final completion report
       │
       ▼
   Prophet captures result and cleans up session
```

## Notes

- This skill does not clean up tmux automatically
- If no ticket, clearly report that the task is complete
