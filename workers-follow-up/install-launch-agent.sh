#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.${USER}.claude-squad-ui"
OLD_LABEL="com.${USER}.codex-squad-ui"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
OLD_PLIST="$HOME/Library/LaunchAgents/$OLD_LABEL.plist"
LOG_DIR="$HOME/Library/Logs"
UID_VALUE="$(id -u)"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

if launchctl list | grep -q "$OLD_LABEL"; then
  launchctl bootout "gui/$UID_VALUE/$OLD_LABEL" >/dev/null 2>&1 || true
fi
if [ -f "$OLD_PLIST" ]; then
  rm -f "$OLD_PLIST"
  echo "Removed old service $OLD_LABEL"
fi

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>cd "$ROOT_DIR" &amp;&amp; exec python3 workers-follow-up/server.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$ROOT_DIR</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/$LABEL.out.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/$LABEL.err.log</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$UID_VALUE" "$PLIST" >/dev/null 2>&1 || true

if lsof -ti tcp:8787 >/dev/null 2>&1; then
  lsof -ti tcp:8787 | xargs kill >/dev/null 2>&1 || true
  sleep 1
fi

launchctl bootstrap "gui/$UID_VALUE" "$PLIST"
launchctl kickstart -k "gui/$UID_VALUE/$LABEL"

echo "Installed $LABEL"
echo "URL: http://127.0.0.1:8787"
echo "Logs:"
echo "  $LOG_DIR/$LABEL.out.log"
echo "  $LOG_DIR/$LABEL.err.log"
