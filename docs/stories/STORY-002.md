# STORY-002: Worker UX Improvements

**Epic:** Multi-Agent Orchestration
**Priority:** Should Have
**Story Points:** 5
**Status:** Completed
**Assigned To:** Claude
**Created:** 2025-01-28
**Sprint:** 1

---

## User Story

As a **Squad Orchestrator**
I want to **have more autonomous workers and better tracking**
So that **the delegation workflow is smoother and less manual**

---

## Description

Following the Multi-Claude Bootstrap system tests, several improvement points were identified to make workers more autonomous and improve the user experience.

---

## Identified Issues

### 1. Worker Auto-exit (Priority: High)
**Problem:** Workers don't automatically `/exit` after completing their task.
**Solution:** Add a directive in the worker role to exit with `/exit` when done.

### 2. /done Skill for Workers (Priority: High)
**Problem:** The worker must manually update the ticket AND do /exit.
**Solution:** Create a `/done` skill that:
- Updates the associated ticket to "done"
- Adds a completion comment
- Executes `/exit`

### 3. Ticket-Worker Integration (Priority: Medium)
**Problem:** No automatic link between ticket and worker.
**Solution:**
- `--ticket` option in `claude spawn` to link a ticket
- Worker knows its ticket ID via environment variable or context

### 4. Improve Worker Directives (Priority: Medium)
**Problem:** Workers don't have enough instructions on how to properly terminate.
**Solution:** Enrich `worker.yaml` with clear end-of-task instructions.

---

## Acceptance Criteria

### /done Skill
- [ ] Create `.claude/commands/done.md`
- [ ] Skill updates ticket to "done" if a ticket is associated
- [ ] Skill displays a confirmation message
- [ ] Instructions to do `/exit` after

### Improved Worker Directives
- [ ] Modify `context-cli/roles/worker.yaml`
- [ ] Add explicit end-of-task instructions
- [ ] Mention mandatory `/exit`

### --ticket Option for Spawn
- [ ] Add `--ticket` to `claude spawn`
- [ ] Pass ticket ID in worker context
- [ ] Auto-update ticket to "in-progress" on spawn

---

## Technical Notes

### /done Skill

```markdown
# Done - Task Completion

Signals the end of the assigned task.

## Actions
1. If ticket associated: `./tickets update <id> --status done`
2. Display confirmation message
3. Remind to do `/exit`
```

### Improved Worker Role

```yaml
# Add to worker.yaml
completion_instructions: |
  WHEN YOU'RE DONE:
  1. Verify everything is complete
  2. If ticket assigned: ./tickets update <ticket> --status done
  3. Do /exit to free the session

  IMPORTANT: NEVER stay active after finishing.
```

---

## Definition of Done

- [ ] `/done` skill created and functional
- [ ] Worker role updated with end instructions
- [ ] `--ticket` option added to spawn
- [ ] Manual tests passed
- [ ] Documentation updated

---

## Progress Tracking

**Status History:**
- 2025-01-28: Story created following tests
