#!/usr/bin/env python3
"""
Squad CLI - Spawn and manage AI coding workers in tmux sessions.

Usage:
    uv run python main.py spawn "Your prompt here"
    uv run python main.py spawn --agent codex --name my-worker "Your prompt"
    uv run python main.py spawn --agent claude --name my-worker "Your prompt"
    uv run python main.py capture my-worker --lines 50
    uv run python main.py list
    uv run python main.py kill my-worker
    uv run python main.py kill-all
"""

import subprocess
import time
import uuid
import os
import shlex
import secrets
from pathlib import Path

import click


AGENTS = {
    "codex": {
        "display": "Codex",
        "prefix": "codex",
        "interactive": False,
        "command": lambda project_root, prompt: [
            "codex",
            "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--sandbox",
            "danger-full-access",
            "--cd",
            project_root,
            prompt,
        ],
    },
    "claude": {
        "display": "Claude",
        "prefix": "claude",
        "interactive": True,
        "command": lambda _project_root, _prompt: ["claude", "--dangerously-skip-permissions"],
    },
}

NAME_ADJECTIVES = [
    "brave",
    "bright",
    "cosmic",
    "daring",
    "electric",
    "golden",
    "lucky",
    "neon",
    "nimble",
    "quantum",
    "rapid",
    "solar",
    "turbo",
    "velvet",
]

NAME_NOUNS = [
    "beacon",
    "circuit",
    "comet",
    "forge",
    "lantern",
    "nova",
    "orbit",
    "pixel",
    "pulse",
    "rocket",
    "signal",
    "spark",
    "vector",
    "vortex",
]


def run_tmux(*args: str) -> subprocess.CompletedProcess:
    """Execute a tmux command and return the result."""
    return subprocess.run(
        ["tmux", *args],
        capture_output=True,
        text=True,
    )


