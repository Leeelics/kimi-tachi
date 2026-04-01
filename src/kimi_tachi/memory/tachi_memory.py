"""
TachiMemory - Automatic memory system for kimi-tachi

This module uses memnexus 0.4.0+ for all storage operations.

Requirements:
    - memnexus>=0.4.0 (for Session Explorer support)

Components:
    - CodeMemory: Project-specific code memories
    - GlobalMemory: Cross-project knowledge
    - SessionExplorer: Cross-session context discovery (memnexus 0.4.0+)
    - DecisionDeduplicator: Content deduplication (memnexus 0.4.0+)
"""

# v3: Uses memnexus 0.4.0+ natively
from .tachi_memory_v3 import (
    MemoryConfig,
    TachiMemory,
    get_memory,
    reset_memory,
)

# Export memnexus types for convenience
try:
    from memnexus.session import (
        Decision,
        DecisionDeduplicator,
        DuplicateCheckResult,
        ExplorationResult,
        ExplorationStats,
        ExploreOptions,
        ExplorerConfig,
        SessionExplorer,
    )
    __all__ = [
        # Main API
        "TachiMemory",
        "MemoryConfig",
        "get_memory",
        "reset_memory",
        # memnexus types (re-exported)
        "SessionExplorer",
        "DecisionDeduplicator",
        "ExploreOptions",
        "ExplorerConfig",
        "ExplorationResult",
        "Decision",
        "DuplicateCheckResult",
        "ExplorationStats",
    ]
except ImportError:
    # memnexus not available
    __all__ = [
        "TachiMemory",
        "MemoryConfig",
        "get_memory",
        "reset_memory",
    ]
