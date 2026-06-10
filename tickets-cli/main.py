#!/usr/bin/env python3
"""Tickets CLI - Track delegated tasks for Multi-Claude orchestration."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import click

TICKETS_DIR = Path(__file__).parent / "tickets"

VALID_STATUSES = ["open", "in-progress", "blocked", "waiting", "done"]


def ensure_tickets_dir():
    """Create tickets directory if it doesn't exist."""
    TICKETS_DIR.mkdir(exist_ok=True)


def generate_ticket_id() -> str:
    """Generate a short unique ticket ID."""
    return uuid.uuid4().hex[:8]


def now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_ticket(ticket_id: str) -> dict:
    """Load a ticket by ID."""
    # Support partial ID matching
    matches = list(TICKETS_DIR.glob(f"{ticket_id}*.json"))
    if not matches:
        raise click.ClickException(f"Ticket not found: {ticket_id}")
    if len(matches) > 1:
        ids = [m.stem for m in matches]
        raise click.ClickException(f"Ambiguous ID '{ticket_id}', matches: {', '.join(ids)}")

    with open(matches[0]) as f:
        return json.load(f)


def save_ticket(ticket: dict):
    """Save a ticket to disk."""
    ensure_tickets_dir()
    path = TICKETS_DIR / f"{ticket['id']}.json"
    with open(path, "w") as f:
        json.dump(ticket, f, indent=2)


def add_history(ticket: dict, action: str, **kwargs):
    """Add an entry to ticket history."""
    entry = {"timestamp": now_iso(), "action": action}
    entry.update(kwargs)
    ticket["history"].append(entry)
    ticket["updated_at"] = now_iso()


def format_status_icon(status: str) -> str:
    """Return icon for ticket status."""
    icons = {
        "open": "○",
        "in-progress": "◐",
        "blocked": "✗",
        "waiting": "⏳",
        "done": "✓",
    }
    return icons.get(status, "?")


@click.group()
def cli():
    """Tickets CLI - Track delegated tasks for Multi-Claude orchestration.

    This CLI helps Squad Orchestrator track tasks delegated to worker Claudes.
    Each task becomes a ticket that can be assigned, updated, and tracked.
    """
    ensure_tickets_dir()


@cli.command()
@click.argument("title")
@click.option("--body", "-b", default="", help="Detailed description of the task")
@click.option("--assign", "-a", default=None, help="Assign to worker immediately")
def create(title: str, body: str, assign: str | None):
    """Create a new ticket.

    Examples:

        tickets create "Implement JWT auth"

        tickets create "Fix login bug" --body "Users can't login with email"

        tickets create "Add tests" --assign test-worker
    """
    ticket_id = generate_ticket_id()
    now = now_iso()

    ticket = {
        "id": ticket_id,
        "title": title,
        "body": body,
        "status": "open",
        "assigned_to": None,
        "created_at": now,
        "updated_at": now,
        "history": [{"timestamp": now, "action": "created", "details": "Ticket created"}],
    }

    # Handle immediate assignment
    if assign:
        ticket["assigned_to"] = assign
        ticket["status"] = "in-progress"
        add_history(ticket, "assigned", details=f"Assigned to {assign}")
        add_history(ticket, "status_change", **{"from": "open", "to": "in-progress"})

    save_ticket(ticket)

    click.echo(f"Created ticket: {ticket_id}")
    click.echo(f"  Title: {title}")
    if assign:
        click.echo(f"  Assigned: {assign}")
        click.echo(f"  Status: in-progress")


@cli.command("list")
@click.option("--status", "-s", default=None,
              type=click.Choice(VALID_STATUSES),
              help="Filter by status")
@click.option("--assigned", "-a", default=None, help="Filter by assigned worker")
def list_tickets(status: str | None, assigned: str | None):
    """List all tickets.

    Examples:

        tickets list

        tickets list --status open

        tickets list --status in-progress --assigned auth-worker
    """
    tickets = []

    for path in sorted(TICKETS_DIR.glob("*.json")):
        with open(path) as f:
            ticket = json.load(f)

            # Apply filters
            if status and ticket["status"] != status:
                continue
            if assigned and ticket["assigned_to"] != assigned:
                continue

            tickets.append(ticket)

    if not tickets:
        click.echo("No tickets")
        return

    # Group by status for better readability
    for t in tickets:
        icon = format_status_icon(t["status"])
        worker = t["assigned_to"] or "unassigned"
        click.echo(f"{icon} {t['id']}: {t['title']} [{t['status']}] -> {worker}")


