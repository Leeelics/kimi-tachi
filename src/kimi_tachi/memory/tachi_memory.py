"""
TachiMemory - Kimi-Tachi integration with MemNexus

Provides:
- Project-level code memory (Git history, code structure)
- Agent-specific context management
- Explicit memory commands (save/recall/search)

Note: This is the explicit memory version (v0.5.0-alpha).
Future versions will integrate with kimi-cli hooks for automatic management.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from rich.console import Console
from rich.table import Table

# Optional import - memory is optional
try:
    from memnexus import CodeMemory
    from memnexus.memory.context import ContextManager
    MEMNEXUS_AVAILABLE = True
except ImportError:
    MEMNEXUS_AVAILABLE = False
    CodeMemory = None
    ContextManager = None

from kimi_tachi.config import get_config

console = Console()


@dataclass
class MemoryConfig:
    """Configuration for TachiMemory."""
    enabled: bool = True
    auto_index: bool = True
    project_path: Optional[Path] = None
    
    # Agent-specific settings
    store_on_switch: bool = True
    recall_on_start: bool = True
    
    # Search settings
    search_limit: int = 10
    min_relevance_score: float = 0.5


@dataclass 
class AgentContext:
    """Context for an agent session."""
    agent_type: str
    session_id: str
    recent_memories: List[Dict] = field(default_factory=list)
    relevant_code: List[Dict] = field(default_factory=list)
    project_summary: str = ""
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class TachiMemory:
    """
    Kimi-Tachi memory layer using MemNexus.
    
    This class provides explicit memory management for the Seven Samurai.
    Users can manually save/recall context, or enable auto-save.
    
    Example:
        >>> memory = await TachiMemory.init("./my-project")
        >>> 
        >>> # Index the project
        >>> await memory.index_project()
        >>> 
        >>> # Before using an agent, recall its context
        >>> context = await memory.recall_agent_context("kamaji")
        >>> 
        >>> # After agent finishes, store its output
        >>> await memory.store_agent_output("kamaji", output, task)
        >>> 
        >>> # Search for specific information
        >>> results = await memory.search("JWT authentication")
    """
    
    def __init__(self, project_path: Union[str, Path], config: Optional[MemoryConfig] = None):
        """
        Initialize TachiMemory.
        
        Args:
            project_path: Path to the project directory
            config: Optional memory configuration
        """
        if not MEMNEXUS_AVAILABLE:
            raise RuntimeError(
                "MemNexus is not installed. "
                "Install with: pip install memnexus"
            )
        
        self.project_path = Path(project_path).resolve()
        self.config = config or MemoryConfig()
        
        # Core components (initialized lazily)
        self._code_memory: Optional[CodeMemory] = None
        self._context_manager: Optional[ContextManager] = None
        self._initialized = False
        
        # Session tracking
        self._current_session_id: Optional[str] = None
        self._agent_contexts: Dict[str, AgentContext] = {}
    
    @classmethod
    async def init(
        cls,
        project_path: Union[str, Path] = ".",
        config: Optional[MemoryConfig] = None,
    ) -> TachiMemory:
        """
        Initialize TachiMemory with async setup.
        
        This is the recommended way to create a TachiMemory instance.
        
        Args:
            project_path: Path to project directory
            config: Optional configuration
            
        Returns:
            Initialized TachiMemory instance
        """
        instance = cls(project_path, config)
        await instance._initialize()
        return instance
    
    async def _initialize(self) -> None:
        """Initialize MemNexus components."""
        if self._initialized:
            return
        
        # Initialize CodeMemory
        self._code_memory = await CodeMemory.init(self.project_path)
        
        # Initialize context manager with unique session ID
        session_id = f"tachi_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._current_session_id = session_id
        
        if ContextManager:
            self._context_manager = ContextManager(session_id)
            await self._context_manager.initialize()
        
        self._initialized = True
        
        console.print(f"[dim]Memory initialized: {self.project_path}[/dim]")
    
    # ========== Project Indexing ==========
    
    async def index_project(self, git: bool = True, code: bool = True) -> Dict[str, int]:
        """
        Index the project for memory.
        
        Args:
            git: Index Git history
            code: Index code structure
            
        Returns:
            Statistics about indexed items
        """
        if not self._initialized:
            raise RuntimeError("Memory not initialized. Call init() first.")
        
        stats = {"git_commits": 0, "code_symbols": 0}
        
        with console.status("[bold green]Indexing project..."):
            if git:
                try:
                    await self._code_memory.index_git_history()
                    stats["git_commits"] = self._code_memory._stats.get("git_commits_indexed", 0)
                    console.print(f"[green]✓[/green] Indexed {stats['git_commits']} Git commits")
                except Exception as e:
                    console.print(f"[yellow]⚠ Git indexing skipped: {e}[/yellow]")
            
            if code:
                try:
                    await self._code_memory.index_codebase()
                    stats["code_symbols"] = self._code_memory._stats.get("code_symbols_indexed", 0)
                    console.print(f"[green]✓[/green] Indexed {stats['code_symbols']} code symbols")
                except Exception as e:
                    console.print(f"[yellow]⚠ Code indexing skipped: {e}[/yellow]")
        
        return stats
    
    async def get_index_status(self) -> Dict[str, Any]:
        """Get current indexing status."""
        if not self._initialized:
            return {"initialized": False}
        
        return {
            "initialized": True,
            "project_path": str(self.project_path),
            "session_id": self._current_session_id,
            "stats": self._code_memory._stats if self._code_memory else {},
        }
    
    # ========== Search ==========
    
    async def search(
        self,
        query: str,
        limit: Optional[int] = None,
        include_code: bool = True,
        include_git: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search project memory.
        
        Args:
            query: Search query
            limit: Maximum results (default from config)
            include_code: Include code results
            include_git: Include Git history results
            
        Returns:
            List of search results
        """
        if not self._initialized:
            raise RuntimeError("Memory not initialized")
        
        limit = limit or self.config.search_limit
        results = []
        
        with console.status(f"[bold blue]Searching: {query[:50]}..."):
            # General search
            try:
                general_results = await self._code_memory.search(query, limit=limit)
                results.extend([
                    {
                        "type": "general",
                        "content": r.content,
                        "source": r.source,
                        "score": r.score,
                    }
                    for r in general_results
                ])
            except Exception as e:
                console.print(f"[yellow]Search warning: {e}[/yellow]")
            
            # Code search
            if include_code:
                try:
                    code_results = await self._code_memory.search_code(query, limit=limit)
                    results.extend([
                        {
                            "type": "code",
                            "name": r.name,
                            "symbol_type": r.symbol_type,
                            "file_path": r.file_path,
                            "line_range": (r.start_line, r.end_line),
                            "signature": r.signature,
                        }
                        for r in code_results
                    ])
                except Exception as e:
                    pass  # Code search is optional
        
        return results
    
    async def search_code(
        self,
        query: str,
        language: Optional[str] = None,
        symbol_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search code specifically.
        
        Args:
            query: Search query (function name, concept, etc.)
            language: Filter by language (python, javascript, etc.)
            symbol_type: Filter by type (function, class, method)
            limit: Maximum results
            
        Returns:
            List of code search results
        """
        if not self._initialized:
            raise RuntimeError("Memory not initialized")
        
        limit = limit or self.config.search_limit
        
        results = await self._code_memory.search_code(query, limit=limit)
        
        # Filter results
        filtered = []
        for r in results:
            if language and r.language != language:
                continue
            if symbol_type and r.symbol_type != symbol_type:
                continue
            filtered.append({
                "name": r.name,
                "type": r.symbol_type,
                "file": r.file_path,
                "lines": f"{r.start_line}-{r.end_line}",
                "signature": r.signature,
                "docstring": r.docstring[:200] if r.docstring else "",
            })
        
        return filtered
    
    # ========== Agent Context Management ==========
    
    async def store_agent_output(
        self,
        agent_type: str,
        output: str,
        task: str,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Store agent output to memory.
        
        Args:
            agent_type: Agent type (kamaji, nekobasu, etc.)
            output: Agent output content
            task: Task description
            metadata: Additional metadata
            
        Returns:
            Memory entry ID
        """
        if not self._initialized or not self._context_manager:
            console.print("[dim]Memory not available, skipping store[/dim]")
            return ""
        
        content = f"Task: {task}\n\nOutput:\n{output}"
        
        memory_id = await self._context_manager.store_agent_output(
            agent=agent_type,
            content=content,
            memory_type="agent_output",
            metadata={
                "task": task,
                "agent_type": agent_type,
                **(metadata or {}),
            },
        )
        
        console.print(f"[dim]Stored memory for {agent_type}: {memory_id[:8]}...[/dim]")
        return memory_id
    
    async def store_agent_context(
        self,
        agent_type: str,
        context: Dict[str, Any],
    ) -> None:
        """
        Store full agent context before switching.
        
        Args:
            agent_type: Agent type
            context: Context dictionary
        """
        # Create AgentContext object
        agent_ctx = AgentContext(
            agent_type=agent_type,
            session_id=self._current_session_id or "unknown",
            recent_memories=context.get("recent_memories", []),
            relevant_code=context.get("relevant_code", []),
            project_summary=context.get("project_summary", ""),
            user_preferences=context.get("user_preferences", {}),
        )
        
        self._agent_contexts[agent_type] = agent_ctx
        
        # Also store to persistent memory
        if self._context_manager:
            await self._context_manager.store_agent_output(
                agent=agent_type,
                content=context.get("summary", ""),
                memory_type="agent_context",
                metadata={
                    "agent_type": agent_type,
                    "full_context": context,
                },
            )
    
    async def recall_agent_context(
        self,
        agent_type: str,
        query: Optional[str] = None,
    ) -> AgentContext:
        """
        Recall context for an agent.
        
        Args:
            agent_type: Agent type to recall
            query: Optional query to find relevant context
            
        Returns:
            AgentContext with recalled information
        """
        if not self._initialized:
            return AgentContext(agent_type=agent_type, session_id="")
        
        # Check in-memory cache first
        if agent_type in self._agent_contexts:
            return self._agent_contexts[agent_type]
        
        # Build context from memory
        context = AgentContext(
            agent_type=agent_type,
            session_id=self._current_session_id or "",
        )
        
        # Get recent memories from this session
        if self._context_manager:
            try:
                recent = await self._context_manager.get_conversation_history(limit=20)
                context.recent_memories = [
                    {"content": m.content, "source": m.source, "type": m.memory_type}
                    for m in recent
                ]
            except Exception:
                pass
        
        # Search for relevant code
        if query:
            try:
                code_results = await self.search_code(query, limit=5)
                context.relevant_code = code_results
            except Exception:
                pass
        
        # Get project summary
        try:
            status = await self.get_index_status()
            context.project_summary = f"Project: {status.get('project_path', 'Unknown')}"
        except Exception:
            pass
        
        return context
    
    # ========== Session Management ==========
    
    async def save_session_summary(self, summary: str, key_decisions: List[str]) -> None:
        """Save summary of current session."""
        if not self._context_manager:
            return
        
        content = f"Session Summary:\n{summary}\n\nKey Decisions:\n" + "\n".join(f"- {d}" for d in key_decisions)
        
        await self._context_manager.store_agent_output(
            agent="session",
            content=content,
            memory_type="session_summary",
            metadata={
                "session_id": self._current_session_id,
                "key_decisions": key_decisions,
            },
        )
        
        console.print("[green]✓ Session summary saved[/green]")
    
    async def get_session_history(self, limit: int = 50) -> List[Dict]:
        """Get conversation history for current session."""
        if not self._context_manager:
            return []
        
        try:
            memories = await self._context_manager.get_conversation_history(limit=limit)
            return [
                {
                    "content": m.content,
                    "source": m.source,
                    "type": m.memory_type,
                    "timestamp": m.timestamp.isoformat() if hasattr(m, 'timestamp') else None,
                }
                for m in memories
            ]
        except Exception as e:
            console.print(f"[yellow]Could not get history: {e}[/yellow]")
            return []
    
    # ========== Utility ==========
    
    def format_search_results(self, results: List[Dict]) -> Table:
        """Format search results as Rich table."""
        table = Table(title="Search Results")
        table.add_column("Type", style="cyan", no_wrap=True)
        table.add_column("Source", style="green")
        table.add_column("Content", style="white")
        
        for r in results[:self.config.search_limit]:
            result_type = r.get("type", "unknown")
            source = r.get("source", r.get("file", "unknown"))[:50]
            
            if result_type == "code":
                content = f"{r.get('name', '')}: {r.get('signature', '')[:80]}"
            else:
                content = r.get("content", "")[:100]
            
            table.add_row(result_type, source, content)
        
        return table
