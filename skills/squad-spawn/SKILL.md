---
name: squad-spawn
description: Spawn Worker
allowed-tools: Bash
---

# Spawn Worker

Creates a new worker in an isolated tmux session.

## Parameters to Collect

1. **Name** (optional): Descriptive name for the worker
2. **Role** (optional): Predefined context (`worker`, `prophet-claude`)
3. **Ticket** (optional): Ticket ID to associate
4. **Skill** (optional): Skills to activate at startup (repeatable)
5. **Task** (required): The prompt/instruction for the worker

## Commands

```bash
# Basic
./squad spawn --name <name> "<task>"

# With role (recommended)
./squad spawn --name <name> --role worker "<task>"

# With ticket (recommended for tracking)
./squad spawn --name <name> --role worker --ticket <ticket-id> "<task>"

# With skills (for autonomy)
./squad spawn --skill ralph-loop:ralph-loop "<task>"

# Combine multiple skills
./squad spawn -s bmad:dev-story -s ralph-loop:ralph-loop "<task>"
```

## Ralph Loop Mode (--ralph)

For autonomous execution without intervention:

```bash
./squad spawn --ralph "Long running task"
./squad spawn --ralph --role worker --ticket abc123 "Complete feature"
```

Note: Avoid parentheses `()` in the prompt with --ralph (bash escaping issue).

## Useful Skills for Workers

| Skill | Effect |
|-------|--------|
| `ralph-loop:ralph-loop` | Continues automatically without waiting |
| `bmad:dev-story` | Structured development workflow |
| `epct` | Explore-Plan-Code-Test workflow |

## Recommended Workflow

```bash
# 1. Create the ticket
./tickets create "<task-title>"

# 2. Spawn with the ticket
./squad spawn --name my-worker --role worker --ticket abc123 "<task>"

# 3. Verify
./squad list
```

## Notes

- Codex workers are launched with bypassed approvals/sandbox for autonomy
- Claude workers can still be launched with `--agent claude`
- The `worker` role includes completion instructions for updating tickets
- Use descriptive names and clear instructions
