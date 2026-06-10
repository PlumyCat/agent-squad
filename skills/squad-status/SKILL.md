---
name: squad-status
description: System Status
allowed-tools: Bash
---

# System Status

Overview of the Codex Squad system.

## Commands to Execute

### 1. Prophet Codex Status
```bash
tmux has-session -t prophet-codex 2>/dev/null && echo "Prophet Codex: RUNNING" || echo "Prophet Codex: STOPPED"
```

### 2. Active Workers
```bash
./squad list
```

### 3. In-Progress Tickets
```bash
./tickets list --status in-progress
./tickets list --status blocked
```

### 4. Ticket Statistics
```bash
./tickets stats
```

### 5. Workers Waiting for Response
```bash
echo "=== Workers waiting ==="
ls ./signals/waiting/*.json 2>/dev/null || echo "No workers waiting"
```

```bash
# Details of waiting tickets
./tickets list --status waiting
```

```bash
# View signal details (if present)
for f in ./signals/waiting/*.json; do
  [ -f "$f" ] && echo "--- $(basename $f .json) ---" && cat "$f"
done 2>/dev/null
```

## Output Format

```
=== Multi-Codex System Status ===

Prophet Codex: [RUNNING/STOPPED]

Active workers: X
  - codex-neon-spark (running)
  - codex-solar-forge (running)

Workers waiting: X
  ⏳ codex-auth: "OAuth or JWT?" (ticket abc123)

Tickets:
  ○ Open: X
  ◐ In-progress: X
  ✗ Blocked: X
  ⏳ Waiting: X
  ✓ Done: X

Tmux sessions: X total
```

## Recommended Actions

- Prophet STOPPED → `/squad:prophet`
- Tickets BLOCKED → Investigate
- Tickets WAITING → `/squad:respond <session> "response"`
- No workers but tickets in-progress → Check `/squad:capture`
