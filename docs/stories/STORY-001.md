# STORY-001: Multi-Claude Bootstrap System

**Epic:** Multi-Agent Orchestration
**Priority:** Must Have
**Story Points:** 13 (to be broken down into sub-stories)
**Status:** Not Started
**Assigned To:** Unassigned
**Created:** 2025-01-28
**Sprint:** 1

---

## User Story

As a **solo developer**
I want to **orchestrate multiple Claude instances via tmux**
So that **I can delegate tasks to specialized Claude workers and multiply my productivity**

---

## Description

### Background
The tutorial by @claudecodeonly (6h on Twitch) demonstrates an advanced multi-agent Claude orchestration pattern. The system allows a main "Squad Orchestrator" to delegate tasks to isolated Claude workers in tmux sessions, creating a parallel and asynchronous workflow.

### Target Architecture

```
                    ┌─────────────────┐
                    │  Squad Orchestrator │ ← Human interface
                    │   (Principal)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  Worker  │  │  Worker  │  │  Manager │
        │  (tmux)  │  │  (tmux)  │  │  (tmux)  │
        └──────────┘  └──────────┘  └──────────┘
```

### Main Components

1. **claude-cli** - Python CLI to spawn/manage workers
   - `spawn`: Create a worker in a tmux session
   - `capture`: Capture a worker's output
   - `list`: List active workers
   - `kill` / `kill-all`: Terminate workers

2. **context-cli** - Role and context management
   - YAML roles (orchestrator.yaml, worker.yaml, manager.yaml)
   - Reusable modular directives
   - settings.json generation for permissions

3. **tickets-cli** - Asynchronous ticket system
   - Ticket creation/management
   - Worker assignment
   - Notifications and ACK

4. **Persistence system**
   - CLAUDE.md for initial context
   - Canonical memories per named Claude
   - roles/ and directives/ for configuration

---

## Scope

### In Scope

- [ ] **Phase 1: claude-cli** (MVP)
  - Spawn Claude workers in tmux
  - Capture worker output
  - List and kill sessions
  - Worker auto-exit

- [ ] **Phase 2: context-cli**
  - roles/ and directives/ structure
  - `show <role>` command to display context
  - settings.json generation
  - Base roles: orchestrator, worker

- [ ] **Phase 3: tickets-cli**
  - CRUD tickets
  - Worker assignment
  - States: open, in-progress, blocked, done

- [ ] **Phase 4: Integration**
  - Startup scripts (restart-claude.sh)
  - Squad Orchestrator → Worker workflow
  - Complete documentation

### Out of Scope (v1)

- Voice control (FastAPI + Whisper)
- Twitch streaming
- Git worktrees for isolation
- Advanced managers (middle-manager, stream-manager)

---

## User Flow

### Main Flow

1. Developer launches Squad Orchestrator with `./restart-squad-orchestrator.sh`
2. Squad Orchestrator receives a complex task
3. Squad Orchestrator delegates via `claude-cli spawn --role worker "Implement X"`
4. Worker executes autonomously in its tmux session
5. Squad Orchestrator checks progress via `claude-cli capture <worker>`
6. Worker finishes and exits automatically (auto-exit)
7. Squad Orchestrator integrates the result and continues

### Concrete Example

```bash
# Squad Orchestrator receives: "Add an authentication system"

# Squad Orchestrator delegates:
claude-cli spawn --role worker --name auth-worker \
  "Implement JWT authentication in /src/auth.
   Create login/logout/refresh endpoints."

# Squad Orchestrator continues with something else...

# Later, Squad Orchestrator checks:
claude-cli capture auth-worker --lines 50

# If done, Squad Orchestrator integrates the work
```

---

## Acceptance Criteria

### claude-cli

- [ ] `spawn` creates a tmux session with Claude in interactive mode
- [ ] `spawn --role <role>` applies the role context
- [ ] `spawn --name <name>` allows naming the session
- [ ] `capture <session> --lines N` displays the last N lines
- [ ] `list` displays all active claude-* sessions
- [ ] `kill <session>` properly terminates a session
- [ ] `kill-all` terminates all claude-* sessions
- [ ] Workers can auto-exit with `/exit`
- [ ] Prompts are sent via `tmux send-keys`

### context-cli

- [ ] `roles/*.yaml` and `directives/*.yaml` structure
- [ ] `show <role>` combines prompt + directives
- [ ] `list-roles` displays available roles
- [ ] `list-directives` displays directives
- [ ] `settings <role>` generates a valid settings.json
- [ ] `orchestrator` role defined with constraints
- [ ] `worker` role defined for delegated tasks

### tickets-cli

- [ ] `create <title> --body <description>` creates a ticket
- [ ] `list` displays tickets with their state
- [ ] `show <ticket-id>` displays details
- [ ] `assign <ticket-id> <worker>` assigns a worker
- [ ] `update <ticket-id> --status <status>` changes state
- [ ] Supported states: open, in-progress, blocked, done

