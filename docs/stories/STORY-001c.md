# STORY-001c: Implement tickets-cli

**Epic:** Multi-Agent Orchestration
**Priority:** Could Have
**Story Points:** 3
**Status:** Completed
**Assigned To:** Unassigned
**Created:** 2025-01-28
**Sprint:** 1
**Parent:** STORY-001
**Depends On:** STORY-001a

---

## User Story

As a **solo developer**
I want to **track tasks delegated to workers via a ticket system**
So that **I can follow progress and coordinate asynchronous work**

---

## Description

### Background
The tickets-cli allows managing tasks asynchronously. When Squad Orchestrator delegates a task, it creates a ticket. The worker is assigned to the ticket and updates its state. This allows tracking work in progress, blockers, and history.

### Workflow

```
Squad Orchestrator                          Worker
   │                                │
   ├─► tickets create "JWT Auth"    │
   │   └─► Ticket #abc123 created   │
   │                                │
   ├─► tickets assign abc123 auth-worker
   │                                │
   ├─► claude spawn --name auth-worker "..."
   │                                │
   │                                ├─► (working...)
   │                                │
   ├─► tickets show abc123          │
   │   └─► Status: in-progress      │
   │                                │
   │                                ├─► tickets update abc123 --status done
   │                                │
   └─► tickets list                 │
       └─► abc123: done ✓           │
```

---

## Scope

### In Scope

- CRUD tickets (create, list, show, update)
- Worker assignment
- States: open, in-progress, blocked, done
- Simple JSON storage (one file per ticket)
- State change history

### Out of Scope

- Notifications/pings between Claudes
- Ticket subscriptions
- ACK system
- Database (sticking with JSON files)

---

## Acceptance Criteria

### create command

- [ ] `tickets create "Title"` creates a ticket with auto-generated ID
- [ ] `tickets create "Title" --body "Description"` adds a description
- [ ] Returns the created ticket ID
- [ ] Initial state: open

### list command

- [ ] `tickets list` displays all tickets
- [ ] Format: ID, title, state, assigned to
- [ ] `tickets list --status open` filters by state
- [ ] Displays "No tickets" if empty

### show command

- [ ] `tickets show <id>` displays full details
- [ ] Includes: title, description, state, assigned, history
- [ ] Clear error if ticket doesn't exist

### update command

- [ ] `tickets update <id> --status <status>` changes state
- [ ] Valid states: open, in-progress, blocked, done
- [ ] Adds an entry to history
- [ ] Error if invalid state

### assign command

- [ ] `tickets assign <id> <worker>` assigns a worker
- [ ] Updates the "assigned_to" field
- [ ] Automatically changes to "in-progress" if state was "open"

### Storage

- [ ] `tickets/` folder created automatically
- [ ] One JSON file per ticket: `tickets/<id>.json`
- [ ] Readable and manually editable format

---

## Technical Notes

### Project Structure

```
bootstrap/tickets-cli/
├── pyproject.toml
├── main.py
├── README.md
└── tickets/              # Created automatically
    ├── abc123.json
    └── def456.json
```

### Ticket JSON Format

```json
{
  "id": "abc123",
  "title": "Implement JWT authentication",
  "body": "Create login/logout/refresh endpoints with JWT tokens",
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
    },
    {
      "timestamp": "2025-01-28T15:35:00Z",
      "action": "status_change",
      "from": "open",
      "to": "in-progress"
    }
  ]
}
```

### main.py - Structure

