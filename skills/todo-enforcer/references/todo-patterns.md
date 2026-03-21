# Todo Patterns by Task Type

Reference guide for creating effective todos based on task categories.

## Pattern Templates

### Feature Implementation

```json
{
  "todos": [
    {"title": "Analyze requirements and constraints", "status": "pending"},
    {"title": "Explore existing codebase", "status": "pending"},
    {"title": "Design system architecture", "status": "pending"},
    {"title": "Implement core functionality", "status": "pending"},
    {"title": "Add tests", "status": "pending"},
    {"title": "Update documentation", "status": "pending"},
    {"title": "Review and verify", "status": "pending"}
  ]
}
```

### Bug Fix

```json
{
  "todos": [
    {"title": "Reproduce the bug", "status": "pending"},
    {"title": "Locate root cause", "status": "pending"},
    {"title": "Implement fix", "status": "pending"},
    {"title": "Add regression test", "status": "pending"},
    {"title": "Verify fix works", "status": "pending"}
  ]
}
```

### Code Review

```json
{
  "todos": [
    {"title": "Review architecture and design", "status": "pending"},
    {"title": "Check code quality", "status": "pending"},
    {"title": "Verify tests coverage", "status": "pending"},
    {"title": "Check documentation", "status": "pending"},
    {"title": "Provide feedback", "status": "pending"}
  ]
}
```

### Refactoring

```json
{
  "todos": [
    {"title": "Analyze current code structure", "status": "pending"},
    {"title": "Design new structure", "status": "pending"},
    {"title": "Create migration plan", "status": "pending"},
    {"title": "Execute refactoring", "status": "pending"},
    {"title": "Run all tests", "status": "pending"},
    {"title": "Verify no regressions", "status": "pending"}
  ]
}
```

### Documentation

```json
{
  "todos": [
    {"title": "Identify documentation gaps", "status": "pending"},
    {"title": "Gather technical details", "status": "pending"},
    {"title": "Write documentation", "status": "pending"},
    {"title": "Add code examples", "status": "pending"},
    {"title": "Review for accuracy", "status": "pending"}
  ]
}
```

## Todo Writing Guidelines

### Good Todos

✅ **Specific:**
- "Implement JWT token validation middleware"
- "Add unit tests for UserService"
- "Update API documentation with new endpoints"

✅ **Actionable:**
- "Run test suite and fix failures"
- "Review PR #123 for security issues"
- "Refactor auth module to use new pattern"

✅ **Verifiable:**
- "Verify all tests pass (pytest -v)"
- "Confirm documentation renders correctly"
- "Check code coverage > 80%"

### Bad Todos

❌ **Vague:**
- "Do stuff"
- "Fix things"
- "Work on feature"

❌ **Too Large:**
- "Implement entire system"
- "Fix all bugs"
- "Rewrite everything"

❌ **Not Actionable:**
- "Think about problem"
- "Consider options"
- "Maybe do something"

## Status Transitions

```
pending → in_progress → completed
   ↓           ↓            ↓
 Not yet    Working     Done and
 started    on it       verified
```

**Rules:**
1. Only mark `completed` when fully done AND verified
2. Update to `in_progress` before starting work
3. If blocked, add comment explaining why
4. Never skip statuses

## Multi-Agent Todo Coordination

When multiple agents work on the same task:

```
Task: Implement feature
├── kamaji: [coordination] - pending
├── tasogare: [plan] - completed
├── nekobasu: [explore] - completed
├── calcifer: [implement] - in_progress
└── enma: [review] - pending
```

Each agent updates their own sub-todos before marking parent complete.
