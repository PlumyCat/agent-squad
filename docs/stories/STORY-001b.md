# STORY-001b: Implement context-cli

**Epic:** Multi-Agent Orchestration
**Priority:** Should Have
**Story Points:** 3
**Status:** Not Started
**Assigned To:** Unassigned
**Created:** 2025-01-28
**Sprint:** 1
**Parent:** STORY-001
**Depends On:** STORY-001a

---

## User Story

As a **solo developer**
I want to **define roles and directives for my Claude workers**
So that **each worker has the right context and permissions for its task**

---

## Description

### Background
The context-cli allows structuring Claude contexts in a modular way. Instead of a large monolithic CLAUDE.md, we define roles (orchestrator, worker, manager) and reusable directives (code-quality, security, etc.). The CLI then generates the complete context and can produce a settings.json for permissions.

### Architecture

```
context-cli/
├── roles/
│   ├── orchestrator.yaml    # Main orchestrator
│   ├── worker.yaml            # Generic worker
│   └── code-reviewer.yaml     # Specialized worker
├── directives/
│   ├── base.yaml              # Common directives
│   ├── code-quality.yaml      # Code standards
│   └── security.yaml          # Security rules
└── main.py
```

---

## Scope

### In Scope

- roles/ and directives/ structure in YAML
- `show <role>` command: displays combined context
- `list-roles` command: lists available roles
- `list-directives` command: lists directives
- `settings <role>` command: generates settings.json
- Base roles: orchestrator, worker
- Base directives: base, code-quality

### Out of Scope

- Persistent memories per Claude (future feature)
- Automatic integration with claude-cli
- UI to edit roles

---

## Acceptance Criteria

### YAML Structure

- [ ] `roles/` folder created with at least 2 YAML files
- [ ] `directives/` folder created with at least 2 YAML files
- [ ] Role format: name, description, prompt, directives[]
- [ ] Directive format: name, description, content

### show command

- [ ] `context show orchestrator` displays combined context
- [ ] Role prompt is included
- [ ] Listed directives are resolved and included
- [ ] Clear error if role doesn't exist

### list-roles command

- [ ] `context list-roles` displays all roles
- [ ] Format: name + short description

### list-directives command

- [ ] `context list-directives` displays all directives
- [ ] Format: name + short description

### settings command

- [ ] `context settings orchestrator` generates valid JSON
- [ ] JSON contains allow/deny permissions
- [ ] Can be redirected to a file

### Base Roles

- [ ] `orchestrator`: orchestrator, delegates to workers
- [ ] `worker`: executes a specific task, exits with /exit

---

## Technical Notes

### YAML Role Format

```yaml
# roles/orchestrator.yaml
name: orchestrator
description: Main orchestrator Claude, delegates to workers

prompt: |
  You are Squad Orchestrator, the orchestrator of a multi-Claude system.

  CORE RESPONSIBILITIES:
  - Receive tasks from the human
  - Break down complex tasks
  - Delegate to worker Claudes via claude-cli
  - Monitor worker progress via capture
  - Integrate results

  CONSTRAINTS:
  - NEVER do implementation work yourself
  - NEVER manually kill tmux sessions
  - NEVER block waiting for workers
  - Always delegate non-trivial tasks

directives:
  - base
  - code-quality

permissions:
  allow:
    - "Bash(claude-cli:*)"
    - "Bash(tmux:*)"
    - "Read"
    - "Edit"
  deny:
    - "Bash(rm -rf:*)"
```

### YAML Directive Format

```yaml
# directives/base.yaml
name: base
description: Base directives for all Claudes

content: |
  ## Communication Style
  - Be concise and direct
  - Use code blocks for commands
  - Confirm understanding before acting

  ## Error Handling
  - Report errors clearly
  - Suggest fixes when possible
  - Don't hide failures
```

### main.py - Structure

```python
#!/usr/bin/env python3
"""Context CLI - Manage roles and directives for Claude workers."""

import click
import yaml
import json
from pathlib import Path

ROLES_DIR = Path(__file__).parent / "roles"
DIRECTIVES_DIR = Path(__file__).parent / "directives"

def load_yaml(path: Path) -> dict:
    """Load a YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)

def load_role(name: str) -> dict:
    """Load a role by name."""
    path = ROLES_DIR / f"{name}.yaml"
    if not path.exists():
        raise click.ClickException(f"Role not found: {name}")
    return load_yaml(path)

def load_directive(name: str) -> dict:
    """Load a directive by name."""
    path = DIRECTIVES_DIR / f"{name}.yaml"
    if not path.exists():
        raise click.ClickException(f"Directive not found: {name}")
    return load_yaml(path)

@click.group()
def cli():
    """Context CLI - Manage roles and directives."""
    pass

@cli.command()
@click.argument("role_name")
def show(role_name: str):
    """Show combined context for a role."""
    role = load_role(role_name)

    click.echo(f"# Role: {role['name']}")
    click.echo(f"# {role['description']}")
    click.echo()
    click.echo(role['prompt'])
    click.echo()

    # Include directives
    for directive_name in role.get('directives', []):
        directive = load_directive(directive_name)
        click.echo(f"## Directive: {directive['name']}")
        click.echo(directive['content'])
        click.echo()

@cli.command("list-roles")
def list_roles():
    """List available roles."""
    click.echo("Available roles:")
    for path in ROLES_DIR.glob("*.yaml"):
        role = load_yaml(path)
        click.echo(f"  - {role['name']}: {role['description']}")

@cli.command("list-directives")
def list_directives():
    """List available directives."""
    click.echo("Available directives:")
    for path in DIRECTIVES_DIR.glob("*.yaml"):
        directive = load_yaml(path)
        click.echo(f"  - {directive['name']}: {directive['description']}")

@cli.command()
@click.argument("role_name")
def settings(role_name: str):
    """Generate settings.json for a role."""
    role = load_role(role_name)

    permissions = role.get('permissions', {})
    settings = {
        "permissions": {
            "allow": permissions.get('allow', []),
            "deny": permissions.get('deny', [])
        }
    }

    click.echo(json.dumps(settings, indent=2))

if __name__ == "__main__":
    cli()
```

---

## Dependencies

### Prerequisites

- Python 3.11+
- uv installed
- PyYAML

### Story Dependencies

- **STORY-001a**: claude-cli must exist to use the --role flag

---

## Definition of Done

- [ ] Project created with `uv init`
- [ ] roles/ and directives/ structure created
- [ ] 2 roles defined: orchestrator, worker
- [ ] 2 directives defined: base, code-quality
- [ ] 4 commands functional
- [ ] README.md documented
- [ ] Integration tested with claude-cli --role

---

## Test Plan

```bash
cd context-cli

# Test list-roles
uv run python main.py list-roles
# Expected: orchestrator, worker

# Test list-directives
uv run python main.py list-directives
# Expected: base, code-quality

# Test show
uv run python main.py show worker
# Expected: Combined context output

# Test settings
uv run python main.py settings orchestrator > settings.json
cat settings.json
# Expected: Valid JSON with permissions
```

---

## Progress Tracking

**Status History:**
- 2025-01-28: Story created

---

**Next story:** STORY-001c (tickets-cli)
