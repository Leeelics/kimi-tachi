---
name: category-router
description: Route tasks to appropriate agents based on category
---

# Category Router (分類ルーター)

Route user requests to the appropriate kimi-tachi agent.

## Categories

| Category | Description | Delegate To |
|----------|-------------|-------------|
| **explore** | Code exploration, finding files | nekobasu |
| **architect** | System design, technology decisions | shishigami |
| **implement** | Deep coding, refactoring | calcifer |
| **review** | Code review, audit | enma |
| **research** | Large-scale analysis | tasogare |
| **document** | Documentation | phoenix |

## Routing Patterns

- `@explore [query]` → nekobasu (猫巴士)
- `@architect [question]` → shishigami (山兽神)
- `@implement [task]` → calcifer (火魔)
- `@review [code]` → enma (阎魔王)

## Auto-Routing

When no tag provided, analyze intent:
- "Find all..." → explore
- "Should we..." → architect
- "Implement..." → implement
- "Review..." → review
