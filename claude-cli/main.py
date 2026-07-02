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
import re
import json
import shlex
import secrets
from pathlib import Path

import click


def _claude_command(project_root, prompt, extra_dirs, model):
    """Build the bare `claude` launch command (the task is delivered after the
    TUI is ready — see spawn).

    - `--permission-mode bypassPermissions`: real autonomy. The legacy
      `--dangerously-skip-permissions` did not engage reliably (workers kept
      landing in "accept edits" and prompted on every bash command / out-of-
      workspace read — nobody was there to answer, so they stalled forever).
    - `--model`: without it the worker inherits the user's default model
      (Opus/Fable — slow and expensive for worker-grade tasks). Cost control
      lives here: workers default to `sonnet` (see DEFAULT_MODELS).
    - `--add-dir`: pre-authorize the dirs the worker will touch (its target
      repo + the squad root for ./tickets and the prompt file) so reads/edits
      don't prompt.

    The task itself is NOT passed positionally: interactive `claude` does not
    auto-submit a positional prompt (it lands on an empty input box). We instead
    write the prompt to a file and, once the TUI is ready, send a one-line
    "read this file and execute" trigger — robust against both the startup race
    and the multiline-paste auto-submit problem.
    """
    cmd = ["claude", "--permission-mode", "bypassPermissions"]
    if model:
        cmd += ["--model", model]
    for d in extra_dirs:
        cmd += ["--add-dir", d]
    return cmd


def _codex_command(project_root, prompt, extra_dirs, model):
    cmd = [
        "codex",
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "--sandbox",
        "danger-full-access",
    ]
    if model:
        cmd += ["--model", model]
    cmd += ["--cd", project_root, prompt]
    return cmd


AGENTS = {
    "codex": {
        "display": "Codex",
        "prefix": "codex",
        "interactive": False,
        "command": _codex_command,
    },
    "claude": {
        "display": "Claude",
        "prefix": "claude",
        "interactive": True,
        "command": _claude_command,
    },
}

