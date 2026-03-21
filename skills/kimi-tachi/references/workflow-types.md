# Workflow Types Reference

Complete guide to kimi-tachi workflow types and their agent orchestration.

## Workflow Type Overview

| Type | Use Case | Agents Involved | Duration |
|------|----------|-----------------|----------|
| `auto` | Let kamaji decide | Varies | Varies |
| `feature` | New feature implementation | 5-6 agents | Long |
| `bugfix` | Bug analysis and fix | 3-4 agents | Medium |
| `explore` | Code exploration | 1-2 agents | Short |
| `refactor` | Safe refactoring | 4-5 agents | Medium-Long |
| `quick` | Quick single-agent fix | 1 agent | Short |

## Detailed Workflows

### `feature` - Full Feature Implementation

**Purpose:** Implement a new feature from scratch

**Agent Sequence:**
```
1. tasogare (plan)
   └─ Analyze requirements
   └─ Create implementation plan
   └─ Identify risks

2. nekobasu (explore)
   └─ Map existing codebase
   └─ Find relevant files
   └─ Identify integration points

3. shishigami (architect)
   └─ Design system architecture
   └─ Define interfaces
   └─ Review plan

4. calcifer (implement)
   └─ Write code
   └─ Add tests
   └─ Update documentation

5. enma (review)
   └─ Code review
   └─ Security check
   └─ Quality verification
```

**Example:**
```bash
kimi-tachi workflow "implement user authentication" --type feature
```

### `bugfix` - Bug Analysis and Fix

**Purpose:** Find and fix bugs

**Agent Sequence:**
```
1. nekobasu (locate)
   └─ Find bug location
   └─ Trace code path
   └─ Identify root cause

2. calcifer (fix)
   └─ Implement fix
   └─ Add regression test
   └─ Verify solution

3. enma (verify)
   └─ Review fix
   └─ Check edge cases
   └─ Approve
```

**Example:**
```bash
kimi-tachi workflow "fix login timeout issue" --type bugfix
```

### `explore` - Code Exploration

**Purpose:** Understand codebase structure

**Agent Sequence:**
```
1. nekobasu (navigate)
   └─ Explore codebase
   └─ Find relevant files
   └─ Map dependencies

2. phoenix (document)
   └─ Document findings
   └─ Create summary
   └─ Preserve knowledge
```

**Example:**
```bash
kimi-tachi workflow "explore how auth works" --type explore
```

### `refactor` - Safe Refactoring

**Purpose:** Improve code quality while maintaining behavior

**Agent Sequence:**
```
1. phoenix (history)
   └─ Review change history
   └─ Identify fragile areas
   └─ Document current behavior

2. shishigami (design)
   └─ Design new structure
   └─ Plan migration path
   └─ Identify risks

3. calcifer (refactor)
   └─ Execute refactoring
   └─ Run tests
   └─ Verify behavior

4. enma (verify)
   └─ Review changes
   └─ Verify no regressions
   └─ Approve
```

**Example:**
```bash
kimi-tachi workflow "refactor auth module" --type refactor
```

### `quick` - Quick Single-Agent Fix

**Purpose:** Simple, straightforward tasks

**Agent Sequence:**
```
1. calcifer (direct)
   └─ Implement change
   └─ Verify fix
```

**Example:**
```bash
kimi-tachi workflow "fix typo in README" --type quick
```

## Workflow State Management

Workflows maintain state across agent transitions:

```
State = {
  "workflow_id": "uuid",
  "type": "feature",
  "status": "in_progress",
  "current_agent": "calcifer",
  "completed_agents": ["tasogare", "nekobasu", "shishigami"],
  "pending_agents": ["enma"],
  "artifacts": {
    "plan": "...",
    "exploration": "...",
    "architecture": "...",
    "implementation": "..."
  },
  "context": {
    "original_request": "...",
    "accumulated_findings": "..."
  }
}
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Agent fails | Retry or escalate to kamaji |
| Timeout | Save state, notify user |
| Conflict | Pause for manual resolution |
| Success | Continue to next agent |
