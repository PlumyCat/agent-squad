# context-cli

CLI for managing worker roles and directives.

## Installation

```bash
cd context-cli
uv sync
```

## Structure

```
context-cli/
├── roles/
│   ├── prophet-claude.yaml
│   └── worker.yaml
├── directives/
│   ├── base.yaml
│   └── code-quality.yaml
└── main.py
```

## Commands

### list-roles

Lists available roles.

```bash
uv run python main.py list-roles
```

### list-directives

Lists available directives.

```bash
uv run python main.py list-directives
```

### show

Displays the complete context for a role (prompt + directives).

```bash
uv run python main.py show worker
uv run python main.py show prophet-claude
```

### settings

Generates a settings.json with the role's permissions.

```bash
# Display to stdout
uv run python main.py settings prophet-claude

# Save to a file
uv run python main.py settings prophet-claude -o settings.json
```

### validate

Validates a role's configuration.

```bash
uv run python main.py validate worker
```

## File Formats

### Role (roles/*.yaml)

```yaml
name: worker
description: Worker Codex for tasks

prompt: |
  Your role prompt here...

directives:
  - base
  - code-quality

permissions:
  allow:
    - "Bash(git:*)"
    - "Read"
  deny:
    - "Bash(rm -rf:*)"
```

### Directive (directives/*.yaml)

```yaml
name: base
description: Base directives

content: |
  Your directive content here...
```

## Integration with codex-cli

```bash
# The --role flag loads context from context-cli
cd ../squad-cli
uv run python main.py spawn --role worker "Implement feature X"
```
