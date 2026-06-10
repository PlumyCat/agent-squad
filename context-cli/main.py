#!/usr/bin/env python3
"""
Context CLI - Manage roles and directives for Claude workers.

Usage:
    uv run python main.py show orchestrator
    uv run python main.py list-roles
    uv run python main.py list-directives
    uv run python main.py settings orchestrator
"""

import json
from pathlib import Path

import click
import yaml

# Paths relative to this file
ROLES_DIR = Path(__file__).parent / "roles"
DIRECTIVES_DIR = Path(__file__).parent / "directives"


def load_yaml(path: Path) -> dict:
    """Load a YAML file."""
    with open(path, encoding="utf-8") as f:
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


def get_all_roles() -> list[dict]:
    """Get all available roles."""
    roles = []
    for path in ROLES_DIR.glob("*.yaml"):
        roles.append(load_yaml(path))
    return roles


def get_all_directives() -> list[dict]:
    """Get all available directives."""
    directives = []
    for path in DIRECTIVES_DIR.glob("*.yaml"):
        directives.append(load_yaml(path))
    return directives


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Context CLI - Manage roles and directives for Claude workers."""
    pass


@cli.command()
@click.argument("role_name")
def show(role_name: str):
    """Show the combined context for a role.

    Displays the role prompt and all included directives.

    Example:
        show orchestrator
        show worker
    """
    role = load_role(role_name)

    # Header
    click.echo(f"# Role: {role['name']}")
    click.echo(f"# {role.get('description', 'No description')}")
    click.echo()

    # Role prompt
    click.echo("## Role Context")
    click.echo()
    click.echo(role.get("prompt", ""))
    click.echo()

    # Include directives
    directive_names = role.get("directives", [])
    if directive_names:
        click.echo("---")
        click.echo()
        for directive_name in directive_names:
            try:
                directive = load_directive(directive_name)
                click.echo(f"## Directive: {directive['name']}")
                click.echo()
                click.echo(directive.get("content", ""))
                click.echo()
            except click.ClickException as e:
                click.echo(f"Warning: {e.message}", err=True)


@cli.command("list-roles")
def list_roles():
    """List all available roles.

    Shows role name and description for each role
    defined in the roles/ directory.
    """
    roles = get_all_roles()

    if not roles:
        click.echo("No roles defined")
        click.echo(f"Add YAML files to: {ROLES_DIR}")
        return

    click.echo("Available roles:")
    for role in sorted(roles, key=lambda r: r.get("name", "")):
        name = role.get("name", "unknown")
        desc = role.get("description", "No description")
        click.echo(f"  - {name}: {desc}")


@cli.command("list-directives")
def list_directives():
    """List all available directives.

    Shows directive name and description for each directive
    defined in the directives/ directory.
    """
    directives = get_all_directives()

    if not directives:
        click.echo("No directives defined")
        click.echo(f"Add YAML files to: {DIRECTIVES_DIR}")
        return

    click.echo("Available directives:")
    for directive in sorted(directives, key=lambda d: d.get("name", "")):
        name = directive.get("name", "unknown")
        desc = directive.get("description", "No description")
        click.echo(f"  - {name}: {desc}")


@cli.command()
@click.argument("role_name")
@click.option("--output", "-o", default=None, help="Output file (default: stdout)")
def settings(role_name: str, output: str | None):
    """Generate settings.json for a role.

    Creates a Claude Code settings.json with permissions
    defined in the role.

    Examples:
        settings orchestrator
        settings orchestrator -o settings.json
    """
    role = load_role(role_name)

    permissions = role.get("permissions", {})
    settings_data = {
        "permissions": {
            "allow": permissions.get("allow", []),
            "deny": permissions.get("deny", []),
        }
    }

    json_output = json.dumps(settings_data, indent=2)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(json_output)
        click.echo(f"Settings written to: {output}")
    else:
        click.echo(json_output)


@cli.command()
@click.argument("role_name")
def validate(role_name: str):
    """Validate a role configuration.

    Checks that the role exists and all referenced
    directives are available.

    Example:
        validate orchestrator
    """
    role = load_role(role_name)
    errors = []

    # Check required fields
    if "name" not in role:
        errors.append("Missing 'name' field")
    if "prompt" not in role:
        errors.append("Missing 'prompt' field")

    # Check directives exist
    for directive_name in role.get("directives", []):
        path = DIRECTIVES_DIR / f"{directive_name}.yaml"
        if not path.exists():
            errors.append(f"Directive not found: {directive_name}")

    if errors:
        click.echo(f"Validation failed for {role_name}:", err=True)
        for error in errors:
            click.echo(f"  - {error}", err=True)
        raise SystemExit(1)
    else:
        click.echo(f"Role '{role_name}' is valid")
        click.echo(f"  - Prompt: {len(role.get('prompt', ''))} chars")
        click.echo(f"  - Directives: {len(role.get('directives', []))}")
        click.echo(f"  - Permissions: {len(role.get('permissions', {}).get('allow', []))} allow, {len(role.get('permissions', {}).get('deny', []))} deny")


if __name__ == "__main__":
    cli()