def create_run_script(project_root: Path, command: list[str], session: str) -> Path:
    """Create a per-session script so tmux does not depend on nested quoting."""
    runs_dir = project_root / ".squad-runs"
    runs_dir.mkdir(exist_ok=True)
    script_path = runs_dir / f"{session}.sh"
    script_path.write_text(
        "\n".join(
            [
                "#!/bin/zsh",
                f"cd {shlex.quote(str(project_root))}",
                shlex.join(command),
                "exit_code=$?",
                "echo",
                f"echo '[squad] Agent exited with status '$exit_code'. Session kept for capture. Kill with: ./squad kill {session}'",
                "while true; do sleep 3600; done",
                "",
            ]
        ),
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    return script_path


def normalize_agent(agent: str | None) -> str:
    """Return a supported agent name."""
    selected = agent or os.environ.get("SQUAD_AGENT", "codex")
    if selected not in AGENTS:
        raise click.ClickException(f"Unsupported agent '{selected}'. Choose: {', '.join(AGENTS)}")
    return selected


def generate_session_name(agent: str) -> str:
    """Generate a fun unique session name."""
    prefix = AGENTS[agent]["prefix"]
    for _ in range(25):
        adjective = secrets.choice(NAME_ADJECTIVES)
        noun = secrets.choice(NAME_NOUNS)
        session = f"{prefix}-{adjective}-{noun}"
        if not session_exists(session):
            return session
    return f"{prefix}-{secrets.choice(NAME_ADJECTIVES)}-{secrets.choice(NAME_NOUNS)}-{uuid.uuid4().hex[:4]}"


def session_exists(name: str) -> bool:
    """Check if a tmux session exists."""
    result = run_tmux("has-session", "-t", name)
    return result.returncode == 0


def get_worker_sessions(agent: str | None = None) -> list[str]:
    """Get all worker sessions."""
    result = run_tmux("list-sessions", "-F", "#{session_name}")
    if result.returncode != 0:
        return []
    prefixes = [AGENTS[normalize_agent(agent)]["prefix"]] if agent else [a["prefix"] for a in AGENTS.values()]
    return [
        s
        for s in result.stdout.strip().split("\n")
        if any(s.startswith(f"{prefix}-") for prefix in prefixes)
    ]


def get_role_context(role: str) -> str | None:
    """Get context from context-cli for a given role."""
    context_cli_path = Path(__file__).parent.parent / "context-cli"
    if not context_cli_path.exists():
        return None

    result = subprocess.run(
        ["uv", "run", "python", "main.py", "show", role],
        capture_output=True,
        text=True,
        cwd=context_cli_path,
    )

    if result.returncode == 0:
        return result.stdout.strip()
    return None


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Squad CLI - Spawn and manage AI coding workers in tmux sessions."""
    pass


@cli.command()
@click.argument("prompt")
@click.option("--name", "-n", default=None, help="Session name (auto-generated if not provided)")
@click.option("--role", "-r", default=None, help="Role to apply from context-cli")
@click.option("--ticket", "-t", default=None, help="Ticket ID to associate with this worker")
@click.option("--skill", "-s", multiple=True, help="Skill(s) to run after prompt (repeatable)")
@click.option("--ralph", is_flag=True, help="Run with Ralph Loop for autonomous execution")
@click.option("--agent", "-a", default=None, type=click.Choice(list(AGENTS)), help="Agent CLI to launch (default: codex or SQUAD_AGENT)")
def spawn(
    prompt: str,
    name: str | None,
    role: str | None,
    ticket: str | None,
    skill: tuple[str, ...],
    ralph: bool,
    agent: str | None,
):
    """Spawn a worker in a new tmux session.

    PROMPT is the task to give to the worker.

    Examples:
        spawn "Implement a fibonacci function"
        spawn --agent codex --name fib-worker "Implement fibonacci"
        spawn --name fib-worker "Implement fibonacci"
        spawn --role worker "Fix the bug in auth.py"
        spawn --role worker --ticket abc123 "Implement feature"
        spawn --ralph "Long autonomous task"
        spawn --ralph --role worker --ticket abc123 "Complex feature"
        spawn --skill bmad:dev-story "Workflow-driven task"
    """
    agent = normalize_agent(agent)
    prefix = AGENTS[agent]["prefix"]
    display = AGENTS[agent]["display"]

    # Generate session name with the agent prefix
    if name:
        known_prefixes = tuple(f"{config['prefix']}-" for config in AGENTS.values())
        session = name if name.startswith(known_prefixes) else f"{prefix}-{name}"
    else:
        session = generate_session_name(agent)

    # Check if session already exists
    if session_exists(session):
        click.echo(f"Error: Session '{session}' already exists", err=True)
        click.echo("Use a different name or kill the existing session", err=True)
        raise SystemExit(1)

    # Build the full prompt with role context if provided
    full_prompt = prompt
    if role:
        context = get_role_context(role)
        if context:
            full_prompt = f"{context}\n\n---\n\nTASK:\n{prompt}"
            click.echo(f"Applied role: {role}")
        else:
            click.echo(f"Warning: Could not load role '{role}'", err=True)

    # Add ticket info to the prompt if provided
    if ticket:
        full_prompt += f"\n\n---\n\nTICKET ID: {ticket}\nWhen done, run: ./tickets update {ticket} --status done"
        click.echo(f"Linked ticket: {ticket}")
        # Update ticket status to in-progress
        tickets_cli_path = Path(__file__).parent.parent / "tickets-cli"
        if tickets_cli_path.exists():
            subprocess.run(
                ["uv", "run", "python", "main.py", "assign", ticket, session],
                cwd=tickets_cli_path,
                capture_output=True,
            )

    # Create tmux session with the selected agent CLI.
    # Start in project root so ./tickets and other CLIs are accessible
    project_root_path = Path(__file__).parent.parent
    project_root = str(project_root_path)
    if skill and not AGENTS[agent]["interactive"]:
        full_prompt += "\n\nRequested startup skills/workflows:\n" + "\n".join(f"- {s}" for s in skill)

    command = AGENTS[agent]["command"](project_root, full_prompt)
    run_script = create_run_script(project_root_path, command, session)
    result = run_tmux("new-session", "-d", "-s", session, "-c", project_root, f"zsh {shlex.quote(str(run_script))}")
    if result.returncode != 0:
        click.echo(f"Error creating session: {result.stderr}", err=True)
        raise SystemExit(1)

    # Wait for the agent CLI to initialize.
    click.echo(f"Starting {display} in session '{session}'...")
    time.sleep(5)

    if AGENTS[agent]["interactive"]:
        # Send the prompt (or ralph-loop command if --ralph)
        if ralph:
            # Use Ralph Loop for autonomous execution
            ralph_cmd = f"/ralph-loop:ralph-loop {prompt}"
            click.echo("Ralph Loop mode enabled")
            run_tmux("send-keys", "-t", session, ralph_cmd, "Enter")
        else:
            run_tmux("send-keys", "-t", session, full_prompt, "Enter")
            # Send extra Enter to confirm paste in CLIs that ask before submitting pasted text.
            time.sleep(1)
            run_tmux("send-keys", "-t", session, "Enter")

        # Send skills if specified (after a delay for the interactive agent to start processing)
        if skill:
            click.echo(f"Skills to activate: {', '.join(skill)}")
            time.sleep(3)
            for s in skill:
                # Normalize skill name (add / prefix if missing)
                skill_cmd = s if s.startswith("/") else f"/{s}"
                run_tmux("send-keys", "-t", session, skill_cmd, "Enter")
                click.echo(f"  Sent skill: {skill_cmd}")
                time.sleep(1)

    click.echo(f"Spawned worker: {session}")
    click.echo(f"Attach with: tmux attach -t {session}")
    click.echo(f"Capture with: uv run python main.py capture {session}")


@cli.command()
@click.argument("session")
@click.option("--lines", "-l", default=30, help="Number of lines to capture (default: 30)")
def capture(session: str, lines: int):
    """Capture output from a worker session.

    SESSION is the name of the tmux session to capture from.

    Examples:
        capture my-worker
        capture my-worker --lines 100
    """
    if not session_exists(session):
        click.echo(f"Error: Session '{session}' not found", err=True)
        click.echo("Use 'list' to see active sessions", err=True)
        raise SystemExit(1)

    # Capture the pane content
    result = run_tmux("capture-pane", "-t", session, "-p")
    if result.returncode != 0:
        click.echo(f"Error capturing session: {result.stderr}", err=True)
        raise SystemExit(1)

    # Get the last N lines
    output_lines = result.stdout.strip().split("\n")
    for line in output_lines[-lines:]:
        click.echo(line)


@cli.command("list")
@click.option("--agent", "-a", default=None, type=click.Choice(list(AGENTS)), help="Filter by agent")
def list_sessions(agent: str | None):
    """List all active worker sessions.

    Shows session name and basic info for all sessions
    starting with a known agent prefix.
    """
    sessions = get_worker_sessions(agent)

    if not sessions:
        click.echo("No active workers")
        return

    click.echo("Active workers:")
    for session in sessions:
        # Get session info
        result = run_tmux(
            "list-sessions",
            "-F",
            "#{session_name}: created #{session_created_string}",
            "-f",
            f"#{{==:#{{session_name}},{session}}}",
        )
        if result.returncode == 0 and result.stdout.strip():
            click.echo(f"  - {result.stdout.strip()}")
        else:
            click.echo(f"  - {session}")


@cli.command()
@click.argument("session")
def kill(session: str):
    """Kill a specific worker session.

    SESSION is the name of the tmux session to kill.

    Example:
        kill my-worker
    """
    if not session_exists(session):
        click.echo(f"Error: Session '{session}' not found", err=True)
        raise SystemExit(1)

    result = run_tmux("kill-session", "-t", session)
    if result.returncode != 0:
        click.echo(f"Error killing session: {result.stderr}", err=True)
        raise SystemExit(1)

    click.echo(f"Killed: {session}")


@cli.command("kill-all")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
def kill_all(force: bool):
    """Kill all worker sessions.

    Kills all tmux sessions using known worker prefixes.

    Examples:
        kill-all
        kill-all --force
    """
    sessions = get_worker_sessions()

    if not sessions:
        click.echo("No worker sessions to kill")
        return

    click.echo(f"Found {len(sessions)} worker session(s):")
    for session in sessions:
        click.echo(f"  - {session}")

    if not force:
        if not click.confirm("Kill all these sessions?"):
            click.echo("Aborted")
            return

    killed = 0
    for session in sessions:
        result = run_tmux("kill-session", "-t", session)
        if result.returncode == 0:
            killed += 1
        else:
            click.echo(f"Warning: Could not kill {session}", err=True)

    click.echo(f"Killed {killed} session(s)")


@cli.command()
@click.argument("session")
@click.argument("text")
def send(session: str, text: str):
    """Send text to a worker session (advanced).

    Useful for sending follow-up text to workers.

    Examples:
        send my-worker "please summarize your current status"
        send my-worker "continue with the next step"
    """
    if not session_exists(session):
        click.echo(f"Error: Session '{session}' not found", err=True)
        raise SystemExit(1)

    run_tmux("send-keys", "-t", session, text, "Enter")
    click.echo(f"Sent to {session}: {text[:50]}{'...' if len(text) > 50 else ''}")


if __name__ == "__main__":
    cli()