# Default model per agent when neither --model nor SQUAD_MODEL is set.
# Claude workers run on sonnet: opus/fable are reserved for orchestrator-side
# work (story writing, review) where the extra cost is justified. Codex has
# its own model namespace, so no default is imposed there.
DEFAULT_MODELS = {
    "claude": "sonnet",
    "codex": None,
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
    selected = agent or os.environ.get("SQUAD_AGENT", "claude")
    if selected not in AGENTS:
        raise click.ClickException(
            f"Unsupported agent '{selected}'. Choose: {', '.join(AGENTS)}"
        )
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
    prefixes = (
        [AGENTS[normalize_agent(agent)]["prefix"]]
        if agent
        else [a["prefix"] for a in AGENTS.values()]
    )
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


# Markers that the Claude TUI is up and ready to receive input.
_READY_MARKERS = (
    "for shortcuts",
    "bypass permissions",
    "accept edits",
    'Try "',
    "│ >",
    "❯",
)

# Pane patterns that mean the worker is blocked on a permission/confirmation
# prompt — i.e. waiting for a human, but UNABLE to self-signal (the TUI prompt
# blocks tool use). Detecting this from the pane is the whole point.
_PERMISSION_PROMPT_RE = re.compile(
    r"Do you want to proceed\?|(?:❯|>)\s*1\.\s*(?:Yes|No)|Approve only if you trust",
    re.IGNORECASE,
)
# A worker still showing the greeting with an EMPTY input box never received
# its task (the old send-keys race). The greyed placeholder gives it away.
_NEVER_STARTED_RE = re.compile(r"Try \"|Welcome to Claude Code")
# Signs the agent is actively thinking/running — definitely not stalled.
_BUSY_RE = re.compile(
    r"esc to interrupt|tokens|Ionizing|Working|Reading|Running|⏺", re.IGNORECASE
)

_SIGNALS_WAITING_DIR = Path(__file__).parent.parent / "signals" / "waiting"


def capture_pane(session: str, history: int = 0) -> str:
    """Return the current tmux pane text for a session ("" on failure)."""
    args = ["capture-pane", "-t", session, "-p"]
    if history:
        args += ["-S", f"-{history}"]
    r = run_tmux(*args)
    return r.stdout if r.returncode == 0 else ""


def wait_for_claude_ready(session: str, timeout: int = 45) -> bool:
    """Poll the pane until the Claude TUI is ready to receive keys.

    Replaces the old fixed `time.sleep(5)` that raced Claude's startup. Only
    used for follow-up send-keys (skills / ralph); the task prompt itself is
    now passed positionally at launch.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if any(m in capture_pane(session) for m in _READY_MARKERS):
            return True
        time.sleep(1)
    return False


def _waiting_signal(session: str) -> dict | None:
    """Read an explicit waiting signal (signals/waiting/<session>.json)."""
    f = _SIGNALS_WAITING_DIR / f"{session}.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text())
    except Exception:
        return {"message": "(waiting signal présent, illisible)"}


def classify_worker(session: str, pane_a: str, pane_b: str) -> dict:
    """Classify a worker's state from two pane snapshots taken a few seconds
    apart, plus any explicit waiting signal. Crucially, the blocked/never-
    started states are detected WITHOUT the worker's cooperation.
    """
    tail = "\n".join([l for l in pane_b.strip().splitlines() if l.strip()][-4:])
    signal = _waiting_signal(session)
    if signal:
        return {
            "session": session,
            "state": "waiting_input",
            "source": "signal",
            "question": signal.get("message", ""),
            "tail": tail,
        }
    if _PERMISSION_PROMPT_RE.search(pane_b):
        return {
            "session": session,
            "state": "waiting_input",
            "source": "permission_prompt",
            "question": tail,
            "tail": tail,
        }
    if _BUSY_RE.search(pane_b):
        return {"session": session, "state": "working", "tail": tail}
    idle = pane_a.strip() == pane_b.strip()  # nothing moved between snapshots
    if idle and _NEVER_STARTED_RE.search(pane_b):
        return {"session": session, "state": "never_started", "tail": tail}
    if idle:
        return {"session": session, "state": "stalled", "tail": tail}
    return {"session": session, "state": "working", "tail": tail}


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Squad CLI - Spawn and manage AI coding workers in tmux sessions."""
    pass


@cli.command()
@click.argument("prompt")
@click.option(
    "--name", "-n", default=None, help="Session name (auto-generated if not provided)"
)
@click.option("--role", "-r", default=None, help="Role to apply from context-cli")
@click.option(
    "--ticket", "-t", default=None, help="Ticket ID to associate with this worker"
)
@click.option(
    "--skill", "-s", multiple=True, help="Skill(s) to run after prompt (repeatable)"
)
@click.option(
    "--ralph", is_flag=True, help="Run with Ralph Loop for autonomous execution"
)
@click.option(
    "--workdir",
    "-w",
    default=None,
    help="Repo/dir the worker will work in — pre-authorized via --add-dir so edits/bash don't prompt. The worker should cd here (say so in the prompt).",
)
@click.option(
    "--agent",
    "-a",
    default=None,
    type=click.Choice(list(AGENTS)),
    help="Agent CLI to launch (default: claude or SQUAD_AGENT)",
)
@click.option(
    "--model",
    "-m",
    default=None,
    help="Model for the worker (alias like sonnet/opus/haiku or full ID). Priority: --model > SQUAD_MODEL env > per-agent default (claude: sonnet).",
)
def spawn(
    prompt: str,
    name: str | None,
    role: str | None,
    ticket: str | None,
    skill: tuple[str, ...],
    ralph: bool,
    workdir: str | None,
    agent: str | None,
    model: str | None,
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
        spawn --model opus "Complex refactoring worth the extra cost"
    """
    agent = normalize_agent(agent)
    prefix = AGENTS[agent]["prefix"]
    display = AGENTS[agent]["display"]

    # Model resolution: explicit flag > SQUAD_MODEL env > per-agent default.
    model = model or os.environ.get("SQUAD_MODEL") or DEFAULT_MODELS[agent]

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
    # Start in project root so ./tickets and other CLIs are accessible.
    project_root_path = Path(__file__).parent.parent
    project_root = str(project_root_path)

    # Dirs the worker is pre-authorized to touch (autonomy without prompts):
    # its target repo (if given) plus the squad root for ./tickets etc.
    extra_dirs = [project_root]
    if workdir:
        workdir_abs = str(Path(workdir).expanduser().resolve())
        if workdir_abs not in extra_dirs:
            extra_dirs.insert(0, workdir_abs)

    if skill and not AGENTS[agent]["interactive"]:
        full_prompt += "\n\nRequested startup skills/workflows:\n" + "\n".join(
            f"- {s}" for s in skill
        )

    interactive = AGENTS[agent]["interactive"]

    # Interactive Claude does NOT auto-submit a positional prompt, so we write
    # the task to a file and trigger it after startup with a one-line "read this
    # file and execute" message (avoids both the startup race and the multiline
    # auto-submit problem). The file lives under the squad root, already in
    # --add-dir, so reading it doesn't prompt.
    prompt_file = None
    if interactive and not ralph:
        prompts_dir = project_root_path / ".squad-prompts"
        prompts_dir.mkdir(exist_ok=True)
        prompt_file = prompts_dir / f"{session}.txt"
        prompt_file.write_text(full_prompt, encoding="utf-8")

    command = AGENTS[agent]["command"](project_root, full_prompt, extra_dirs, model)
    run_script = create_run_script(project_root_path, command, session)
    result = run_tmux(
        "new-session",
        "-d",
        "-s",
        session,
        "-c",
        project_root,
        f"zsh {shlex.quote(str(run_script))}",
    )
    if result.returncode != 0:
        click.echo(f"Error creating session: {result.stderr}", err=True)
        raise SystemExit(1)

    if model:
        click.echo(f"Model: {model}")
    click.echo(f"Starting {display} in session '{session}'...")

    if interactive:
        # No fixed sleep — poll until the TUI is actually ready, otherwise any
        # follow-up keys get dropped like the old prompt did.
        if not wait_for_claude_ready(session):
            click.echo(
                "Warning: Claude TUI not detected as ready within timeout; "
                "run 'squad status --json' to check the worker.",
                err=True,
            )

        if ralph:
            click.echo("Ralph Loop mode enabled")
            run_tmux(
                "send-keys", "-t", session, "-l", f"/ralph-loop:ralph-loop {prompt}"
            )
            run_tmux("send-keys", "-t", session, "Enter")
        elif prompt_file is not None:
            trigger = (
                f"Lis le fichier {prompt_file} et exécute intégralement, dans "
                f"l'ordre, les consignes qu'il contient. Commence maintenant, "
                f"ne pose pas de question."
            )
            run_tmux("send-keys", "-t", session, "-l", trigger)
            time.sleep(0.5)
            run_tmux("send-keys", "-t", session, "Enter")

        # Activate skills after the task has been delivered. `-l` sends the text
        # literally; Enter is a separate key event.
        if skill:
            click.echo(f"Skills to activate: {', '.join(skill)}")
            time.sleep(2)
            for s in skill:
                skill_cmd = s if s.startswith("/") else f"/{s}"
                run_tmux("send-keys", "-t", session, "-l", skill_cmd)
                run_tmux("send-keys", "-t", session, "Enter")
                click.echo(f"  Sent skill: {skill_cmd}")
                time.sleep(1)

    click.echo(f"Spawned worker: {session}")
    click.echo(f"Attach with: tmux attach -t {session}")
    click.echo("Status (JSON): ./squad status --json")


@cli.command()
@click.argument("session")
@click.option(
    "--lines", "-l", default=30, help="Number of lines to capture (default: 30)"
)
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
@click.option(
    "--agent",
    "-a",
    default=None,
    type=click.Choice(list(AGENTS)),
    help="Filter by agent",
)
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
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Machine-readable JSON for the orchestrator.",
)
@click.option(
    "--agent",
    "-a",
    default=None,
    type=click.Choice(list(AGENTS)),
    help="Filter by agent",
)
def status(as_json: bool, agent: str | None):
    """Report each worker's state — including the states a worker CANNOT
    self-report: blocked on a permission prompt, or never started.

    States: working | waiting_input | stalled | never_started.
    The orchestrator polls `status --json` and acts on anything != working
    (answer the prompt, nudge, or escalate to the human).
    """
    sessions = get_worker_sessions(agent)
    if not sessions:
        click.echo("[]" if as_json else "No active workers")
        return

    # Two snapshots a few seconds apart: a moving pane => working; a frozen
    # pane that isn't a prompt => stalled.
    snap_a = {s: capture_pane(s) for s in sessions}
    time.sleep(3)
    snap_b = {s: capture_pane(s) for s in sessions}
    report = [classify_worker(s, snap_a[s], snap_b[s]) for s in sessions]

    if as_json:
        click.echo(json.dumps(report, ensure_ascii=False))
        return

    icon = {"working": "▶", "waiting_input": "⏸", "stalled": "⚠", "never_started": "✗"}
    click.echo("Worker status:")
    for r in report:
        click.echo(f"  {icon.get(r['state'], '?')} {r['session']}: {r['state']}")
        if r.get("question"):
            click.echo(f"      ↳ {r['question'].strip()[:200]}")


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
