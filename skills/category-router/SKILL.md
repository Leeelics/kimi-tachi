---
name: category-router
description: Route tasks to appropriate agents based on category
triggers:
  - "@explore"
  - "@architect"
  - "@implement"
  - "@review"
---

# Category Router (分類ルーター)

Route user requests to the appropriate kimi-tachi agent.

## Overview

```
┌─────────────────────────────────────────┐
│  L1: Metadata (YAML frontmatter)        │
│  - Skill identification                 │
│  - Trigger patterns                     │
├─────────────────────────────────────────┤
│  L2: SKILL.md body                      │
│  - Category definitions                 │
│  - Routing rules                        │
├─────────────────────────────────────────┤
│  L3: Bundled resources                  │
│  - references/agent-capabilities.md     │
│  - scripts/route-decision.py            │
└─────────────────────────────────────────┘
```

## Categories

| Category | Description | Delegate To |
|----------|-------------|-------------|
| **explore** | Code exploration, finding files | nekobasu (猫巴士) |
| **architect** | System design, technology decisions | shishigami (山兽神) |
| **implement** | Deep coding, refactoring | calcifer (火魔) |
| **review** | Code review, audit | enma (阎魔王) |
| **research** | Large-scale analysis | tasogare (黄昏) |
| **document** | Documentation | phoenix (火之鸟) |

## Routing Patterns

- `@explore [query]` → nekobasu (猫巴士) 🚌
- `@architect [question]` → shishigami (山兽神) 🦌
- `@implement [task]` → calcifer (火魔) 🔥
- `@review [code]` → enma (阎魔王) 👹

## Auto-Routing

When no tag provided, analyze intent:
- "Find all..." → explore
- "Should we..." → architect
- "Implement..." → implement
- "Review..." → review

## Anti-Patterns

| Anti-Pattern | Symptom | Fix |
|--------------|---------|-----|
| Manual agent switching | User tries `/agent:calcifer` | Remind them to use `@implement` or let kamaji auto-route |
| Wrong category | Task routed to inappropriate agent | Re-analyze and suggest correct category |

## References

- `references/agent-capabilities.md` - Detailed agent capability matrix
