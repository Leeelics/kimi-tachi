"""
Kimi-Tachi Memory Module

Integration with MemNexus for persistent code memory.

Usage:
    from kimi_tachi.memory import TachiMemory

    memory = await TachiMemory.init("./my-project")

    # Index project
    await memory.index_project()

    # Search memory
    results = await memory.search("authentication")

    # Store agent context
    await memory.store_agent_context("kamaji", context)

    # Recall for agent
    context = await memory.recall_agent_context("kamaji")
"""

from .agent_profiles import AGENT_MEMORY_PROFILES
from .tachi_memory import MemoryConfig, TachiMemory, get_memory

# Try to import v3 with team support
try:
    from .tachi_memory_v3 import get_memory_for_current_team

    TEAM_MEMORY_AVAILABLE = True
except ImportError:
    TEAM_MEMORY_AVAILABLE = False
    get_memory_for_current_team = None

# Alias for backward compatibility
AGENT_PROFILES = AGENT_MEMORY_PROFILES

__all__ = [
    "TachiMemory",
    "MemoryConfig",
    "get_memory",
    "get_memory_for_current_team",
    "AGENT_MEMORY_PROFILES",
    "AGENT_PROFILES",
]
