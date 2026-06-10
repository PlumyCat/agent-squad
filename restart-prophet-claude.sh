#!/bin/bash
# Restart Prophet Codex with proper context
# Usage: ./restart-prophet-claude.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Prophet Codex Bootstrap ==="
echo ""

# Generate settings.json from context-cli
echo "Generating settings.json for prophet-claude role..."
cd context-cli
uv run python main.py settings prophet-claude -o ../settings.json
cd ..
echo "  ✓ settings.json created"

# Kill existing prophet-codex session if any
if tmux has-session -t prophet-codex 2>/dev/null; then
    echo "Killing existing prophet-codex session..."
    tmux kill-session -t prophet-codex
    echo "  ✓ Old session terminated"
fi

# Start new session with codex (bypass approvals/sandbox for autonomous local orchestration)
echo "Starting Prophet Codex..."
tmux new-session -d -s prophet-codex -c "$SCRIPT_DIR" "codex --dangerously-bypass-approvals-and-sandbox --ask-for-approval never --sandbox danger-full-access --cd '$SCRIPT_DIR' --no-alt-screen"

# Wait for Codex to start
sleep 2

# Send initial context
INIT_PROMPT="You are now Prophet Codex. Your context has been loaded from context-cli.

Available commands:
- ./squad spawn --name <name> \"task\" - Spawn a Codex worker
- ./squad spawn --role worker \"task\" - Spawn with role context
- ./squad spawn --agent claude --role worker \"task\" - Spawn a Claude worker
- ./squad capture <session> - See worker output
- ./squad list - List active workers
- ./squad kill <session> - Kill a worker

Ready to receive tasks. What would you like me to help with?"

tmux send-keys -t prophet-codex "$INIT_PROMPT" Enter

echo ""
echo "=== Prophet Codex Started ==="
echo ""
echo "Attach with:"
echo "  tmux attach -t prophet-codex"
echo ""
echo "Or run commands directly:"
echo "  ./squad list"
echo "  ./squad spawn --role worker \"your task\""
