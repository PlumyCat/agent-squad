---
name: squad-status
description: System Status
allowed-tools: Bash
---

# System Status

Overview of the Codex Squad system.

## Commands to Execute

### 1. Squad Orchestrator Status
```bash
tmux has-session -t squad-orchestrator 2>/dev/null && echo "Squad Orchestrator: RUNNING" || echo "Squad Orchestrator: STOPPED"
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

Squad Orchestrator: [RUNNING/STOPPED]

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

- Squad Orchestrator STOPPED → `/squad:orchestrator`
- Tickets BLOCKED → Investigate
- Tickets WAITING → `/squad:respond <session> "response"`
- No workers but tickets in-progress → Check `/squad:capture`