```python
#!/usr/bin/env python3
"""Tickets CLI - Track delegated tasks."""

import click
import json
import uuid
from pathlib import Path
from datetime import datetime

TICKETS_DIR = Path(__file__).parent / "tickets"

def ensure_tickets_dir():
    TICKETS_DIR.mkdir(exist_ok=True)

def generate_ticket_id() -> str:
    return uuid.uuid4().hex[:8]

def load_ticket(ticket_id: str) -> dict:
    path = TICKETS_DIR / f"{ticket_id}.json"
    if not path.exists():
        raise click.ClickException(f"Ticket not found: {ticket_id}")
    with open(path) as f:
        return json.load(f)

def save_ticket(ticket: dict):
    path = TICKETS_DIR / f"{ticket['id']}.json"
    with open(path, 'w') as f:
        json.dump(ticket, f, indent=2)

def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

@click.group()
def cli():
    """Tickets CLI - Track delegated tasks."""
    ensure_tickets_dir()

@cli.command()
@click.argument("title")
@click.option("--body", "-b", default="", help="Ticket description")
def create(title: str, body: str):
    """Create a new ticket."""
    ticket = {
        "id": generate_ticket_id(),
        "title": title,
        "body": body,
        "status": "open",
        "assigned_to": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "history": [
            {"timestamp": now_iso(), "action": "created", "details": "Ticket created"}
        ]
    }
    save_ticket(ticket)
    click.echo(f"Created ticket: {ticket['id']}")
    click.echo(f"  Title: {title}")

@cli.command("list")
@click.option("--status", "-s", default=None, help="Filter by status")
def list_tickets(status: str):
    """List all tickets."""
    tickets = []
    for path in TICKETS_DIR.glob("*.json"):
        with open(path) as f:
            ticket = json.load(f)
            if status is None or ticket['status'] == status:
                tickets.append(ticket)

    if not tickets:
        click.echo("No tickets")
        return

    for t in tickets:
        assigned = t['assigned_to'] or 'unassigned'
        status_icon = "✓" if t['status'] == 'done' else "○"
        click.echo(f"{status_icon} {t['id']}: {t['title']} [{t['status']}] → {assigned}")

@cli.command()
@click.argument("ticket_id")
def show(ticket_id: str):
    """Show ticket details."""
    ticket = load_ticket(ticket_id)

    click.echo(f"# {ticket['title']}")
    click.echo(f"ID: {ticket['id']}")
    click.echo(f"Status: {ticket['status']}")
    click.echo(f"Assigned: {ticket['assigned_to'] or 'unassigned'}")
    click.echo(f"Created: {ticket['created_at']}")
    click.echo()

    if ticket['body']:
        click.echo("## Description")
        click.echo(ticket['body'])
        click.echo()

    click.echo("## History")
    for entry in ticket['history']:
        click.echo(f"  - {entry['timestamp']}: {entry['action']}")

@cli.command()
@click.argument("ticket_id")
@click.option("--status", "-s", type=click.Choice(['open', 'in-progress', 'blocked', 'done']))
def update(ticket_id: str, status: str):
    """Update ticket status."""
    ticket = load_ticket(ticket_id)
    old_status = ticket['status']

    ticket['status'] = status
    ticket['updated_at'] = now_iso()
    ticket['history'].append({
        "timestamp": now_iso(),
        "action": "status_change",
        "from": old_status,
        "to": status
    })

    save_ticket(ticket)
    click.echo(f"Updated {ticket_id}: {old_status} → {status}")

@cli.command()
@click.argument("ticket_id")
@click.argument("worker")
def assign(ticket_id: str, worker: str):
    """Assign a worker to a ticket."""
    ticket = load_ticket(ticket_id)

    ticket['assigned_to'] = worker
    ticket['updated_at'] = now_iso()
    ticket['history'].append({
        "timestamp": now_iso(),
        "action": "assigned",
        "details": f"Assigned to {worker}"
    })

    # Auto-transition to in-progress
    if ticket['status'] == 'open':
        ticket['status'] = 'in-progress'
        ticket['history'].append({
            "timestamp": now_iso(),
            "action": "status_change",
            "from": "open",
            "to": "in-progress"
        })

    save_ticket(ticket)
    click.echo(f"Assigned {ticket_id} to {worker}")

if __name__ == "__main__":
    cli()
```

---

## Dependencies

### Prerequisites

- Python 3.11+
- uv installed

### Story Dependencies

- **STORY-001a**: claude-cli to spawn assigned workers

---

## Definition of Done

- [ ] Project created with `uv init`
- [ ] 5 commands functional (create, list, show, update, assign)
- [ ] JSON storage in tickets/
- [ ] Change history tracked
- [ ] README.md documented
- [ ] Manual tests passed

---

## Test Plan

```bash
cd tickets-cli

# Create
uv run python main.py create "Implement auth" --body "JWT tokens"
# Note the ID returned

# List
uv run python main.py list

# Show
uv run python main.py show <id>

# Assign
uv run python main.py assign <id> auth-worker

# Update
uv run python main.py update <id> --status done

# List filtered
uv run python main.py list --status done
```

---

## Progress Tracking

**Status History:**
- 2025-01-28: Story created

---

**Next story:** STORY-001d (Integration)
