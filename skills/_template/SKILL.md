---
name: <skill-name>
description: <One-line description of what this skill does>
triggers:
  - "/<command>"
  - "@<keyword>"
---

# <Skill Name> (スキル名)

Brief description of the skill's purpose and when to use it.

## Overview

```
┌─────────────────────────────────────────┐
│  L1: Metadata (YAML frontmatter)        │
│  - Always loaded (~100 tokens)          │
│  - Used for trigger matching            │
├─────────────────────────────────────────┤
│  L2: SKILL.md body                      │
│  - Loaded when triggered (< 5k tokens)  │
│  - Instructions and examples            │
├─────────────────────────────────────────┤
│  L3: Bundled resources                  │
│  - Loaded on demand                     │
│  - scripts/: Deterministic scripts      │
│  - references/: Reference materials     │
└─────────────────────────────────────────┘
```

## When to Use

Describe the scenarios where this skill should be activated.

## Usage

### Trigger Patterns

- `/<command> [args]` - Primary trigger
- `@<keyword> [query]` - Alternative trigger

### Examples

```
User: /<command> example-arg

[Expected behavior and output]
```

## Instructions

### Step-by-Step Workflow

1. **Step One**: Description
2. **Step Two**: Description
3. **Step Three**: Description

### Output Format

```
[Template for consistent output]
```

## Anti-Patterns

| Anti-Pattern | Symptom | Fix |
|--------------|---------|-----|
| Example bad practice | What goes wrong | How to correct |

## Scripts (L3 Resources)

Deterministic scripts in `scripts/` directory:

| Script | Purpose | Usage |
|--------|---------|-------|
| `example.py` | What it does | `python scripts/example.py [args]` |

## References (L3 Resources)

Reference materials in `references/` directory:

| File | Content |
|------|---------|
| `best-practices.md` | Domain-specific best practices |

---

*This skill follows the kimi-tachi three-tier architecture.*