### Integration

- [ ] `restart-squad-orchestrator.sh` script functional
- [ ] Squad Orchestrator can spawn workers
- [ ] Workers receive proper context via `--role`
- [ ] README documentation for each CLI

---

## Technical Notes

### Tech Stack

- **Python 3.11+** with **uv** for dependency management
- **Click** for CLIs
- **tmux** for session isolation
- **YAML** for role configuration

### Folder Structure

```
bootstrap/
├── claude-cli/
│   ├── pyproject.toml
│   ├── main.py
│   └── README.md
├── context-cli/
│   ├── pyproject.toml
│   ├── main.py
│   ├── roles/
│   │   ├── orchestrator.yaml
│   │   └── worker.yaml
│   ├── directives/
│   │   ├── base.yaml
│   │   └── persistent-memory.yaml
│   └── README.md
├── tickets-cli/
│   ├── pyproject.toml
│   ├── main.py
│   ├── tickets/          # JSON/YAML storage
│   └── README.md
├── CLAUDE.md             # Squad Orchestrator context (can be empty if using context-cli)
├── restart-squad-orchestrator.sh
└── memories/             # Persistent memories per Claude
```

### Key tmux Commands

```bash
# Create session
tmux new-session -d -s <name> "claude"

# Send prompt
tmux send-keys -t <name> "prompt text" Enter

# Capture output
tmux capture-pane -t <name> -p | tail -n 50

# List sessions
tmux list-sessions | grep "^claude-"

# Kill session
tmux kill-session -t <name>
```

### YAML Role Format

```yaml
# roles/worker.yaml
name: worker
description: Worker Claude for delegated tasks
prompt: |
  You are a Worker Claude. Complete the assigned task and exit.

  CONSTRAINTS:
  - Focus on the specific task given
  - Do not start new tasks
  - Exit when done with /exit

directives:
  - base
  - code-quality
```

### Security

- Never expose API keys in logs
- Isolate each worker in its own tmux session
- Restrictive permissions via settings.json
- Rate limiting to avoid excessive spawns

---

## Dependencies

### System Prerequisites

- tmux installed and configured
- Python 3.11+ with uv
- Claude Code CLI installed and configured
- Claude account with sufficient credits

### Python Dependencies

```toml
[dependencies]
click = "^8.1"
pyyaml = "^6.0"
```

### Implementation Order

1. **claude-cli** (no dependencies)
2. **context-cli** (no dependencies)
3. **tickets-cli** (optional, can use context-cli for roles)
4. **Integration** (depends on the 3 CLIs)

---

## Definition of Done

- [ ] Code implemented and committed
- [ ] Manual tests passed for each command
- [ ] README documented for each CLI
- [ ] Complete workflow tested: Squad Orchestrator → spawn → capture → integration
- [ ] At least 2 roles defined (orchestrator, worker)
- [ ] restart-squad-orchestrator.sh script functional
- [ ] No errors during normal execution

---

## Story Points Breakdown

| Component | Points | Complexity |
|-----------|--------|------------|
| claude-cli | 5 | Medium - tmux + Click |
| context-cli | 3 | Simple - YAML + templating |
| tickets-cli | 3 | Simple - Basic CRUD |
| Integration | 2 | Simple - shell scripts |
| **Total** | **13** | |

**Rationale:** The complete system is too large for a single story. Recommendation: break down into 4 sub-stories (one per component).

---

## Sub-Stories

| ID | Title | Points | Priority | Dependencies |
|----|-------|--------|----------|--------------|
| [STORY-001a](STORY-001a.md) | Implement claude-cli | 5 | Must Have | - |
| [STORY-001b](STORY-001b.md) | Implement context-cli | 3 | Should Have | 001a |
| [STORY-001c](STORY-001c.md) | Implement tickets-cli | 3 | Could Have | 001a |
| [STORY-001d](STORY-001d.md) | Integration and documentation | 2 | Must Have | 001a, 001b |

### Recommended Implementation Order

```
STORY-001a (claude-cli)     ──────┐
         │                        │
         ▼                        ▼
STORY-001b (context-cli)    STORY-001c (tickets-cli)
         │                        │
         └────────┬───────────────┘
                  ▼
         STORY-001d (integration)
```

---

## Resources

- **Extracted tutorial**: `tutorial.md` (488 KB, 362 frames analyzed)
- **Source video**: https://www.twitch.tv/claudecodeonly/video/2657952550
- **Frames**: `/tmp/claude/.../twitch_frames/frames/` (4344 images)

---

## Progress Tracking

**Status History:**
- 2025-01-28: Story created

**Actual Effort:** TBD

---

**This story was created following the Multi-Claude Bootstrap tutorial by @claudecodeonly**
