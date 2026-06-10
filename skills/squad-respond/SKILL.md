---
name: squad-respond
description: Respond to a waiting worker
allowed-tools: Bash, Read, Write
---

# Respond - Respond to a Waiting Worker

This skill allows Squad Orchestrator to respond to a worker waiting for a response via `/squad:waiting`.

## Usage

```
/squad:respond <session> "Your response"
```

## Parameters

1. **Session** (required): Name of the worker's tmux session (e.g., `codex-auth`)
2. **Response** (required): The response to send to the worker

## Actions to Perform

### 1. Check the waiting signal

```bash
cat ./signals/waiting/<session>.json
```

This provides context: ticket_id, original message, timestamp.

### 2. Write the response

Create the file `./signals/responses/<session>.json`:

```json
{
  "session": "<session>",
  "ticket_id": "<ticket-id-from-waiting>",
  "timestamp": "<ISO-8601>",
  "response": "<your response>",
  "from": "orchestrator"
}
```

Command:
```bash
cat > ./signals/responses/<session>.json << 'EOF'
{
  "session": "<session>",
  "ticket_id": "<ticket-id>",
  "timestamp": "<timestamp>",
  "response": "<response>",
  "from": "orchestrator"
}
EOF
```

### 3. Update the ticket

```bash
./tickets update <ticket-id> --status in-progress
./tickets comment <ticket-id> "Squad Orchestrator responded: <summary>"
```

### 4. Send message to worker

```bash
./squad send <session> "Squad Orchestrator: <your response>"
```

### 5. Delete the waiting signal

```bash
rm ./signals/waiting/<session>.json
```

## Complete Workflow

```
Squad Orchestrator sees worker waiting (via /squad:status)
       │
       ▼
  /squad:respond codex-auth "Use OAuth2"
       │
       ├─► Read signals/waiting/codex-auth.json
       ├─► Write signals/responses/codex-auth.json
       ├─► tickets update → in-progress
       ├─► ./squad send codex-auth "Squad Orchestrator: ..."
       ├─► rm signals/waiting/codex-auth.json
       │
       ▼
  Worker receives the response
       │
       ▼
  Worker continues work
```

## Example

```bash
# See waiting workers
/squad:status

# Output shows:
# ⏳ Workers waiting:
#   codex-auth: "OAuth or JWT?" (since 5 min)

# Respond
/squad:respond codex-auth "Use OAuth2 with refresh tokens. See the doc in /docs/auth.md"
```

## View Waiting Workers

To list waiting workers:

```bash
ls -la ./signals/waiting/

# View signal details
cat ./signals/waiting/<session>.json
```

Or use `/squad:status` which displays this section.

## Notes

- Always respond to waiting workers promptly
- Response is sent via `./squad send` for immediate notification
- The responses/ file serves as backup if send fails
- Ticket automatically returns to `in-progress`
