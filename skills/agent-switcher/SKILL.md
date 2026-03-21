---
name: agent-switcher
description: Legacy skill - kept for compatibility but no longer needed
triggers:
  - "/agent:"
---

# Agent Switcher (Legacy)

**⚠️ DEPRECATED**: This skill is kept for compatibility but **no longer needed**.

## Overview

```
┌─────────────────────────────────────────┐
│  L1: Metadata (YAML frontmatter)        │
│  - Legacy trigger preserved             │
│  - Deprecation notice                   │
├─────────────────────────────────────────┤
│  L2: SKILL.md body                      │
│  - Migration guide                      │
│  - New usage patterns                   │
├─────────────────────────────────────────┤
│  L3: Bundled resources                  │
│  - None (deprecated skill)              │
└─────────────────────────────────────────┘
```

## New Usage

In the current kimi-tachi design:
- **You only talk to kamaji (釜爺)**
- Kamaji automatically delegates to other agents behind the scenes
- You don't need to manually switch agents

Simply describe what you want:

```
> 实现用户登录功能

[kamaji automatically coordinates the team]
```

Kamaji will call the appropriate workers and show you:
```
---
**◕‿◕ Workers Involved:**
- 🌆 tasogare: Analyzed requirements
- 🚌 nekobasu: Explored existing code
- 🔥 calcifer: Implemented the feature
- 👹 enma: Reviewed the code
```

## Old Usage (No longer needed)

The old `/agent:<name>` syntax is no longer necessary:
```
# OLD - Don't use this anymore
/agent:calcifer 实现登录

# NEW - Just say what you want
实现用户登录功能
```

**The new design is simpler - just talk to kamaji!**

## Anti-Patterns

| Anti-Pattern | Symptom | Fix |
|--------------|---------|-----|
| Using old syntax | Typing `/agent:nekobasu` | Just describe the task naturally |
| Manual delegation | Trying to pick agents yourself | Trust kamaji to route appropriately |
