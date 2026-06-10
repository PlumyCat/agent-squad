#!/bin/bash
# Compatibility wrapper with the Codex-oriented name.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/restart-prophet-claude.sh" "$@"
