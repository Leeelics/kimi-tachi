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

from .tachi_memory import TachiMemory, MemoryConfig
from .agent_profiles import AGENT_MEMORY_PROFILES

__all__ = [
    "TachiMemory",
    "MemoryConfig", 
    "AGENT_MEMORY_PROFILES",
]
