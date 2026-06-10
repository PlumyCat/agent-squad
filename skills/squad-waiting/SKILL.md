---
name: squad-waiting
description: Signal that worker is waiting for Prophet response
allowed-tools: Bash, Read, Write
---

# Waiting - Waiting for Prophet Response

This skill allows a worker to signal that it needs a response from Prophet Codex before continuing.

## Usage

```
/squad:waiting "Your question for Prophet"
```

## Parameters

1. **Message** (required): The question or request for Prophet
2. **Ticket ID** (optional): If not provided, tries to detect from context

## Actions to Perform

### 1. Identify session and ticket

```bash
# Get the current tmux session name
tmux display-message -p '#S'
```

If the ticket ID is not known, ask the user or search in context.

### 2. Update ticket to "waiting" status

```bash
./tickets update <ticket-id> --status waiting
./tickets comment <ticket-id> "Waiting for Prophet: <message>"
```

### 3. Create the signal file

Write the JSON file to `./signals/waiting/<session>.json`:

```json
{
  "session": "<session-name>",
  "ticket_id": "<ticket-id>",
  "timestamp": "<ISO-8601>",
  "message": "<question for Prophet>",
  "type": "question"
}
```

Command to create the file (replace variables):
```bash
cat > ./signals/waiting/<session>.json << 'EOF'
{
  "session": "<session>",
  "ticket_id": "<ticket-id>",
  "timestamp": "<timestamp>",
  "message": "<message>",
  "type": "question"
}
EOF
```

### 4. Wait for response (polling)

Check periodically if a response exists:

```bash
# Check if response available
ls ./signals/responses/<session>.json 2>/dev/null
```

If the file exists, read the response:
```bash
cat ./signals/responses/<session>.json
```

### 5. Process the response

Once the response is received:
1. Read and display Prophet's response
2. Delete the waiting signal file (Prophet has normally already done this)
3. Continue work with the response

## Waiting Signal Format

```json
{
  "session": "codex-auth",
  "ticket_id": "abc123",
  "timestamp": "2026-01-29T14:30:00Z",
  "message": "OAuth or JWT for authentication?",
  "type": "question"
}
```

## Response Format (signals/responses/)

```json
{
  "session": "codex-auth",
  "ticket_id": "abc123",
  "timestamp": "2026-01-29T14:35:00Z",
  "response": "Use OAuth2 with refresh tokens",
  "from": "prophet"
}
```

## Workflow

```
Worker has a question
       │
       ▼
  /squad:waiting "OAuth or JWT?"
       │
       ├─► tickets update → waiting
       ├─► Write signals/waiting/<session>.json
       │
       ▼
  Worker waits (poll responses/)
       │
       ▼
  Prophet sees via /squad:status
       │
       ▼
  Prophet responds via /squad:respond
       │
       ▼
  Worker reads the response
       │
       ▼
  Continue work
```

## Important Notes

- **DO NOT** end the session while waiting
- **DO NOT** continue with assumptions - wait for the response
- If blocked too long, set ticket to `blocked` instead of `waiting`
- Prophet will be notified via `/squad:status` of waiting workers
