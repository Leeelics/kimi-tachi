# Agent Capability Matrix

Complete reference for kimi-tachi agent capabilities and routing decisions.

## Quick Reference

| Agent | Icon | Primary Role | Best For | Avoid When |
|-------|------|--------------|----------|------------|
| kamaji | ◕‿◕ | Coordinator | Everything (user interface) | - |
| shishigami | 🦌 | Architect | Design decisions, patterns | Quick fixes |
| nekobasu | 🚌 | Explorer | Finding code, navigation | Implementation |
| calcifer | 🔥 | Builder | Coding, refactoring | Architecture decisions |
| enma | 👹 | Reviewer | Code review, quality | Initial implementation |
| tasogare | 🌆 | Planner | Complex planning, research | Simple tasks |
| phoenix | 🐦 | Librarian | Documentation, history | Active coding |

## Detailed Capabilities

### kamaji (釜爺) - Coordinator

**Strengths:**
- Task analysis and decomposition
- Worker coordination
- Result synthesis
- User communication

**Tools:** All available tools

**Delegation Pattern:**
```
kamaji analyzes → delegates to workers → synthesizes → presents to user
```

### shishigami (シシ神) - Architect

**Strengths:**
- System design
- Pattern recognition
- Long-term thinking
- Trade-off analysis

**Best Inputs:**
- "Should we use X or Y?"
- "Design a system for..."
- "What's the best architecture for..."

**Output Format:**
- Architecture overview
- Component breakdown
- Trade-off analysis
- Recommendations

### nekobasu (猫バス) - Explorer

**Strengths:**
- Fast code navigation
- Pattern finding
- Codebase mapping
- Dependency tracing

**Best Inputs:**
- "Find all..."
- "Where is..."
- "How does X work?"

**Output Format:**
- File list with relevance
- Code snippets
- Relationship mapping

### calcifer (カルシファー) - Builder

**Strengths:**
- Code implementation
- Refactoring
- Bug fixing
- Test writing

**Best Inputs:**
- "Implement..."
- "Fix..."
- "Refactor..."
- Clear specifications

**Output Format:**
- Code changes
- Implementation notes
- Testing suggestions

### enma (閻魔大王) - Reviewer

**Strengths:**
- Code quality assessment
- Security review
- Style checking
- Best practice verification

**Best Inputs:**
- Code to review
- PR description
- Specific concerns

**Output Format:**
- Severity classification
- Issue list (file:line - description)
- Fix suggestions
- Final verdict

### tasogare (黄昏時) - Planner

**Strengths:**
- Complex task breakdown
- Research and analysis
- Option evaluation
- Timeline estimation

**Best Inputs:**
- Vague requirements
- Complex features
- "How should we approach..."

**Output Format:**
- Multiple options
- Pros/cons analysis
- Recommended approach
- Implementation roadmap

### phoenix (火の鳥) - Librarian

**Strengths:**
- Documentation
- Historical context
- Pattern documentation
- Knowledge preservation

**Best Inputs:**
- "Document..."
- "Why was this done..."
- "Explain the history of..."

**Output Format:**
- Documentation
- Historical context
- Pattern explanations
- Knowledge records

## Routing Decision Tree

```
User Request
    │
    ├── Simple task (< 2 steps)
    │   └── kamaji handles directly
    │
    ├── Exploration needed
    │   └── nekobasu
    │
    ├── Design/Architecture decision
    │   └── shishigami
    │
    ├── Implementation required
    │   └── calcifer
    │
    ├── Code review needed
    │   └── enma
    │
    ├── Complex planning
    │   └── tasogare
    │
    └── Documentation/History
        └── phoenix
```

## Multi-Agent Workflows

### Feature Implementation
```
tasogare (plan) → nekobasu (explore) → shishigami (arch) → calcifer (impl) → enma (review)
```

### Bug Fix
```
nekobasu (locate) → calcifer (fix) → enma (verify)
```

### Refactoring
```
nekobasu (analyze) → shishigami (design) → calcifer (refactor) → enma (verify)
```
