---
name: agent-switcher
description: Legacy skill - kept for compatibility but no longer needed
triggers:
  - "/agent:"
---

# Agent Switcher (Legacy)

**⚠️ DEPRECATED**: This skill is kept for compatibility but **no longer needed**.

In the current kimi-tachi design:
- **You only talk to kamaji (釜爺)**
- Kamaji automatically delegates to other agents behind the scenes
- You don't need to manually switch agents

## New Usage

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
