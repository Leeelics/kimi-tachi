"""
TachiMemory v2 - Orchestration Layer

重构后的 TachiMemory，专注于：
1. Orchestrating memory operations (not implementing them)
2. Providing kimi-cli specific conveniences
3. Delegating all storage to memnexus (via MemoryAdapter)

Architecture:
- All storage operations go through MemoryAdapter
- MemoryAdapter delegates to memnexus when available
- Fallback implementations are temporary (marked as TODO v0.6.0)
- kimi-tachi does not implement storage logic directly
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console

# Try to import memnexus
try:
    from memnexus import CodeMemory, MemoryType
    from memnexus.mechanisms.global_memory import GlobalMemory
    from memnexus.memory import MemoryEntry
    MEMNEXUS_AVAILABLE = True
except ImportError:
    MEMNEXUS_AVAILABLE = False

# Import our adapter layer
from ._memory_adapter import (
    MemoryAdapter,
    get_memory_adapter,
)

console = Console()


@dataclass
class MemoryConfig:
    """Configuration for TachiMemory."""

    project_path: str = "."
    storage_path: str | None = None
    recall_limit: int = 10
    store_limit: int = 100
    search_limit: int = 10
    enable_global: bool = True
    global_project_name: str | None = None

    # Auto-memory settings
    auto_recall: bool = True
    auto_store: bool = True

    # v0.5.3: Proactive exploration
    proactive_explore: bool = True
    exploration_limit: int = 5
    min_relevance: float = 0.2

    def __post_init__(self):
        if self.storage_path is None:
            self.storage_path = os.path.join(
                self.project_path, ".kimi-tachi", "memory"
            )


class TachiMemoryV2:
    """
    Automatic memory system for kimi-tachi (v2 refactored).

    Responsibilities:
    1. ORCHESTRATION: Coordinate memory operations
    2. CLI INTEGRATION: Format output for kimi-cli
    3. WORKFLOW: Provide convenient high-level APIs

    NOT Responsible:
    - ❌ Storage implementation (delegated to memnexus via adapter)
    - ❌ Vector indexing (memnexus)
    - ❌ Session file parsing (memnexus)
    - ❌ Deduplication algorithm (memnexus)

    All storage operations go through MemoryAdapter, which delegates
    to memnexus when available.
    """

    def __init__(self, project_path: str = ".", config: MemoryConfig | None = None):
        self.config = config or MemoryConfig(project_path=project_path)
        self.project_path = Path(self.config.project_path).resolve()
        self._storage_path = Path(self.config.storage_path)

        # memnexus stores (when available)
        self._mn_memory: CodeMemory | None = None
        self._mn_global: GlobalMemory | None = None

        # Our adapter layer (hides memnexus vs fallback details)
        self._adapter: MemoryAdapter | None = None

        # Session tracking
        self._current_session_id: str | None = None
        self._session_start_time: str | None = None

        # Lock for async operations
        self._lock = asyncio.Lock()

    @classmethod
    async def init(
        cls,
        project_path: str = ".",
        config: MemoryConfig | None = None
    ) -> TachiMemoryV2:
        """Initialize TachiMemoryV2."""
        instance = cls(project_path, config)
        await instance._initialize()
        return instance

    async def _initialize(self):
        """Initialize all components."""
        # Initialize memnexus stores
        if MEMNEXUS_AVAILABLE:
            await self._init_memnexus()

        # Initialize adapter layer (hides implementation details)
        self._adapter = await get_memory_adapter()

    async def _init_memnexus(self):
        """Initialize memnexus components."""
        self._storage_path.mkdir(parents=True, exist_ok=True)

        # CodeMemory for project-specific memories
        self._mn_memory = await CodeMemory.init(
            project_path=str(self.project_path),
            storage_path=str(self._storage_path / "code")
        )

        # GlobalMemory for cross-project knowledge
        if self.config.enable_global:
            try:
                global_storage = self._storage_path / "global"
                global_storage.mkdir(parents=True, exist_ok=True)

                self._mn_global = GlobalMemory(storage_path=str(global_storage))
                await self._mn_global.initialize()
            except Exception as e:
                console.print(f"[yellow]Global memory not available: {e}[/yellow]")

    # ========================================================================
    # ORCHESTRATION APIs (what kimi-tachi provides)
    # ========================================================================

    async def recall_for_task(
        self,
        task: str,
        agent_type: str | None = None
    ) -> dict[str, Any]:
        """
        Recall context for a task.

        Orchestrates:
        1. Search project memory (via memnexus)
        2. Explore related sessions (via adapter -> memnexus)
        3. Search global memory (via memnexus)
        4. Format for kimi-cli consumption

        Args:
            task: Task description
            agent_type: Optional agent type for profile-based recall

        Returns:
            Formatted context for kimi-cli
        """
        context = {
            "task": task,
            "agent_type": agent_type,
            "project_memories": [],
            "related_decisions": [],
            "global_knowledge": [],
            "formatted_output": "",
        }

        # 1. Search project memory (memnexus)
        if self._mn_memory and self._mn_memory.store:
            try:
                results = await self._mn_memory.store.search(
                    query=task,
                    limit=self.config.recall_limit
                )
                context["project_memories"] = self._format_memories(results)
            except Exception as e:
                console.print(f"[dim]Project memory search: {e}[/dim]")

        # 2. Explore related sessions (adapter -> memnexus)
        if self._adapter and self.config.proactive_explore:
            try:
                exploration = await self._adapter.explore_sessions(
                    current_session_id=self._current_session_id or "unknown",
                    query=task,
                    context={"cwd": str(self.project_path), "agent": agent_type},
                    limit=self.config.exploration_limit,
                    min_relevance=self.config.min_relevance
                )
                context["related_decisions"] = [
                    {
                        "content": d.content,
                        "source": d.source_session,
                        "timestamp": d.timestamp,
                    }
                    for d in exploration.decisions
                ]
            except Exception as e:
                console.print(f"[dim]Session exploration: {e}[/dim]")

        # 3. Search global memory (memnexus)
        if self._mn_global:
            try:
                results = await self._mn_global.search(query=task, limit=3)
                context["global_knowledge"] = results
            except Exception as e:
                console.print(f"[dim]Global memory search: {e}[/dim]")

        # 4. Format for kimi-cli (kimi-tachi responsibility)
        context["formatted_output"] = self._format_for_cli(context)

        return context

    async def store_decision(
        self,
        content: str,
        metadata: dict | None = None
    ) -> str | None:
        """
        Store a decision (with automatic deduplication).

        Args:
            content: Decision content
            metadata: Additional metadata

        Returns:
            Fingerprint if stored, None if duplicate
        """
        if not self._adapter:
            return None

        # Delegate to adapter (which handles deduplication)
        fingerprint = await self._adapter.store_decision(
            content=content,
            source_session=self._current_session_id or "",
            metadata=metadata
        )

        # Also store in memnexus if available
        if fingerprint and self._mn_memory and self._mn_memory.store:
            try:
                entry = MemoryEntry(
                    content=content,
                    memory_type=MemoryType.DECISION,
                    source=f"session:{self._current_session_id}",
                    metadata={
                        "fingerprint": fingerprint,
                        **(metadata or {})
                    }
                )
                await self._mn_memory.store.store(entry)
            except Exception as e:
                console.print(f"[dim]Could not store in memnexus: {e}[/dim]")

        return fingerprint

    def start_session(
        self,
        session_id: str | None = None,
        task: str = ""
    ) -> str:
        """
        Start a new session.

        Args:
            session_id: Optional session ID
            task: Initial task description

        Returns:
            Session ID
        """
        import uuid
        from datetime import datetime

        self._current_session_id = session_id or str(uuid.uuid4())[:8]
        self._session_start_time = datetime.now().isoformat()

        # Note: Proactive exploration is now done via recall_for_task()
        # to avoid blocking session start

        return self._current_session_id

    # ========================================================================
    # CLI FORMATTING (kimi-tachi specific)
    # ========================================================================

    def _format_memories(self, results: list[Any]) -> list[dict]:
        """Format memnexus results for CLI."""
        formatted = []
        for r in results:
            formatted.append({
                "id": getattr(r, 'id', str(id(r))),
                "content": getattr(r, 'content', str(r)),
                "type": getattr(r, 'memory_type', 'unknown'),
                "source": getattr(r, 'source', 'unknown'),
                "score": getattr(r, 'score', 1.0),
            })
        return formatted

    def _format_for_cli(self, context: dict) -> str:
        """
        Format context for kimi-cli output.

        This is kimi-tachi's value-add: formatting for CLI consumption.
        """
        lines = []
        has_content = False

        # Related decisions from other sessions
        if context["related_decisions"]:
            has_content = True
            lines.append("📚 Related decisions from other sessions:")
            for d in context["related_decisions"][:3]:
                source = d.get('source', 'unknown')[:8]
                content = d.get('content', '')[:80]
                lines.append(f"  - [{source}] {content}")

        # Project memories
        if context["project_memories"]:
            has_content = True
            if lines:
                lines.append("")
            lines.append("📋 Recent project context:")
            for m in context["project_memories"][:3]:
                content = m.get('content', '')[:80]
                lines.append(f"  - {content}")

        # Global knowledge
        if context["global_knowledge"]:
            has_content = True
            if lines:
                lines.append("")
            lines.append("🌍 Cross-project knowledge:")
            for k in context["global_knowledge"][:2]:
                content = k.get('content', '')[:80]
                project = k.get('project', 'unknown')
                lines.append(f"  - [{project}] {content}")

        if not has_content:
            return ""

        return "\n".join([
            "",
            "=" * 50,
            "🧠 kimi-tachi Memory Context:",
            "=" * 50,
            *lines,
            "=" * 50,
            "",
        ])

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def get_exploration_stats(self) -> dict[str, Any]:
        """Get exploration statistics."""
        if self._adapter:
            return self._adapter.get_exploration_stats()
        return {"error": "Memory adapter not available"}

    async def search_code(self, query: str, limit: int = 10) -> list[dict]:
        """Search code symbols."""
        if not self._mn_memory or not self._mn_memory.store:
            return []

        try:
            results = await self._mn_memory.store.search(
                query=query,
                limit=limit,
                memory_types=["code"]
            )
            return self._format_memories(results)
        except Exception as e:
            console.print(f"[yellow]Code search failed: {e}[/yellow]")
            return []


# =============================================================================
# Backward Compatibility
# =============================================================================

# Keep old TachiMemory name for compatibility
TachiMemory = TachiMemoryV2

# Singleton instance
_memory_instance: TachiMemoryV2 | None = None


async def get_memory(project_path: str = ".") -> TachiMemoryV2:
    """Get or create singleton instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = await TachiMemoryV2.init(project_path)
    return _memory_instance


def reset_memory():
    """Reset singleton (useful for testing)."""
    global _memory_instance
    _memory_instance = None
