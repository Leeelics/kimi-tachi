import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import asyncio

from rich.console import Console
from rich.table import Table

# Optional memnexus import
try:
    from memnexus import CodeMemory, MemoryStore, MemoryType
    from memnexus.memory import MemoryEntry
    from memnexus.mechanisms.global_memory import GlobalMemory
    from memnexus.storage.git_storage import GitCommitStorage
    from memnexus.storage.code_storage import CodeSymbolStorage
    MEMNEXUS_AVAILABLE = True
except ImportError:
    MEMNEXUS_AVAILABLE = False

from .agent_profiles import AGENT_MEMORY_PROFILES

console = Console()


@dataclass
class MemoryConfig:
    """Configuration for TachiMemory."""
    
    project_path: str = "."
    storage_path: Optional[str] = None
    recall_limit: int = 10
    store_limit: int = 100
    search_limit: int = 10
    enable_global: bool = True
    global_project_name: Optional[str] = None
    
    # Auto-memory settings
    auto_recall: bool = True
    auto_store: bool = True
    
    def __post_init__(self):
        if self.storage_path is None:
            self.storage_path = os.path.join(
                self.project_path, ".kimi-tachi", "memory"
            )


class TachiMemory:
    """
    Automatic memory system for kimi-tachi.
    
    Wraps MemNexus with Seven Samurai-specific configurations
    for transparent memory integration.
    """
    
    def __init__(self, project_path: str = ".", config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig(project_path=project_path)
        self.project_path = Path(self.config.project_path).resolve()
        self._storage_path = Path(self.config.storage_path)
        
        # Memory stores
        self.memory: Optional[CodeMemory] = None
        self.global_memory: Optional[GlobalMemory] = None
        
        # Current session tracking
        self._current_session_id: Optional[str] = None
        self._session_start_time: Optional[str] = None
        
        # Lock for async operations
        self._lock = asyncio.Lock()
    
    @classmethod
    async def init(
        cls,
        project_path: str = ".",
        config: Optional[MemoryConfig] = None
    ) -> "TachiMemory":
        """
        Initialize TachiMemory with storage.
        
        Args:
            project_path: Path to the project root
            config: Optional memory configuration
            
        Returns:
            Initialized TachiMemory instance
        """
        if not MEMNEXUS_AVAILABLE:
            raise ImportError("memnexus is required for memory features")
        
        instance = cls(project_path, config)
        await instance._initialize_storage()
        return instance
    
    async def _initialize_storage(self):
        """Initialize memory storage backends."""
        # Ensure storage directory exists
        self._storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize CodeMemory (local project memory)
        self.memory = await CodeMemory.init(
            project_path=str(self.project_path),
            storage_path=str(self._storage_path / "code")
        )
        
        # Initialize GlobalMemory (cross-project knowledge)
        if self.config.enable_global:
            try:
                global_storage = self._storage_path / "global"
                global_storage.mkdir(parents=True, exist_ok=True)
                
                self.global_memory = GlobalMemory(
                    storage_path=str(global_storage)
                )
                await self.global_memory.initialize()
            except Exception as e:
                console.print(f"[yellow]Global memory not available: {e}[/yellow]")
                self.global_memory = None
    
    # ========== Project Indexing ==========
    
    async def index_project(
        self,
        git: bool = True,
        code: bool = True,
        files: Optional[List[str]] = None,
        incremental: bool = False
    ) -> Dict[str, Any]:
        """
        Index project into memory.
        
        Args:
            git: Index git history
            code: Index code symbols
            files: Specific files to index (None for all)
            incremental: Only index changed files
            
        Returns:
            Statistics about indexed data
        """
        if not self.memory:
            raise RuntimeError("Memory not initialized")
        
        stats = {"files_indexed": 0, "git_commits": 0, "code_symbols": 0}
        
        with console.status("[cyan]Indexing project...[/cyan]"):
            # Use MemNexus's index method
            result = await self.memory.index(
                git=git,
                code=code,
                files=files,
                incremental=incremental
            )
            
            stats.update(result)
        
        console.print(f"[green]✓ Indexed:[/green] {stats}")
        return stats
    
    # ========== Search ==========
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        memory_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search project memory.
        
        Args:
            query: Search query
            limit: Maximum results
            memory_types: Filter by memory types
            
        Returns:
            List of matching memories
        """
        if not self.memory or not self.memory.store:
            return []
        
        try:
            results = await self.memory.store.search(
                query=query,
                limit=limit,
                memory_types=memory_types
            )
            
            # Convert to serializable format
            return [
                {
                    "id": r.id if hasattr(r, 'id') else str(i),
                    "content": r.content if hasattr(r, 'content') else str(r),
                    "type": r.memory_type.value if hasattr(r, 'memory_type') else 'unknown',
                    "source": r.source if hasattr(r, 'source') else 'unknown',
                    "score": r.score if hasattr(r, 'score') else 1.0,
                }
                for i, r in enumerate(results)
            ]
        except Exception as e:
            console.print(f"[yellow]Search failed: {e}[/yellow]")
            return []
    
    async def search_code(
        self,
        query: str,
        limit: int = 10,
        symbol_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search code symbols.
        
        Args:
            query: Search query
            limit: Maximum results
            symbol_types: Filter by symbol types (function, class, etc.)
            
        Returns:
            List of matching code symbols
        """
        return await self.search(
            query=query,
            limit=limit,
            memory_types=["code"]
        )
    
    async def search_global_memory(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search global (cross-project) memory.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching global memories
        """
        if not self.global_memory:
            return []
        
        try:
            results = await self.global_memory.search(query=query, limit=limit)
            
            return [
                {
                    "content": r.get("content", ""),
                    "project": r.get("project", "unknown"),
                    "type": r.get("type", "unknown"),
                    "score": r.get("score", 0),
                }
                for r in results
            ]
        except Exception as e:
            console.print(f"[yellow]Global search failed: {e}[/yellow]")
            return []
    
    # ========== Agent Context ==========
    
    async def recall_agent_context(
        self,
        agent_type: str,
        task: str = ""
    ) -> Dict[str, Any]:
        """
        Recall context for an agent.
        
        Automatically retrieves:
        - Recent project memories relevant to the agent
        - Global knowledge if enabled
        - Previous decisions by this agent
        
        Args:
            agent_type: Type of agent (kamaji, nekobasu, etc.)
            task: Current task description
            
        Returns:
            Context dictionary with memories and knowledge
        """
        profile = AGENT_MEMORY_PROFILES.get(agent_type, AGENT_MEMORY_PROFILES["default"])
        
        context = {
            "agent_type": agent_type,
            "task": task,
            "recent_context": [],
            "global_knowledge": [],
            "previous_decisions": [],
        }
        
        # Check if should recall (recall_on_start list is not empty)
        should_recall = bool(profile.recall_on_start) if hasattr(profile, 'recall_on_start') else True
        
        # Search recent project memories
        if self.memory and self.memory.store and should_recall:
            search_query = task or agent_type
            try:
                recent = await self.memory.store.search(
                    query=search_query,
                    limit=getattr(profile, 'search_limit', 10),
                    memory_types=None
                )
                context["recent_context"] = [
                    {
                        "content": r.content if hasattr(r, 'content') else str(r),
                        "type": r.memory_type.value if hasattr(r, 'memory_type') else 'unknown',
                        "source": r.source if hasattr(r, 'source') else 'unknown',
                    }
                    for r in recent
                ]
            except Exception as e:
                console.print(f"[yellow]Could not recall context: {e}[/yellow]")
        
        # Search global memory for knowledge (always try if available)
        if self.global_memory:
            try:
                global_query = f"{agent_type} {task}".strip()
                global_results = await self.global_memory.search(
                    query=global_query,
                    limit=3
                )
                context["global_knowledge"] = global_results
            except Exception as e:
                console.print(f"[yellow]Could not search global memory: {e}[/yellow]")
        
        return context
    
    async def store_agent_output(
        self,
        agent: str,
        output: str,
        task: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Store agent output to memory.
        
        Args:
            agent: Agent type
            output: Output content to store
            task: Task description
            metadata: Additional metadata
            
        Returns:
            Memory ID if stored successfully
        """
        profile = AGENT_MEMORY_PROFILES.get(agent, AGENT_MEMORY_PROFILES["default"])
        
        # Check if should store (store_on_end list is not empty)
        should_store = bool(profile.store_on_end) if hasattr(profile, 'store_on_end') else True
        if not should_store:
            return None
        
        if not self.memory or not self.memory.store:
            return None
        
        try:
            memory_entry = MemoryEntry(
                content=output,
                memory_type=MemoryType.DECISION,
                source=f"agent:{agent}",
                metadata={
                    "agent": agent,
                    "task": task,
                    "session_id": self._current_session_id,
                    **(metadata or {})
                }
            )
            
            memory_id = await self.memory.store.store(memory_entry)
            return memory_id
            
        except Exception as e:
            console.print(f"[yellow]Could not store agent output: {e}[/yellow]")
            return None
    
    # ========== Session Management ==========
    
    def start_session(self, session_id: Optional[str] = None) -> str:
        """
        Start a new memory session.
        
        Args:
            session_id: Optional session ID (auto-generated if not provided)
            
        Returns:
            Session ID
        """
        import uuid
        from datetime import datetime
        
        self._current_session_id = session_id or str(uuid.uuid4())[:8]
        self._session_start_time = datetime.now().isoformat()
        
        return self._current_session_id
    
    async def get_session_history(
        self,
        session_id: Optional[str] = None,
        agent: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get memories from a specific session.
        
        Args:
            session_id: Session ID (current session if None)
            agent: Filter by agent type
            
        Returns:
            List of session memories
        """
        if not self.memory or not self.memory.store:
            return []
        
        sid = session_id or self._current_session_id
        if not sid:
            return []
        
        try:
            # Search for session memories
            all_memories = await self.memory.store.search(
                query=f"session_id:{sid}",
                limit=100
            )
            
            # Filter by agent if specified
            if agent:
                all_memories = [
                    m for m in all_memories
                    if m.metadata.get("agent") == agent
                ]
            
            return [
                {
                    "content": m.content,
                    "source": m.source,
                    "type": m.memory_type.value,
                    "timestamp": m.timestamp.isoformat() if hasattr(m, 'timestamp') else None,
                }
                for m in all_memories
            ]
        except Exception as e:
            console.print(f"[yellow]Could not get history: {e}[/yellow]")
            return []
    
    # ========== Global Memory Integration ==========
    
    async def register_in_global_memory(self, project_name: str) -> bool:
        """
        Register current project in global memory.
        
        Args:
            project_name: Name to register project under
            
        Returns:
            True if successful
        """
        if not self.global_memory:
            console.print("[yellow]Global memory not available[/yellow]")
            return False
        
        try:
            await self.global_memory.register_project(
                project_name,
                str(self.project_path)
            )
            console.print(f"[green]✓ Registered {project_name} in global memory[/green]")
            return True
        except Exception as e:
            console.print(f"[yellow]Could not register: {e}[/yellow]")
            return False
    
    async def sync_to_global_memory(
        self,
        project_name: str,
        incremental: bool = True
    ) -> Dict[str, int]:
        """
        Sync project memories to global memory.
        
        Args:
            project_name: Project name in global memory
            incremental: Only sync new/changed memories
            
        Returns:
            Sync statistics
        """
        if not self.global_memory:
            return {"synced": 0}
        
        try:
            result = await self.global_memory.sync_project(
                project_name,
                incremental=incremental
            )
            
            console.print(f"[green]✓ Synced {result.get('synced', 0)} memories to global[/green]")
            return result
            
        except Exception as e:
            console.print(f"[yellow]Could not sync: {e}[/yellow]")
            return {"synced": 0, "error": str(e)}
    
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


# Singleton instance for get_memory()
_memory_instance: Optional[TachiMemory] = None


async def get_memory(project_path: str = ".") -> TachiMemory:
    """
    Get or create singleton TachiMemory instance.
    
    Args:
        project_path: Path to project root
        
    Returns:
        TachiMemory instance
    """
    global _memory_instance
    
    if _memory_instance is None:
        _memory_instance = await TachiMemory.init(project_path)
    
    return _memory_instance


def reset_memory():
    """Reset singleton instance (useful for testing)."""
    global _memory_instance
    _memory_instance = None
