# claude-cli

CLI for spawning and managing workers in tmux sessions.

Default backend: **Claude** (`claude --dangerously-skip-permissions`, sessions
prefixed `claude-`). Codex remains available via `--agent codex` or
`SQUAD_AGENT=codex`.

## Installation

```bash
cd claude-cli
uv sync
```

## Commands

### spawn

Creates a new worker in a tmux session.

```bash
# Basic spawn (auto-generated name)
uv run python main.py spawn "Implement a fibonacci function"

# Spawn with custom name
uv run python main.py spawn --name fib-worker "Implement fibonacci"

# Spawn with a role (requires context-cli)
uv run python main.py spawn --role worker "Fix the bug in auth.py"

# Force a model (cost control)
uv run python main.py spawn --model opus "Complex refactoring"
```

#### Worker model (cost control)

Claude workers are launched with an explicit `--model` so they never inherit
the user's default model (Opus/Fable — expensive and slow for worker tasks).

Resolution order: `--model` flag > `SQUAD_MODEL` env var > default `sonnet`.

```bash
uv run python main.py spawn "task"                 # → claude --model sonnet
uv run python main.py spawn -m opus "hard task"    # → claude --model opus
SQUAD_MODEL=haiku uv run python main.py spawn "t"  # → claude --model haiku
```

Codex workers get no default model; `--model` is forwarded as-is when given.

### capture

Captures a worker's output.

```bash
# Capture the last 30 lines (default)
uv run python main.py capture my-worker

# Capture the last 100 lines
uv run python main.py capture my-worker --lines 100
```

### list

Lists all active workers.

```bash
uv run python main.py list
```

### kill

Terminates a specific worker.

```bash
uv run python main.py kill my-worker
```

### kill-all

Terminates all workers.

```bash
# With confirmation
uv run python main.py kill-all

# Without confirmation
uv run python main.py kill-all --force
```

### send

Sends text to a worker (advanced).

```bash
# Send /exit to terminate
uv run python main.py send my-worker "/exit"

# Send an additional instruction
uv run python main.py send my-worker "Continue with the next step"
```

## Workflow Example

```bash
# 1. Spawn a worker
uv run python main.py spawn --name auth-impl "Implement JWT authentication"

# 2. Check that it's running
uv run python main.py list

# 3. View its progress
uv run python main.py capture auth-impl --lines 50

# 4. When done, clean up
uv run python main.py kill auth-impl
```

## Notes

- Sessions are prefixed with the agent name (`claude-` by default, `codex-` with `--agent codex`)
- Use `capture` rather than `tmux attach` to monitor
- Workers can auto-terminate with `/exit`
