#!/bin/bash
# Install Squad skills to global Codex skills directory
# Usage: ./install-skills.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_SRC="$SCRIPT_DIR/skills"
SKILLS_DST="${CODEX_HOME:-$HOME/.codex}/skills"

echo "=== Squad Skills Installation for Codex ==="
echo ""

# Check source exists
if [ ! -d "$SKILLS_SRC" ]; then
    echo "Error: Skills source not found: $SKILLS_SRC"
    exit 1
fi

# Create destination if needed
mkdir -p "$SKILLS_DST"

# Copy skills
echo "Installing skills to $SKILLS_DST..."
for skill_dir in "$SKILLS_SRC"/squad-*; do
    [ -d "$skill_dir" ] || continue
    skill_name="$(basename "$skill_dir")"
    rm -rf "$SKILLS_DST/$skill_name"
    cp -R "$skill_dir" "$SKILLS_DST/$skill_name"
done

echo ""
echo "=== Installed Skills ==="
find "$SKILLS_SRC" -maxdepth 1 -type d -name 'squad-*' -exec basename {} \; | sort | while read skill; do
    echo "  $skill"
done

echo ""
echo "Done! Skills are now available globally in Codex."
echo ""
echo "Usage examples:"
echo "  squad-status   - System status"
echo "  squad-spawn    - Spawn a worker"
echo "  squad-workers  - List workers"
