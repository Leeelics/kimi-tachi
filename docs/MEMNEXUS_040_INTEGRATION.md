# memnexus 0.4.0 Integration Guide for kimi-tachi

> **Status:** Ready for integration  
> **Target:** kimi-tachi v0.6.0  
> **memnexus Requirement:** >=0.4.0

---

## Overview

memnexus 0.4.0 has been released with full Session Explorer support. This guide documents how to migrate kimi-tachi from the temporary implementation to use memnexus natively.

## Changes in memnexus 0.4.0

### New Module: `memnexus.session`

```python
from memnexus.session import (
    SessionExplorer,           # Main exploration class
    DecisionDeduplicator,      # Deduplication service
    RelevanceScorer,           # Scoring algorithm
    ExploreOptions,            # Exploration options
    ExplorerConfig,            # Configuration
    # Data models
    Decision,
    ExplorationResult,
    DuplicateCheckResult,
    ExplorationStats,
)
```

### Key Features

1. **SessionExplorer.explore_related()** - Find relevant decisions from other sessions
2. **MinHash Fingerprinting** - Advanced semantic similarity (better than simple hashing)
3. **Dual Storage Backends** - SQLite (production) + JSON (development)
4. **Technical Term Boosting** - 248 tech terms get 3x weight
5. **Configurable Scoring** - All weights adjustable

---

## Migration Steps

### Step 1: Update Dependency

```toml
# pyproject.toml
[project.dependencies]
memnexus = ">=0.4.0"
```

### Step 2: Update MemoryAdapter

Replace `kimi_tachi/memory/_memory_adapter.py`:

```python
"""Memory adapter - now just a thin wrapper around memnexus."""

from memnexus.session import (
    SessionExplorer,
    DecisionDeduplicator,
    ExploreOptions,
    ExplorerConfig,
)

class MemoryAdapter:
    """Thin adapter to integrate memnexus with kimi-tachi."""
    
    def __init__(self, storage_path=None):
        self._explorer = SessionExplorer(storage_path)
        self._deduplicator = DecisionDeduplicator(storage_path)
    
    async def explore_sessions(self, current_session_id, query, context, limit=5, min_relevance=0.2):
        """Delegate to memnexus SessionExplorer."""
        options = ExploreOptions(limit=limit, min_relevance=min_relevance)
        return await self._explorer.explore_related(
            current_session_id=current_session_id,
            query=query,
            context=context,
            options=options,
        )
    
    async def check_duplicate(self, content):
        """Delegate to memnexus DecisionDeduplicator."""
        return await self._deduplicator.check_duplicate(content)
    
    async def store_decision(self, content, source_session="", metadata=None):
        """Store with automatic deduplication."""
        check = await self.check_duplicate(content)
        if check.is_duplicate and check.confidence > 0.9:
            return None
        return await self._deduplicator.add_fingerprint(
            content=content,
            source_session=source_session,
            metadata=metadata,
        )
```

### Step 3: Remove Temporary Code

Delete these files (functionality now in memnexus):

```bash
# Remove temporary implementations
rm src/kimi_tachi/memory/session_explorer.py
rm src/kimi_tachi/memory/_memory_adapter.py  # Replace with new version

# Update imports in other files
# - hooks/tools.py
# - tachi_memory.py
```

### Step 4: Update hooks/tools.py

```python
# Replace EXPLORER_AVAILABLE check with:
try:
    from memnexus.session import SessionExplorer
    MEMNEXUS_SESSION_AVAILABLE = True
except ImportError:
    MEMNEXUS_SESSION_AVAILABLE = False

# In recall_on_session_start():
if MEMNEXUS_SESSION_AVAILABLE and source == "startup":
    from memnexus.session import ExploreOptions
    
    explorer = SessionExplorer()
    options = ExploreOptions(limit=5, min_relevance=0.3)
    
    result = await explorer.explore_related(
        current_session_id=session_id,
        query=cwd,
        context={"cwd": cwd},
        options=options,
    )
    
    if result.decisions:
        # Format for CLI output...
```

### Step 5: Update TachiMemory

