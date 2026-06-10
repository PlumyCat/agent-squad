# tickets-cli

CLI for tracking tasks delegated to workers.

## Installation

```bash
cd tickets-cli
uv sync
```

## Concept

```
Prophet Codex                          Worker Codex
      │                                       │
      ├─► tickets create "JWT Auth"           │
      │   └─► Ticket #abc123 created          │
      │                                       │
      ├─► tickets assign abc123 auth-worker   │
      │                                       │
      ├─► claude spawn --name auth-worker ... │
      │                                       │
      │                                       ├─► (working...)
      │                                       │
      ├─► tickets show abc123                 │
      │   └─► Status: in-progress             │
      │                                       │
      │                                       ├─► tickets update abc123 --status done
      │                                       │
      └─► tickets list                        │
          └─► abc123: done ✓                  │
```

## Commands

### create

Creates a new ticket.

```bash
# Basic
uv run python main.py create "Implement JWT auth"

# With description
uv run python main.py create "Fix login" --body "Users can't login with email"

# With immediate assignment
uv run python main.py create "Add tests" --assign test-worker
```

### list

Lists tickets.

```bash
# All tickets
uv run python main.py list

# Filter by status
uv run python main.py list --status open
uv run python main.py list --status in-progress

# Filter by worker
uv run python main.py list --assigned auth-worker
```

### show

Displays ticket details.

```bash
uv run python main.py show abc123

# Supports partial IDs
uv run python main.py show abc
```

### update

Updates a ticket.

```bash
# Change status
uv run python main.py update abc123 --status done
uv run python main.py update abc123 --status blocked

# Update description
uv run python main.py update abc123 --body "New description"

# Change title
uv run python main.py update abc123 --title "New title"
```

### assign

Assigns a worker to a ticket.

```bash
uv run python main.py assign abc123 auth-worker
```

Note: If the ticket is "open", it automatically changes to "in-progress".

### comment

Adds a comment to a ticket.

```bash
uv run python main.py comment abc123 "Started implementation, 50% done"
```

### delete

Deletes a ticket.

```bash
uv run python main.py delete abc123

# Without confirmation
uv run python main.py delete abc123 --force
```

### stats

Displays statistics.

```bash
uv run python main.py stats
```

## States

| State | Icon | Description |
|-------|------|-------------|
| open | ○ | New ticket, not yet assigned |
| in-progress | ◐ | Being processed |
| blocked | ✗ | Blocked (waiting for info, dependency) |
| done | ✓ | Completed |

## Storage

Tickets are stored as JSON in `tickets/`:

```
tickets-cli/
└── tickets/
    ├── abc12345.json
    └── def67890.json
```

Ticket format:

```json
{
  "id": "abc12345",
  "title": "Implement JWT authentication",
  "body": "Create login/logout endpoints",
  "status": "in-progress",
  "assigned_to": "auth-worker",
  "created_at": "2025-01-28T15:30:00Z",
  "updated_at": "2025-01-28T16:45:00Z",
  "history": [
    {
      "timestamp": "2025-01-28T15:30:00Z",
      "action": "created",
      "details": "Ticket created"
    },
    {
      "timestamp": "2025-01-28T15:35:00Z",
      "action": "assigned",
      "details": "Assigned to auth-worker"
    }
  ]
}
```

## Integration with codex-cli

Typical workflow:

```bash
# 1. Prophet creates a ticket
./tickets create "Implement feature X" --body "Details..."

# 2. Prophet assigns and spawns the worker
./tickets assign abc123 feature-worker
./squad spawn --name feature-worker --role worker "Implement feature X"

# 3. Prophet checks the status
./tickets list
./tickets show abc123

# 4. Worker marks as done
./tickets update abc123 --status done
```
