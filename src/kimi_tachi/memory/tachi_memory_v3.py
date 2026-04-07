"""
TachiMemory v3 - Uses memnexus 0.4.0+ Session Explorer

This version replaces the temporary implementation with memnexus native APIs.

Requirements:
    - memnexus>=0.4.0
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console

# memnexus imports
try:
    from memnexus import CodeMemory, GlobalMemory
    from memnexus.session import (
        DecisionDeduplicator,
        ExploreOptions,
        SessionExplorer,
    )

    MEMNEXUS_AVAILABLE = True
except ImportError as e:
    MEMNEXUS_AVAILABLE = False
    _import_error = e

# Team management
try:
    from ..team import TeamManager

    TEAM_AVAILABLE = True
except ImportError:
    TEAM_AVAILABLE = False
    TeamManager = None

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

    # Team isolation settings
    team_id: str | None = None  # Team ID for memory isolation
    enable_shared_memory: bool = True  # Enable cross-team shared memory layer

    # Auto-memory settings
    auto_recall: bool = True
    auto_store: bool = True

    # Session exploration settings
    proactive_explore: bool = True
    exploration_limit: int = 5
    min_relevance: float = 0.2

    def __post_init__(self):
        if self.storage_path is None:
            base_path = os.path.join(self.project_path, ".kimi-tachi", "memory")
            # Add team subdirectory if team_id is specified
            if self.team_id:
                self.storage_path = os.path.join(base_path, self.team_id)
            else:
                self.storage_path = base_path


class _MemoryWrapper:
    """Wrapper to allow tests to set memory.store."""

    def __init__(self, tachi_memory: TachiMemory):
        self._tm = tachi_memory

    @property
    def store(self) -> Any:
        return self._tm._mock_store

    @store.setter
    def store(self, value: Any) -> None:
        self._tm._mock_store = value


class TachiMemory:
    """
    Automatic memory system for kimi-tachi (v3 - memnexus 0.4.0+).

    Uses memnexus for all storage operations:
    - CodeMemory: Project-specific code memories
    - GlobalMemory: Cross-project knowledge
    - SessionExplorer: Cross-session context discovery
    - DecisionDeduplicator: Content deduplication
    """

    def __init__(self, project_path: str = ".", config: MemoryConfig | None = None):
        if not MEMNEXUS_AVAILABLE:
            raise ImportError(
                f"memnexus>=0.4.0 is required. Install with: uv pip install memnexus>=0.4.0\n"
                f"Import error: {_import_error}"
            )

        self.config = config or MemoryConfig(project_path=project_path)
        self.project_path = Path(self.config.project_path).resolve()
        self._storage_path = Path(self.config.storage_path)

        # memnexus components
        self._mn_memory: CodeMemory | None = None
        self._mn_global: GlobalMemory | None = None
        self._mn_explorer: SessionExplorer | None = None
        self._mn_deduplicator: DecisionDeduplicator | None = None

        # Session tracking
        self._current_session_id: str | None = None
        self._session_start_time: str | None = None

        # Lock for async operations
        self._lock = asyncio.Lock()

        # Backward compatibility: mock store wrapper for tests
        self._mock_store: Any = None

    @property
    def memory(self) -> Any:
        """Backward compatible property for tests."""
        # Return a wrapper that allows setting store
        return _MemoryWrapper(self)

    @memory.setter
    def memory(self, value: Any) -> None:
        """Allow tests to inject mock memory."""
        if value is None:
            self._mn_memory = None
            self._mock_store = None

    @property
    def global_memory(self) -> Any:
        """Backward compatible property for tests."""
        return self._mn_global

    @global_memory.setter
    def global_memory(self, value: Any) -> None:
        """Allow tests to set global_memory."""
        self._mn_global = value

    @classmethod
    async def init(cls, project_path: str = ".", config: MemoryConfig | None = None) -> TachiMemory:
        """Initialize TachiMemory with memnexus components."""
        instance = cls(project_path, config)
        await instance._initialize_storage()
        return instance

    def _ensure_mnx_config(self):
        """Ensure .mnx/ directory and config exist (uses .mnx instead of .memnexus)."""
        mnx_path = self.project_path / ".mnx"
        config_path = mnx_path / "config.yaml"

        # Create .mnx directory
        mnx_path.mkdir(parents=True, exist_ok=True)

        # Create default config if not exists
        if not config_path.exists():
            from datetime import datetime

            import yaml

            default_config = {
                "version": "1.0",
                "project": {
                    "name": self.project_path.name,
                    "root": str(self.project_path),
                    "initialized_at": datetime.now().isoformat(),
                },
                "memory": {
                    "backend": "lancedb",
                    "path": ".mnx/memory.lance",
                },
                "embedding": {
                    "method": "tfidf",
                    "dim": 384,
                },
                "git": {
                    "enabled": True,
                    "max_history": 1000,
                },
                "code": {
                    "languages": ["python", "javascript", "typescript", "rust", "go"],
                    "exclude_patterns": [
                        "*.pyc",
                        "__pycache__/",
                        "node_modules/",
                        ".git/",
                        ".venv/",
                        ".mnx/",
                    ],
                },
            }

            with open(config_path, "w") as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)

    async def _initialize_storage(self):
        """Initialize memnexus storage backends."""
        self._storage_path.mkdir(parents=True, exist_ok=True)

        # Ensure .mnx/ config exists before memnexus init
        self._ensure_mnx_config()

        # CodeMemory for project-specific memories
        try:
            self._mn_memory = await CodeMemory.init(project_path=str(self.project_path))
        except Exception as e:
            console.print(f"[yellow]CodeMemory not available: {e}[/yellow]")

        # GlobalMemory for cross-project knowledge
        if self.config.enable_global:
            try:
                self._mn_global = await GlobalMemory.init()
            except Exception as e:
                console.print(f"[yellow]Global memory not available: {e}[/yellow]")

        # SessionExplorer for cross-session discovery (memnexus 0.4.0+)
        self._mn_explorer = SessionExplorer()

        # DecisionDeduplicator for content deduplication (memnexus 0.4.0+)
        # Use project-specific storage path to avoid conflicts between projects
        dedup_path = self._storage_path / "deduplicator"
        self._mn_deduplicator = DecisionDeduplicator(storage_path=dedup_path)

    # ========================================================================
    # Core Memory Operations
    # ========================================================================

    async def recall_for_task(self, task: str, agent_type: str | None = None) -> dict[str, Any]:
        """
        Recall context for a task using memnexus Session Explorer.

        Args:
            task: Task description
            agent_type: Optional agent type for profile-based recall

        Returns:
            Context dictionary with memories and formatted output
        """
        context = {
            "task": task,
            "agent_type": agent_type,
            "project_memories": [],
            "related_decisions": [],
            "global_knowledge": [],
            "formatted_output": "",
        }

        # 1. Search project memory (CodeMemory)
        if self._mn_memory:
            try:
                results = await self._mn_memory.search(query=task, limit=self.config.recall_limit)
                context["project_memories"] = self._format_memories(results)
            except Exception as e:
                console.print(f"[dim]Project memory search: {e}[/dim]")

        # 2. Explore related sessions (SessionExplorer - memnexus 0.4.0+)
        if self._mn_explorer and self.config.proactive_explore:
            try:
                options = ExploreOptions(
                    limit=self.config.exploration_limit,
                    min_relevance=self.config.min_relevance,
                    skip_explored=True,
                )

                result = await self._mn_explorer.explore_related(
                    current_session_id=self._current_session_id or "unknown",
                    query=task,
                    context={"cwd": str(self.project_path), "agent": agent_type},
                    options=options,
                )

                context["related_decisions"] = [
                    {"content": d.content, "source": d.source_session} for d in result.decisions
                ]
                context["exploration_stats"] = {
                    "explored_sessions": len(result.explored_sessions),
                    "total_relevance": result.total_relevance,
                }
            except Exception as e:
                console.print(f"[dim]Session exploration: {e}[/dim]")

        # 3. Search global memory (GlobalMemory)
        if self._mn_global:
            try:
                results = await self._mn_global.search(query=task, limit=3)
                context["global_knowledge"] = [
                    {"content": r.content, "project": r.project, "type": r.type} for r in results
                ]
            except Exception as e:
                console.print(f"[dim]Global memory search: {e}[/dim]")

        # 4. Format for kimi-cli
        context["formatted_output"] = self._format_for_cli(context)

        return context

    async def store_decision(self, content: str, metadata: dict | None = None) -> str | None:
        """
        Store a decision with automatic deduplication.

        Uses memnexus DecisionDeduplicator for content fingerprinting.

        Args:
            content: Decision content
            metadata: Additional metadata

        Returns:
            Fingerprint hash if stored, None if duplicate
        """
        if not self._mn_deduplicator:
            return None

        try:
            # Check for duplicates (memnexus 0.4.0+)
            check = await self._mn_deduplicator.check_duplicate(content)
            if check.is_duplicate and check.confidence > 0.9:
                return None

            # Add fingerprint (memnexus 0.4.0+)
            fingerprint = await self._mn_deduplicator.add_fingerprint(
                content=content, source_session=self._current_session_id or "", metadata=metadata
            )

            return fingerprint

        except Exception as e:
            console.print(f"[yellow]Could not store decision: {e}[/yellow]")
            return None

    def start_session(self, session_id: str | None = None, task: str = "") -> str:
        """Start a new memory session."""
        import uuid
        from datetime import datetime

        self._current_session_id = session_id or str(uuid.uuid4())[:8]
        self._session_start_time = datetime.now().isoformat()

        return self._current_session_id

    # ========================================================================
    # CLI Formatting
    # ========================================================================

    def _format_memories(self, results: list[Any]) -> list[dict]:
        """Format memnexus results for CLI."""
        formatted = []
        for r in results:
            formatted.append(
                {
                    "content": getattr(r, "content", str(r))[:200],
                    "type": getattr(r, "type", "unknown"),
                    "source": getattr(r, "file", getattr(r, "source", "unknown")),
                    "score": getattr(r, "score", 1.0),
                }
            )
        return formatted

    def _format_for_cli(self, context: dict) -> str:
        """Format context for kimi-cli output."""
        lines = []
        has_content = False

        # Related decisions from other sessions (SessionExplorer)
        if context.get("related_decisions"):
            has_content = True
            lines.append("📚 Related decisions from other sessions:")
            for d in context["related_decisions"][:3]:
                source = d.get("source", "unknown")[:8]
                content = d.get("content", "")[:80]
                lines.append(f"  - [{source}] {content}")

        # Project memories
        if context.get("project_memories"):
            has_content = True
            if lines:
                lines.append("")
            lines.append("📋 Recent project context:")
            for m in context["project_memories"][:3]:
                content = m.get("content", "")[:80]
                lines.append(f"  - {content}")

        # Global knowledge
        if context.get("global_knowledge"):
            has_content = True
            if lines:
                lines.append("")
            lines.append("🌍 Cross-project knowledge:")
            for k in context["global_knowledge"][:2]:
                content = k.get("content", "")[:80]
                project = k.get("project", "unknown")
                lines.append(f"  - [{project}] {content}")

        if not has_content:
            return ""

        return "\n".join(
            [
                "",
                "=" * 50,
                "🧠 kimi-tachi Memory Context:",
                "=" * 50,
                *lines,
                "=" * 50,
                "",
            ]
        )

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_exploration_stats(self) -> dict[str, Any]:
        """Get exploration statistics from SessionExplorer."""
        if self._mn_explorer:
            return self._mn_explorer.get_stats()
        return {"error": "SessionExplorer not available"}

    # ========================================================================
    # Backward Compatible Methods
    # ========================================================================

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search project memory (backward compatible)."""
        # Check for mock store (used in tests)
        if self._mock_store is not None:
            results = await self._mock_store.search(query=query, limit=limit)
            return self._format_memories(results)

        if not self._mn_memory:
            return []
        try:
            results = await self._mn_memory.search(query=query, limit=limit)
            return self._format_memories(results)
        except Exception as e:
            console.print(f"[yellow]Search failed: {e}[/yellow]")
            return []

    async def recall_agent_context(self, agent_type: str, task: str = "") -> dict[str, Any]:
        """Recall context for an agent (backward compatible)."""
        context = await self.recall_for_task(task, agent_type)
        # Add backward compatible fields
        context["recent_context"] = context.get("project_memories", [])
        context["previous_decisions"] = context.get("related_decisions", [])
        return context

    async def store_agent_output(
        self, agent: str, output: str, task: str = "", metadata: dict | None = None
    ) -> str | None:
        """Store agent output to memory (backward compatible)."""
        return await self.store_decision(output, metadata)

    async def search_code(self, query: str, limit: int = 10) -> list[dict]:
        """Search code symbols using CodeMemory."""
        if not self._mn_memory:
            return []

        try:
            results = await self._mn_memory.search_code(query=query, limit=limit)
            return self._format_memories(results)
        except Exception as e:
            console.print(f"[yellow]Code search failed: {e}[/yellow]")
            return []

    async def close(self):
        """Close all memnexus connections."""
        if self._mn_explorer:
            self._mn_explorer.close()
        if self._mn_deduplicator:
            self._mn_deduplicator.close()
        if self._mn_memory:
            await self._mn_memory.close()
        if self._mn_global:
            await self._mn_global.close()


