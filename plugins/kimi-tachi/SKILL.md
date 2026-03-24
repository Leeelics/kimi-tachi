---
name: kimi-tachi
description: Kimi-tachi internal commands for multi-agent orchestration
triggers:
  - "/workflow"
  - "/sessions"
---

# Kimi-Tachi Commands

Internal commands for kimi-tachi multi-agent orchestration.

## Overview

```
┌─────────────────────────────────────────┐
│  L1: Metadata (YAML frontmatter)        │
│  - Command triggers                     │
│  - Skill identification                 │
├─────────────────────────────────────────┤
│  L2: SKILL.md body                      │
│  - Command reference                    │
│  - Usage examples                       │
├─────────────────────────────────────────┤
│  L3: Bundled resources                  │
│  - references/workflow-types.md         │
│  - scripts/workflow-runner.py           │
└─────────────────────────────────────────┘
```

**Note**: These commands are used by kimi-tachi CLI, not directly in Kimi conversation.

## Available Commands

### `/workflow <task> [--type <type>]`

Run a multi-agent workflow in non-interactive mode.

**Types:**
- `auto` - Auto-detect (default)
- `feature` - Full feature implementation
- `bugfix` - Bug analysis and fix
- `explore` - Code exploration
- `refactor` - Safe refactoring
- `quick` - Quick single-agent fix

**Usage via CLI:**
```bash
kimi-tachi workflow "implement auth system" --type feature
```

### `/sessions [--clear]`

Manage kimi-tachi sessions for the current project.

**Usage via CLI:**
```bash
kimi-tachi sessions        # List sessions
kimi-tachi sessions --clear # Clear all sessions
```

## How It Works

In normal usage, you **don't need these commands**. Just:

```bash
kimi-tachi  # Start interactive session
```

Then talk to kamaji naturally. Kamaji will automatically:
1. Analyze your request
2. Delegate to appropriate workers behind the scenes
3. Present synthesized results
4. Show "◕‿◕ Workers Involved" credits

The `/workflow` command is for **automation scenarios** where you want to run a complete workflow without interaction.

## Anti-Patterns

| Anti-Pattern | Symptom | Fix |
|--------------|---------|-----|
| Using CLI commands in chat | Typing `/workflow` in Kimi chat | Use natural language with kamaji instead |
| Ignoring interactive mode | Always using non-interactive | Interactive mode provides better context and feedback |

## References

- `references/workflow-types.md` - Detailed workflow type definitions
