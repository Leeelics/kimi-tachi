---
name: todo-enforcer
description: Ensure tasks are completed before claiming done
---

# Todo Enforcement Protocol (必須遂行プロトコル)

As a member of kimi-tachi, you MUST follow this protocol for all multi-step tasks.

## Core Rules

1. **Always Create Todos** for tasks with more than 2 steps
2. **Update Status** as you progress (pending → in_progress → completed)
3. **Verify Completion** before claiming done - ALL todos must be completed
4. **Never Skip** - If stuck, explain why and create alternative todos

## Workflow

```
User Request
    ↓
Analyze Complexity
    ↓
Multi-step? → Create Todos with SetTodoList
    ↓
Execute & Update Todos
    ↓
All Completed? → Claim Done
```

## Todo Format

Use SetTodoList with this structure:

```json
{
  "todos": [
    {"id": "1", "content": "Analyze requirements", "status": "completed"},
    {"id": "2", "content": "Design solution", "status": "in_progress"},
    {"id": "3", "content": "Implement code", "status": "pending"},
    {"id": "4", "content": "Test and verify", "status": "pending"}
  ]
}
```

## Status Definitions

- **pending**: Not started yet
- **in_progress**: Currently working on it
- **completed**: Done and verified

## Enforcement

Before saying "Done", "Complete", or "Finished":
- Check all todos are "completed"
- If not, continue working or explain blockers

This is not optional - it's the kimi-tachi way (君たちの流儀).