# Singleton instance
_memory_instance: TachiMemory | None = None
_team_memory_instances: dict[str, TachiMemory] = {}  # team_id -> TachiMemory


async def get_memory(project_path: str = ".", team_id: str | None = None) -> TachiMemory:
    """
    Get or create singleton TachiMemory instance.

    Args:
        project_path: Project path
        team_id: Optional team ID for team-specific memory

    Returns:
        TachiMemory instance (team-specific or global)
    """
    global _memory_instance, _team_memory_instances

    # If team_id specified, use team-specific instance
    if team_id:
        if team_id not in _team_memory_instances:
            config = MemoryConfig(project_path=project_path, team_id=team_id)
            _team_memory_instances[team_id] = await TachiMemory.init(project_path, config)
        return _team_memory_instances[team_id]

    # Otherwise use global instance
    if _memory_instance is None:
        _memory_instance = await TachiMemory.init(project_path)
    return _memory_instance


async def get_memory_for_current_team(project_path: str = ".") -> TachiMemory:
    """
    Get TachiMemory instance for the current team.

    Automatically detects the current team from TeamManager.
    """
    if TEAM_AVAILABLE and TeamManager:
        manager = TeamManager()
        team_id = manager.get_effective_team_id()
        return await get_memory(project_path, team_id)

    # Fallback to global memory
    return await get_memory(project_path)


def reset_memory(team_id: str | None = None):
    """
    Reset singleton instance (useful for testing).

    Args:
        team_id: Specific team to reset, or None to reset all
    """
    global _memory_instance, _team_memory_instances

    if team_id:
        # Reset specific team
        if team_id in _team_memory_instances:
            _team_memory_instances[team_id].close()
            del _team_memory_instances[team_id]
    else:
        # Reset all
        if _memory_instance:
            _memory_instance.close()
        _memory_instance = None

        for tm in _team_memory_instances.values():
            tm.close()
        _team_memory_instances.clear()