@cli.command()
@click.argument("ticket_id")
def show(ticket_id: str):
    """Show detailed ticket information.

    Supports partial ID matching (e.g., 'abc' matches 'abc12345').

    Example:

        tickets show abc123
    """
    ticket = load_ticket(ticket_id)

    icon = format_status_icon(ticket["status"])
    click.echo(f"{icon} {ticket['title']}")
    click.echo(f"")
    click.echo(f"ID:       {ticket['id']}")
    click.echo(f"Status:   {ticket['status']}")
    click.echo(f"Assigned: {ticket['assigned_to'] or 'unassigned'}")
    click.echo(f"Created:  {ticket['created_at']}")
    click.echo(f"Updated:  {ticket['updated_at']}")

    if ticket["body"]:
        click.echo(f"")
        click.echo("Description:")
        for line in ticket["body"].split("\n"):
            click.echo(f"  {line}")

    click.echo(f"")
    click.echo("History:")
    for entry in ticket["history"]:
        ts = entry["timestamp"]
        action = entry["action"]

        if action == "status_change":
            detail = f"{entry['from']} -> {entry['to']}"
        elif "details" in entry:
            detail = entry["details"]
        else:
            detail = ""

        click.echo(f"  {ts}: {action} {detail}")


@cli.command()
@click.argument("ticket_id")
@click.option("--status", "-s",
              type=click.Choice(VALID_STATUSES),
              help="New status")
@click.option("--body", "-b", default=None, help="Update description")
@click.option("--title", "-t", default=None, help="Update title")
def update(ticket_id: str, status: str | None, body: str | None, title: str | None):
    """Update a ticket.

    Examples:

        tickets update abc123 --status done

        tickets update abc123 --status blocked --body "Waiting for API access"

        tickets update abc123 --title "New title"
    """
    ticket = load_ticket(ticket_id)

    if not any([status, body, title]):
        raise click.ClickException("Provide at least one update: --status, --body, or --title")

    if status:
        old_status = ticket["status"]
        ticket["status"] = status
        add_history(ticket, "status_change", **{"from": old_status, "to": status})
        click.echo(f"Status: {old_status} -> {status}")

    if body is not None:
        ticket["body"] = body
        add_history(ticket, "updated", details="Description updated")
        click.echo("Description updated")

    if title:
        old_title = ticket["title"]
        ticket["title"] = title
        add_history(ticket, "updated", details=f"Title: '{old_title}' -> '{title}'")
        click.echo(f"Title updated")

    save_ticket(ticket)
    click.echo(f"Ticket {ticket['id']} updated")


@cli.command()
@click.argument("ticket_id")
@click.argument("worker")
def assign(ticket_id: str, worker: str):
    """Assign a worker to a ticket.

    If the ticket is 'open', it automatically transitions to 'in-progress'.

    Examples:

        tickets assign abc123 auth-worker

        tickets assign abc123 test-worker
    """
    ticket = load_ticket(ticket_id)

    old_assigned = ticket["assigned_to"]
    ticket["assigned_to"] = worker
    add_history(ticket, "assigned", details=f"Assigned to {worker}")

    # Auto-transition to in-progress
    if ticket["status"] == "open":
        ticket["status"] = "in-progress"
        add_history(ticket, "status_change", **{"from": "open", "to": "in-progress"})
        click.echo(f"Status: open -> in-progress (auto)")

    save_ticket(ticket)

    if old_assigned:
        click.echo(f"Reassigned {ticket['id']}: {old_assigned} -> {worker}")
    else:
        click.echo(f"Assigned {ticket['id']} to {worker}")


@cli.command()
@click.argument("ticket_id")
@click.argument("comment")
def comment(ticket_id: str, comment: str):
    """Add a comment to a ticket.

    Useful for workers to report progress or issues.

    Example:

        tickets comment abc123 "Started implementation, 50% done"
    """
    ticket = load_ticket(ticket_id)
    add_history(ticket, "comment", details=comment)
    save_ticket(ticket)
    click.echo(f"Comment added to {ticket['id']}")


@cli.command()
@click.argument("ticket_id")
@click.option("--force", "-f", is_flag=True, help="Delete without confirmation")
def delete(ticket_id: str, force: bool):
    """Delete a ticket.

    Example:

        tickets delete abc123

        tickets delete abc123 --force
    """
    ticket = load_ticket(ticket_id)

    if not force:
        click.confirm(f"Delete ticket '{ticket['title']}'?", abort=True)

    path = TICKETS_DIR / f"{ticket['id']}.json"
    path.unlink()
    click.echo(f"Deleted ticket: {ticket['id']}")


@cli.command()
def stats():
    """Show ticket statistics.

    Example:

        tickets stats
    """
    stats_data = {"open": 0, "in-progress": 0, "blocked": 0, "waiting": 0, "done": 0}
    total = 0

    for path in TICKETS_DIR.glob("*.json"):
        with open(path) as f:
            ticket = json.load(f)
            stats_data[ticket["status"]] = stats_data.get(ticket["status"], 0) + 1
            total += 1

    if total == 0:
        click.echo("No tickets")
        return

    click.echo(f"Total: {total} tickets")
    click.echo("")
    for status, count in stats_data.items():
        if count > 0:
            icon = format_status_icon(status)
            pct = (count / total) * 100
            click.echo(f"  {icon} {status}: {count} ({pct:.0f}%)")


if __name__ == "__main__":
    cli()
