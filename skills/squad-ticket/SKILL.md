---
name: squad-ticket
description: Ticket Management
allowed-tools: Bash
---

# Ticket Management

Ticket management for tracking delegated tasks.

## Available Actions

### 1. Create a ticket
```bash
./tickets create "<title>" --body "<description>"
# With assignment:
./tickets create "<title>" --assign <worker-name>
```

### 2. List tickets
```bash
./tickets list
# Filter:
./tickets list --status open
./tickets list --status in-progress
./tickets list --status blocked
./tickets list --status done
```

### 3. View a ticket
```bash
./tickets show <ticket-id>
```

### 4. Assign a worker
```bash
./tickets assign <ticket-id> <worker-name>
```

### 5. Update status
```bash
./tickets update <ticket-id> --status done
./tickets update <ticket-id> --status blocked
```

### 6. Add a comment
```bash
./tickets comment <ticket-id> "Progress update"
```

### 7. Statistics
```bash
./tickets stats
```

## Ticket States

| State | Icon | Description |
|-------|------|-------------|
| open | ○ | New, not assigned |
| in-progress | ◐ | In progress |
| blocked | ✗ | Blocked |
| done | ✓ | Completed |