```python
# src/kimi_tachi/memory/tachi_memory.py

from memnexus.session import SessionExplorer, ExploreOptions

class TachiMemory:
    """Now uses memnexus directly."""
    
    def __init__(self):
        # ... existing init ...
        self._session_explorer = SessionExplorer()
    
    async def recall_for_task(self, task, agent_type=None):
        """Use memnexus for exploration."""
        # ... existing code ...
        
        # Explore related sessions via memnexus
        result = await self._session_explorer.explore_related(
            current_session_id=self._current_session_id or "unknown",
            query=task,
            context={"cwd": str(self.project_path), "agent": agent_type},
            options=ExploreOptions(limit=5, min_relevance=0.2),
        )
        
        context["related_decisions"] = [
            {"content": d.content, "source": d.source_session}
            for d in result.decisions
        ]
```

---

## API Mapping

| kimi-tachi (old) | memnexus 0.4.0 | Notes |
|------------------|----------------|-------|
| `SessionExplorer.find_relevant_sessions()` | `SessionExplorer.explore_related()` | Direct replacement |
| `DecisionDeduplicator.is_duplicate()` | `DecisionDeduplicator.check_duplicate()` | Returns more info |
| `DecisionDeduplicator.add()` | `DecisionDeduplicator.add_fingerprint()` | Direct replacement |
| `SessionExplorer.mark_explored()` | `SessionExplorer.mark_explored()` | Identical |
| `SessionExplorer.is_explored()` | `SessionExplorer.is_explored()` | Identical |
| `RelevanceScorer.calculate()` | `RelevanceScorer.calculate()` | Enhanced algorithm |

---

## Storage Path Changes

```
# Old (kimi-tachi temporary)
~/.kimi-tachi/memory/session_explorer/
├── decision_fingerprints.json
└── explored_sessions.json

# New (memnexus 0.4.0)
~/.memnexus/explorer/
├── explorer.db (SQLite, production)
# OR
├── fingerprints.json
└── explorations.json (development)
```

**Migration needed**: Existing users will lose exploration history unless we provide a migration script.

---

## Testing

### Unit Tests

```python
# tests/test_session_explorer.py - SIMPLIFIED

import pytest
from memnexus.session import SessionExplorer, DecisionDeduplicator

@pytest.fixture
def explorer(tmp_path):
    return SessionExplorer(storage_path=tmp_path)

@pytest.mark.asyncio
async def test_explore_related(explorer):
    # memnexus handles the logic - just verify integration
    result = await explorer.explore_related(
        current_session_id="test",
        query="database",
    )
    assert isinstance(result.decisions, list)
```

### Integration Tests

```python
# Test kimi-tachi integration

async def test_recall_for_task():
    memory = await TachiMemory.init(".")
    context = await memory.recall_for_task("implement auth")
    
    # Should use memnexus internally
    assert "related_decisions" in context
```

---

## Benefits of Migration

### 1. **Better Deduplication**
- Old: Simple keyword hash
- New: MinHash (128 hashes) - detects near-duplicates

### 2. **Production Storage**
- Old: JSON files only
- New: SQLite (atomic, concurrent) + JSON fallback

### 3. **Smarter Scoring**
- Old: Basic keyword matching
- New: 248 technical terms with 3x weight boost

### 4. **Unified Codebase**
- Storage logic in one place (memnexus)
- kimi-tachi focuses on orchestration

### 5. **Future Proof**
- Future memnexus improvements automatic
- Vector similarity coming in v0.5.0

---

## Rollback Plan

If issues arise:

```python
# In case of emergency, fall back to temporary implementation
try:
    from memnexus.session import SessionExplorer
except ImportError:
    # Use legacy implementation
    from .session_explorer_legacy import SessionExplorer
```

---

## Timeline

| Phase | Version | Action |
|-------|---------|--------|
| 1 | v0.6.0-alpha | Add memnexus>=0.4.0 dependency, update imports |
| 2 | v0.6.0-beta | Remove temporary code, update tests |
| 3 | v0.6.0 | Release with full memnexus integration |
| 4 | v0.7.0 | Remove legacy fallback code |

---

## References

- memnexus 0.4.0 Changelog: `/home/lee/ship/memnexus/CHANGELOG.md`
- Session Explorer Spec: `/home/lee/ship/memnexus/docs/REQUIREMENTS_SESSION_EXPLORER.md`
- Compliance Report: `/home/lee/ship/memnexus/docs/SESSION_EXPLORER_COMPLIANCE_REPORT.md`
- memnexus Session Module: `/home/lee/ship/memnexus/src/memnexus/session/`
