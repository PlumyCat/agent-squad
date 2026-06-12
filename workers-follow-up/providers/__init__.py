"""State providers for the workers-follow-up dashboard.

Each provider exposes a ``build_state()`` returning the /api/state payload
({workers, tickets, logs, signals, generated_at}). server.py selects one at
runtime via the WFU_PROVIDER environment variable:

- WFU_PROVIDER=agent_teams (default) -> Claude Code Agent Teams (this package)
- WFU_PROVIDER=codex                 -> legacy tmux/codex backend (server.py)
"""
