# STORY-001d: Integration and Documentation

**Epic:** Multi-Agent Orchestration
**Priority:** Must Have
**Story Points:** 2
**Status:** Not Started
**Assigned To:** Unassigned
**Created:** 2025-01-28
**Sprint:** 1
**Parent:** STORY-001
**Depends On:** STORY-001a, STORY-001b

---

## User Story

As a **solo developer**
I want to **have an integrated and documented Multi-Claude system**
So that **I can easily get started and understand how to use the system**

---

## Description

### Background
This story finalizes the system by integrating the CLIs together, creating startup scripts, and documenting the complete workflow. It's the "glue" that makes the system production-ready.

### Deliverables

1. `restart-squad-orchestrator.sh` script to start Squad Orchestrator
2. claude-cli + context-cli integration (--role flag)
3. Wrapper scripts to simplify commands
4. Complete workflow documentation
5. Basic CLAUDE.md for Squad Orchestrator

---

## Scope

### In Scope

- Squad Orchestrator startup script
- --role integration between claude-cli and context-cli
- Wrapper scripts (claude, context, tickets)
- Main README with complete workflow
- Minimal bootstrap CLAUDE.md
- Complete session example

### Out of Scope

- Automated installation (documentation only)
- Automated tests
- CI/CD

---

## Acceptance Criteria

### Startup Script

- [ ] `./restart-squad-orchestrator.sh` starts Squad Orchestrator
- [ ] Applies the orchestrator role context
- [ ] Generates settings.json from context-cli
- [ ] Can be relaunched without issues (idempotent)

### claude-cli + context-cli Integration

- [ ] `claude spawn --role worker "prompt"` works
- [ ] Role context is injected into the prompt
- [ ] Works without --role (default behavior)

### Wrapper Scripts

- [ ] `./claude <command>` equivalent to `cd claude-cli && uv run python main.py <command>`
- [ ] `./context <command>` equivalent to `cd context-cli && uv run python main.py <command>`
- [ ] `./tickets <command>` equivalent to `cd tickets-cli && uv run python main.py <command>`
- [ ] Scripts are executable (chmod +x)

### Documentation

- [ ] Main README.md with:
  - [ ] System overview
  - [ ] Installation prerequisites
  - [ ] Quick start (5 min)
  - [ ] Complete workflow documented
  - [ ] Command reference
- [ ] Minimal CLAUDE.md for Squad Orchestrator

---

## Technical Notes

### Final Structure

```
bootstrap/
├── README.md                     # Main documentation
├── CLAUDE.md                     # Squad Orchestrator context (minimal)
├── restart-squad-orchestrator.sh     # Startup script
├── claude                        # Wrapper → claude-cli
├── context                       # Wrapper → context-cli
├── tickets                       # Wrapper → tickets-cli
├── claude-cli/
│   └── ...
├── context-cli/
│   └── ...
└── tickets-cli/
    └── ...
```

### restart-squad-orchestrator.sh

```bash
#!/bin/bash
# Restart Squad Orchestrator with proper context

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Generating settings.json..."
cd context-cli && uv run python main.py settings orchestrator > ../settings.json
cd ..

echo "Starting Squad Orchestrator..."
# Kill existing if any
tmux kill-session -t orchestrator 2>/dev/null || true

# Start new session
tmux new-session -d -s orchestrator "claude --settings settings.json"

echo "Squad Orchestrator started!"
echo "Attach with: tmux attach -t orchestrator"
```

### Wrapper Scripts

```bash
#!/bin/bash
# claude - wrapper for claude-cli
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/claude-cli"
exec uv run python main.py "$@"
```

### --role Integration in claude-cli

```python
# In spawn(), add:
if role:
    # Get context from context-cli
    result = subprocess.run(
        ["uv", "run", "python", "../context-cli/main.py", "show", role],
        capture_output=True, text=True, cwd=Path(__file__).parent
    )
    if result.returncode == 0:
        context = result.stdout
        full_prompt = f"{context}\n\n---\n\nTASK:\n{prompt}"
    else:
        click.echo(f"Warning: Could not load role '{role}'", err=True)
        full_prompt = prompt
else:
    full_prompt = prompt
```

### Minimal CLAUDE.md

```markdown
# Squad Orchestrator

You are Squad Orchestrator, the orchestrator of a multi-Claude system.

## Quick Reference

- Spawn worker: `./claude spawn --role worker "task"`
- Capture output: `./claude capture <session>`
- List workers: `./claude list`
- Kill worker: `./claude kill <session>`

## Constraints

- NEVER do implementation work - delegate to workers
- NEVER block waiting for workers
- NEVER manually kill tmux sessions

## Context

Full context is managed by context-cli. See `./context show orchestrator`.
```

### README.md Structure

```markdown
# Multi-Claude Bootstrap System

Orchestrate multiple Claude instances for parallel, asynchronous work.

## Overview

[ASCII architecture diagram]

## Prerequisites

- Python 3.11+
- uv package manager
- tmux
- Claude Code CLI configured

## Quick Start

1. Clone and setup
2. Start Squad Orchestrator
3. Delegate your first task

## Workflow

### Basic Delegation
[Complete example]

### Using Tickets
[Example with tickets]

## Command Reference

### claude-cli
[All commands]

### context-cli
[All commands]

### tickets-cli
[All commands]

## Troubleshooting

[Common issues]
```

---

## Dependencies

### Prerequisites

- STORY-001a (claude-cli): Required
- STORY-001b (context-cli): Required for --role
- STORY-001c (tickets-cli): Optional (wrapper script if present)

---

## Definition of Done

- [ ] `./restart-squad-orchestrator.sh` works
- [ ] `./claude spawn --role worker "test"` works
- [ ] Wrapper scripts created and executable
- [ ] README.md complete
- [ ] Minimal CLAUDE.md created
- [ ] Complete workflow tested end-to-end

---

## Test Plan

### End-to-End Test

```bash
# 1. Start Squad Orchestrator
./restart-squad-orchestrator.sh
tmux attach -t orchestrator

# 2. In Squad Orchestrator, delegate a task
./claude spawn --role worker --name test-worker "List files in /tmp and exit"

# 3. Check the worker
./claude list
./claude capture test-worker

# 4. Create a ticket (if tickets-cli present)
./tickets create "Test task"
./tickets list

# 5. Clean up
./claude kill-all --force
```

---

## Progress Tracking

**Status History:**
- 2025-01-28: Story created

---

**End of Sprint 1** - Multi-Claude Bootstrap System operational!
