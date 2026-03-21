---
name: todo-enforcer
description: Ensure tasks are completed before claiming done
triggers:
  - "multi-step"
  - "complex task"
---

# Todo Enforcement Protocol (必須遂行プロトコル)

As a member of kimi-tachi, you MUST follow this protocol for all multi-step tasks.

## Overview

```
┌─────────────────────────────────────────┐
│  L1: Metadata (YAML frontmatter)        │
│  - Skill identification                 │
│  - Implicit triggers                    │
├─────────────────────────────────────────┤
│  L2: SKILL.md body                      │
│  - Core rules                           │
│  - Workflow                             │
├─────────────────────────────────────────┤
│  L3: Bundled resources                  │
│  - references/todo-patterns.md          │
│  - scripts/todo-validator.py            │
└─────────────────────────────────────────┘
```

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
    {"title": "Analyze requirements", "status": "completed"},
    {"title": "Design solution", "status": "in_progress"},
    {"title": "Implement code", "status": "pending"},
    {"title": "Test and verify", "status": "pending"}
  ]
}
```

## Status Definitions

- **pending**: Not started yet
- **in_progress**: Currently working on it
- **completed**: Done and verified

## Anti-Patterns

| Anti-Pattern | Symptom | Fix |
|--------------|---------|-----|
| Skipping todo creation | Jumping into implementation without plan | Stop and create todos first |
| Outdated todos | Todos don't reflect actual progress | Update todos as you work |
| False completion | Claiming done with incomplete todos | Verify all todos completed first |
| Vague todos | Todos like "do stuff" | Make todos specific and actionable |

## Enforcement

Before saying "Done", "Complete", or "Finished":
- Check all todos are "completed"
- If not, continue working or explain blockers

This is not optional - it's the **kimi-tachi way** (君たちの流儀).

## References

- `references/todo-patterns.md` - Common todo patterns by task type
