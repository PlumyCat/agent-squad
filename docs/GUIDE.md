# Codex Squad - Usage Guide

> Complete documentation for the multi-agent Codex orchestration system

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Key Concepts](#key-concepts)
6. [Workflows](#workflows)
7. [Command Reference](#command-reference)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

### What is Codex Squad?

A system for orchestrating **multiple Codex instances** working in parallel. A main Codex ("Squad Orchestrator") delegates tasks to isolated workers in tmux sessions.

### Why use this system?

| Problem | Solution |
|---------|----------|
| Complex tasks = saturated context | Delegate to specialized workers |
| Sequential work = slow | Asynchronous parallel workers |
| Context lost on restart | Persistent roles and directives |
| No task tracking | Integrated ticket system |

### Use Cases

- **Parallel development**: One worker on backend, one on frontend
- **Code review**: Specialized worker with review directives
- **Massive refactoring**: Multiple workers on different modules
- **Documentation**: Dedicated worker for doc generation

---

## Architecture

### Global Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         HUMAN                                   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   SQUAD ORCHESTRATOR                        │    │
│  │                   (Orchestrator)                        │    │
│  │                                                         │    │
│  │  • Receives human requests                              │    │
│  │  • Breaks down into sub-tasks                           │    │
│  │  • Delegates to workers                                 │    │
│  │  • Supervises and integrates                            │    │
│  │                                                         │    │
│  │  Tools: codex-cli, context-cli, tickets-cli            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                     │
│            ┌──────────────┼──────────────┐                      │
│            │              │              │                      │
│            ▼              ▼              ▼                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │   WORKER 1   │ │   WORKER 2   │ │   WORKER N   │             │
│  │   (tmux)     │ │   (tmux)     │ │   (tmux)     │             │
│  │              │ │              │ │              │             │
│  │ • Specific   │ │ • Specific   │ │ • Specific   │             │
│  │   task       │ │   task       │ │   task       │             │
│  │ • Isolated   │ │ • Isolated   │ │ • Isolated   │             │
│  │   context    │ │   context    │ │   context    │             │
│  │ • Auto-exit  │ │ • Auto-exit  │ │ • Auto-exit  │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Components

```
bootstrap/
│
├── codex-cli/          # Tmux worker management
│   ├── spawn            # Create a worker
│   ├── capture          # View output
│   ├── list             # List workers
│   └── kill             # Terminate a worker
│
├── context-cli/         # Context management
│   ├── roles/           # Role definitions
│   ├── directives/      # Reusable rules
│   ├── show             # Display a context
│   └── settings         # Generate settings.json
│
├── tickets-cli/         # Task tracking
│   ├── tickets/         # JSON storage
│   ├── create           # Create a ticket
│   ├── assign           # Assign a worker
│   └── update           # Change status
│
└── scripts/
    └── restart-squad-orchestrator.sh
```

### Data Flow

```
                    ┌─────────────┐
                    │ context-cli │
                    │             │
                    │ roles/      │
                    │ directives/ │
                    └──────┬──────┘
                           │
                           │ generates context
                           ▼
┌─────────────────┐     ┌─────────────┐     ┌─────────────┐
│ tickets-cli │◄────│ codex-cli  │────►│    tmux     │
│             │     │             │     │             │
│ • tracking  │     │ • spawn     │     │ • sessions  │
│ • states    │     │ • capture   │     │ • isolation │
│ • history   │     │ • kill      │     │ • send-keys │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## Installation

### Prerequisites

```bash
# Python 3.11+
python3 --version  # >= 3.11

# uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# tmux
sudo apt install tmux  # Ubuntu/Debian
brew install tmux      # macOS

# Codex CLI
# Must be installed and configured with an active account
codex --version
```

### System Installation

```bash
# Clone or create the folder
mkdir -p ~/workspace/bootstrap
cd ~/workspace/bootstrap

# Initialize worker manager CLI
mkdir claude-cli && cd claude-cli
uv init
uv add click
# ... copy main.py

# Initialize context-cli
cd .. && mkdir context-cli && cd context-cli
uv init
uv add click pyyaml
# ... copy main.py and create roles/, directives/

# Initialize tickets-cli (optional)
cd .. && mkdir tickets-cli && cd tickets-cli
uv init
uv add click
# ... copy main.py

# Create wrapper scripts
cd ..
# ... create squad, context, tickets scripts
chmod +x squad context tickets restart-squad-orchestrator.sh
```

---

## Quick Start

### 1. Start Squad Orchestrator

```bash
cd ~/workspace/bootstrap
./restart-squad-orchestrator.sh

# Or manually:
tmux new-session -d -s squad-orchestrator "codex --no-alt-screen"
tmux attach -t squad-orchestrator
```

### 2. Delegate your first task

In Squad Orchestrator:

```bash
# Spawn a worker
./squad spawn --name hello-worker "Say 'Hello World', report completion, then stop"

# Check that it's running
./squad list

# View its output
./squad capture hello-worker

# Clean up
./squad kill hello-worker
```

### 3. Use roles

```bash
# View available roles
./context list-roles

# Spawn with a role
./squad spawn --role worker --name code-worker "Implement a fibonacci function in Python"

# The worker receives the "worker" role context
```

---

## Key Concepts

### Squad Orchestrator vs Workers

| Aspect | Squad Orchestrator | Worker Codex |
|--------|----------------|---------------|
| **Role** | Orchestrator | Executor |
| **Lifespan** | Permanent | Temporary |
| **Context** | Complete (system) | Specialized (task) |
| **Actions** | Delegate, supervise | Implement, report |
| **Tmux session** | `squad-orchestrator` | `codex-neon-spark` |

### Tmux Sessions

```
┌─────────────────────────────────────────────────────┐
│ tmux server                                         │
│                                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐   │
│  │ squad-orchestrator      │  │ codex-abc12345     │   │
│  │ (attached)          │  │ (detached)          │   │
│  │                     │  │                     │   │
│  │ Human ◄──► Codex   │  │ Worker Codex       │   │
│  │                     │  │ (autonomous)        │   │
│  └─────────────────────┘  └─────────────────────┘   │
│                                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐   │
│  │ codex-def67890     │  │ codex-ghi11111     │   │
│  │ (detached)          │  │ (detached)          │   │
│  └─────────────────────┘  └─────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Roles and Directives

```yaml
# Role structure
roles/worker.yaml:
  name: worker
  description: "Worker for delegated tasks"
  prompt: |
    You are a Worker Codex. Complete the task, report completion, and stop.

    CONSTRAINTS:
    - Focus on the given task
    - Don't start new tasks
    - Report completion and stop when done

  directives:
    - base           # Includes directives/base.yaml
    - code-quality   # Includes directives/code-quality.yaml

# Directive structure
directives/code-quality.yaml:
  name: code-quality
  description: "Code quality standards"
  content: |
    ## Code Standards
    - Tests for each function
    - Descriptive names
    - No dead code
```

### Ticket System

```
┌─────────────────────────────────────────────────────────┐
│                    TICKET LIFECYCLE                     │
│                                                         │
│   ┌──────┐    ┌─────────────┐    ┌─────────┐    ┌────┐  │
│   │ OPEN │───►│IN-PROGRESS  │───►│ BLOCKED │───►│DONE│  │
│   └──────┘    └─────────────┘    └─────────┘    └────┘  │
│       │              │                 │           ▲    │
│       │              │                 │           │    │
│       └──────────────┴─────────────────┴───────────┘    │
│                                                         │
│   create          assign            update       update │
│                   (auto)                                │
└─────────────────────────────────────────────────────────┘
```

---

## Workflows

### Basic Workflow: Simple Delegation

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  1. Human requests a complex task                       │
│     │                                                   │
│     ▼                                                   │
│  2. Squad Orchestrator analyzes and decomposes              │
│     │                                                   │
│     ├─────────────────────────────────────────┐         │
│     ▼                                         ▼         │
│  3. ./squad spawn "Sub-task 1"    ./squad spawn "Sub-task 2"
│     │                                         │         │
│     ▼                                         ▼         │
│  4. Worker 1 executes              Worker 2 executes    │
│     │                                         │         │
│     ▼                                         ▼         │
│  5. ./squad capture worker1    ./squad capture worker2│
│     │                                         │         │
│     └─────────────────┬───────────────────────┘         │
│                       ▼                                 │
│  6. Squad Orchestrator integrates results                   │
│     │                                                   │
│     ▼                                                   │
│  7. Human receives complete deliverable                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Advanced Workflow: With Tickets

```bash
# Squad Orchestrator receives: "Add JWT authentication"

# 1. Create the ticket
./tickets create "Implement JWT Auth" --body "Backend + Frontend"

# 2. Spawn and assign
./squad spawn --role worker --name auth-backend "Implement JWT backend"
./tickets assign <ticket-id> auth-backend

# 3. Supervise
./squad capture auth-backend --lines 50
./tickets show <ticket-id>

# 4. When complete
./tickets update <ticket-id> --status done
```

### Workflow: Code Review

```bash
# Define a reviewer role
# context-cli/roles/code-reviewer.yaml

# Spawn the reviewer
./squad spawn --role code-reviewer --name reviewer-pr123 \
  "Review the changes in src/auth.py for security issues"

# Capture the report
./squad capture reviewer-pr123 > review-report.md
```

---

## Command Reference

### codex-cli

| Command | Description | Example |
|---------|-------------|---------|
| `spawn` | Create a worker | `./squad spawn "task"` |
| `spawn --name` | Named worker | `./squad spawn --name my-worker "task"` |
| `spawn --role` | With a role | `./squad spawn --role worker "task"` |
| `capture` | View output | `./squad capture my-worker` |
| `capture --lines` | Last N lines | `./squad capture my-worker --lines 100` |
| `list` | List workers | `./squad list` |
| `kill` | Kill a worker | `./squad kill my-worker` |
| `kill-all` | Kill all | `./squad kill-all --force` |

### context-cli

| Command | Description | Example |
|---------|-------------|---------|
| `show` | Display context | `./context show worker` |
| `list-roles` | List roles | `./context list-roles` |
| `list-directives` | List directives | `./context list-directives` |
| `settings` | Generate settings.json | `./context settings orchestrator` |

### tickets-cli

| Command | Description | Example |
|---------|-------------|---------|
| `create` | Create a ticket | `./tickets create "Title"` |
| `create --body` | With description | `./tickets create "Title" --body "Details"` |
| `create --assign` | Create + assign | `./tickets create "Title" --assign worker` |
| `list` | List tickets | `./tickets list` |
| `list --status` | Filter by status | `./tickets list --status open` |
| `list --assigned` | Filter by worker | `./tickets list --assigned my-worker` |
| `show` | Ticket details | `./tickets show abc123` |
| `assign` | Assign a worker | `./tickets assign abc123 my-worker` |
| `update --status` | Change status | `./tickets update abc123 --status done` |
| `comment` | Add a comment | `./tickets comment abc123 "Progress update"` |
| `delete` | Delete a ticket | `./tickets delete abc123 --force` |
| `stats` | Global statistics | `./tickets stats` |

---

## Best Practices

### For Squad Orchestrator

```
✅ DO:
- Delegate non-trivial tasks
- Give clear instructions to workers
- Check regularly with capture
- Use descriptive session names

❌ DON'T:
- Do implementation work
- Wait for a worker to finish (non-blocking)
- Manually kill tmux sessions
- Attach to worker sessions
```

### For Workers

```
✅ DO:
- Focus on the assigned task
- Report completion and stop when done
- Report blockers clearly

❌ DON'T:
- Start new unasked tasks
- Modify files out of scope
- Stay active after completion
```

### Session Naming

```
Good:
- auth-backend-worker
- feature-42-implementation
- code-review-pr-123

Bad:
- worker1
- test
- codex-session
```

---

## Troubleshooting

### "Session not found"

```bash
# Check existing sessions
tmux list-sessions

# The worker may have finished (auto-exit)
# Relaunch if needed
./squad spawn --name <name> "task"
```

### "No active workers"

```bash
# Normal if all have finished
# Check tmux history
tmux list-sessions -a
```

### Stuck worker

```bash
# Capture to see the state
./squad capture <worker> --lines 100

# If really stuck, kill and respawn
./squad kill <worker>
./squad spawn --name <worker> "corrected task"
```

### Context not applied

```bash
# Check that the role exists
./context list-roles

# Check the role content
./context show <role>

# Regenerate settings.json if needed
./context settings <role> > settings.json
```

---

## Appendices

### Useful tmux Commands

```bash
# List sessions
tmux list-sessions

# Attach to a session (debug only)
tmux attach -t <session>

# Detach (Ctrl+B then D)

# Capture manually
tmux capture-pane -t <session> -p

# Send a command
tmux send-keys -t <session> "command" Enter
```

### Complete Session Example

```bash
# Terminal 1: Squad Orchestrator
./restart-squad-orchestrator.sh
tmux attach -t squad-orchestrator

# In Squad Orchestrator:
> Implement a Redis cache system for the API

# Squad Orchestrator responds and delegates:
./squad spawn --role worker --name cache-impl \
  "Implement Redis caching in src/api/cache.py:
   - Connection pool
   - get/set methods
   - TTL support
   - Error handling"

./squad spawn --role worker --name cache-tests \
  "Write tests for Redis cache in tests/test_cache.py"

# Squad Orchestrator checks:
./squad list
# cache-impl (running)
# cache-tests (running)

./squad capture cache-impl --lines 30
# ... see progress ...

# When done:
./squad capture cache-impl > /tmp/cache-impl-result.md
./squad capture cache-tests > /tmp/cache-tests-result.md

# Integrate and continue
```

---

*Documentation generated from the Multi-Codex Bootstrap tutorial by @claudecodeonly*
*Last updated: 2025-01-28*
