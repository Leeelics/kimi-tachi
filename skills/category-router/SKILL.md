---
name: category-router
description: Route tasks to appropriate agents based on category
---

# Category Router (分類ルーター)

Route user requests to the appropriate kimi-tachi agent.

## Categories

| Category | Description | Delegate To |
|----------|-------------|-------------|
| **explore** | Code exploration, finding files | hermes |
| **architect** | System design, technology decisions | oracle |
| **implement** | Deep coding, refactoring | hephaestus |
| **review** | Code review, audit | momus |
| **research** | Large-scale analysis | prometheus |
| **document** | Documentation | librarian |

## Routing Patterns

- `@explore [query]` → hermes
- `@architect [question]` → oracle
- `@implement [task]` → hephaestus
- `@review [code]` → momus

## Auto-Routing

When no tag provided, analyze intent:
- "Find all..." → explore
- "Should we..." → architect
- "Implement..." → implement
- "Review..." → review
