# Codex Squad - Multi-Agent Bootstrap System

Multi-agent Codex orchestration system enabling task delegation to isolated workers in tmux sessions.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                     HUMAN                           │
│                       │                             │
│                       ▼                             │
│  ┌─────────────────────────────────────────────┐    │
│  │             PROPHET CODEX                   │    │
│  │            (Orchestrator)                   │    │
│  │                                             │    │
│  │  • Receives requests                        │    │
│  │  • Delegates to workers                     │    │
│  │  • Supervises and integrates                │    │
│  └─────────────────────────────────────────────┘    │
│                       │                             │
│          ┌────────────┼────────────┐                │
│          ▼            ▼            ▼                │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐       │
│  │  WORKER 1  │ │  WORKER 2  │ │  WORKER N  │       │
│  │   (tmux)   │ │   (tmux)   │ │   (tmux)   │       │
│  └────────────┘ └────────────┘ └────────────┘       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- tmux
- Codex CLI configured

### Setup

```bash
git clone https://github.com/PlumyCat/codex-prophet.git
cd codex-prophet

# Install dependencies for each CLI
cd claude-cli && uv sync && cd ..
cd context-cli && uv sync && cd ..
cd tickets-cli && uv sync && cd ..

# Install Codex skills (Squad)
./install-skills.sh
```

## Quick Start

```bash
# 1. Start Prophet Codex
./restart-prophet-codex.sh

# 2. Attach to the session
tmux attach -t prophet-codex

# 3. In Prophet Codex, delegate a task
./squad spawn --role worker --name my-task "Implement a fibonacci function"

# 4. Check the worker
./squad list
./squad capture my-task
```

## Components

### squad CLI

Tmux worker management.

```bash
./squad spawn "prompt"              # Spawn a worker
./squad spawn --name foo "prompt"   # With a name
./squad spawn --role worker "prompt" # With a role
./squad capture foo --lines 50      # View output
./squad list                        # List workers
./squad kill foo                    # Kill a worker
./squad kill-all                    # Kill all workers
```

### context-cli

Role and directive management.

```bash
./context list-roles        # List roles
./context list-directives   # List directives
./context show worker       # Display role context
./context settings worker   # Generate settings.json
./context validate worker   # Validate a role
```

### tickets-cli

Delegated task tracking.

```bash
./tickets create "Task"      # Create a ticket
./tickets list               # List tickets
./tickets show abc123        # View a ticket
./tickets assign abc123 worker # Assign a worker
./tickets update abc123 --status done # Mark as done
./tickets stats              # Statistics
```

## Structure

```
codex-prophet/
├── squad                     # Wrapper → worker manager CLI
├── claude                    # Backward-compatible wrapper
├── context                   # Wrapper → context-cli
├── tickets                   # Wrapper → tickets-cli
├── restart-prophet-codex.sh  # Startup script
├── install-skills.sh         # Installs Squad skills
├── claude-cli/               # Worker management CLI (historical directory name)
├── context-cli/              # Context management CLI
│   ├── roles/                # Role definitions
│   └── directives/           # Reusable directives
├── tickets-cli/              # Task tracking CLI
│   └── tickets/              # JSON ticket storage
├── skills/squad-*             # Codex skills (Squad)
│   ├── prophet/              # Prophet Codex management
│   ├── spawn/                # Spawn a worker
│   ├── workers/              # List workers
│   ├── capture/              # Capture output
│   ├── kill/                 # Kill workers
│   ├── status/               # System status
│   ├── ticket/               # Ticket management
│   ├── respond/              # Respond to waiting workers
│   ├── waiting/              # Signal worker waiting state
│   └── done/                 # Signal task completion
└── docs/
    ├── GUIDE.md              # Complete usage guide
    └── stories/              # User stories
```

## Codex Skills (Squad)

Global skills available from any project (`~/.codex/skills/`).

| Skill | Description |
|-------|-------------|
| `/squad:prophet` | (Re)launch Prophet Codex in tmux |
| `/squad:spawn` | Create a worker with options |
| `/squad:workers` | List active workers |
| `/squad:capture` | View worker output |
| `/squad:kill` | Kill one/all workers |
| `/squad:status` | System overview |
| `/squad:ticket` | Ticket management |
| `/squad:respond` | Respond to a waiting worker |
| `/squad:waiting` | Signal that a worker is waiting |
| `/squad:done` | Signal task completion (workers) |

### Usage Example

```bash
# From any terminal with Codex
codex

# In Codex
> /squad:status           # View system status
> /squad:spawn            # Create a worker (interactive)
> /squad:workers          # List workers
> /squad:capture codex-neon-spark # View output
```

## Documentation

- [Complete Usage Guide](docs/GUIDE.md)
- [worker manager README](claude-cli/README.md)
- [context-cli README](context-cli/README.md)
- [tickets-cli README](tickets-cli/README.md)

## How This Project Was Created

This project was automatically generated from a 6-hour Twitch video using a "Video-to-Code" pipeline:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Twitch Video   │────▶│ Frame           │────▶│ Frame Analysis  │
│  (6h, no audio) │     │ Extraction      │     │ (GPT-4 Vision)  │
│                 │     │ (ffmpeg)        │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Codex    │◀────│ BMAD Stories    │◀────│ Tutorial MD     │
│  Implementation │     │ (User Stories)  │     │ (documentation) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Steps

1. **Download**: `yt-dlp` to fetch the Twitch video
2. **Frame extraction**: `ffmpeg -vf "fps=1/5"` → 4344 frames
3. **Vision analysis**: Azure OpenAI GPT-4.1-mini analyzes frames
4. **Tutorial generation**: Structured Markdown documentation
5. **BMAD Stories**: Conversion to User Stories with BMAD workflow
6. **Implementation**: Codex implements each story

### Result

A 6-hour video transformed into a functional system with:
- 3 CLIs (codex-cli, context-cli, tickets-cli)
- 10 Codex skills
- Complete multi-agent architecture

## Credits

Based on the Multi-Codex Bootstrap tutorial by [@claudecodeonly](https://www.twitch.tv/claudecodeonly).

A big thank you for this 6-hour Twitch video presenting a truly innovative multi-agent orchestration system. The approach with Prophet Codex, tmux workers, and the ticket system is elegant and powerful.

Source video: https://www.twitch.tv/claudecodeonly/video/2657952550

## License

MIT
