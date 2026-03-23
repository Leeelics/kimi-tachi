"""
Agent Factory - Dynamic Subagent Creation for Phase 2.1

This module provides the AgentFactory class for dynamically creating subagents
without loading MCP configurations, reducing MCP process count from 7 to ≤2.

Architecture:
- Fixed subagent mode: 1 main agent + 6 subagents = 7 MCP processes
- Dynamic subagent mode: 1 main agent (with MCP) + 0 subagent MCP = ≤2 MCP processes

Author: kimi-tachi Team
Phase: 2.1
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AgentConfig:
    """Configuration for an agent loaded from YAML"""

    name: str
    role: str
    description: str
    system_prompt: str = ""
    tools: list[str] = field(default_factory=list)
    raw_config: dict = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, config_path: Path) -> AgentConfig:
        """Load agent configuration from YAML file"""
        if not config_path.exists():
            raise FileNotFoundError(f"Agent config not found: {config_path}")

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        agent_data = data.get("agent", {})

        # Build system prompt from system_prompt_args
        system_prompt = cls._build_system_prompt(agent_data.get("system_prompt_args", {}))

        return cls(
            name=agent_data.get("name", config_path.stem),
            role=agent_data.get("name", "worker"),
            description=agent_data.get("description", ""),
            system_prompt=system_prompt,
            tools=agent_data.get("tools", []),
            raw_config=data,
        )

    @staticmethod
    def _build_system_prompt(args: dict) -> str:
        """Build system prompt from system_prompt_args"""
        if not args:
            return ""

        parts = []

        # Add ROLE if present
        if "ROLE" in args:
            parts.append(f"You are a {args['ROLE']}.")

        # Add ROLE_ADDITIONAL if present
        if "ROLE_ADDITIONAL" in args:
            parts.append(args["ROLE_ADDITIONAL"])

        return "\n\n".join(parts)


@dataclass
class DynamicSubagent:
    """Represents a dynamically created subagent instance"""

    id: str
    name: str
    config: AgentConfig
    created_at: float = field(default_factory=lambda: __import__("time").time())
    last_used: float = field(default_factory=lambda: __import__("time").time())
    use_count: int = 0

    def touch(self) -> None:
        """Update last used timestamp and increment use count"""
        self.last_used = __import__("time").time()
        self.use_count += 1


class AgentFactory:
    """
    Factory for creating dynamic subagents without MCP overhead.

    This factory implements the Phase 2.1 architecture for reducing MCP processes:
    - Loads agent configurations from YAML files
    - Creates lightweight subagent instances without MCP
    - Provides caching and lifecycle management
    - Supports fallback to fixed subagent mode via environment variable

    Environment Variables:
        KIMI_TACHI_DYNAMIC_AGENTS: Enable/disable dynamic creation (default: true)
        KIMI_TACHI_DEBUG_AGENTS: Enable debug logging (default: false)
        KIMI_TACHI_SUBAGENT_CACHE_TTL: Cache TTL in seconds (default: 300)

    Example:
        >>> factory = AgentFactory(agents_dir=Path("~/.kimi/agents/kimi-tachi"))
        >>> subagent = await factory.create_subagent("nekobasu")
        >>> print(subagent.id)  # "nekobasu_a1b2c3d4"
    """

    # Agent file mapping
    AGENT_FILES = {
        "shishigami": "shishigami.yaml",
        "nekobasu": "nekobasu.yaml",
        "calcifer": "calcifer.yaml",
        "enma": "enma.yaml",
        "tasogare": "tasogare.yaml",
        "phoenix": "phoenix.yaml",
    }

    # Agent metadata for quick reference
    AGENT_META = {
        "shishigami": {
            "name": "シシ神 (Shishigami)",
            "role": "architect",
            "description": "Architecture and system design",
            "icon": "🦌",
        },
        "nekobasu": {
            "name": "猫バス (Nekobasu)",
            "role": "explorer",
            "description": "Fast code exploration",
            "icon": "🚌",
        },
        "calcifer": {
            "name": "カルシファー (Calcifer)",
            "role": "builder",
            "description": "Implementation and coding",
            "icon": "🔥",
        },
        "enma": {
            "name": "閻魔大王 (Enma)",
            "role": "reviewer",
            "description": "Code review and quality",
            "icon": "👹",
        },
        "tasogare": {
            "name": "黄昏時 (Tasogare)",
            "role": "planner",
            "description": "Planning and research",
            "icon": "🌆",
        },
        "phoenix": {
            "name": "火の鳥 (Phoenix)",
            "role": "librarian",
            "description": "Documentation and knowledge",
            "icon": "🐦",
        },
    }

    def __init__(
        self,
        agents_dir: Path | str | None = None,
        cache_ttl: int | None = None,
    ):
        """
        Initialize the AgentFactory.

        Args:
            agents_dir: Directory containing agent YAML files.
                       Defaults to ~/.kimi/agents/kimi-tachi
            cache_ttl: Time-to-live for cached subagents in seconds.
                      Defaults to KIMI_TACHI_SUBAGENT_CACHE_TTL or 300
        """
        self.agents_dir = (
            Path(agents_dir) if agents_dir else (Path.home() / ".kimi" / "agents" / "kimi-tachi")
        )
        self.cache_ttl = cache_ttl or int(os.environ.get("KIMI_TACHI_SUBAGENT_CACHE_TTL", "300"))
        self.debug = os.environ.get("KIMI_TACHI_DEBUG_AGENTS", "").lower() in (
            "1",
            "true",
            "yes",
        )
        self.dynamic_mode = os.environ.get("KIMI_TACHI_DYNAMIC_AGENTS", "true").lower() not in (
            "0",
            "false",
            "no",
            "disabled",
        )

        # Cache for loaded agent configurations
        self._agent_configs: dict[str, AgentConfig] = {}

        # Cache for created subagent instances
        self._subagents: dict[str, DynamicSubagent] = {}

        # Statistics for monitoring
        self._stats = {
            "created": 0,
            "reused": 0,
            "destroyed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        if self.debug:
            print(f"[AgentFactory] Initialized with dynamic_mode={self.dynamic_mode}")
            print(f"[AgentFactory] agents_dir={self.agents_dir}")
            print(f"[AgentFactory] cache_ttl={self.cache_ttl}s")

    def is_dynamic_mode_enabled(self) -> bool:
        """Check if dynamic subagent creation is enabled"""
        return self.dynamic_mode

    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """
        Load or retrieve cached agent configuration.

        Args:
            agent_name: Name of the agent (e.g., "nekobasu")

        Returns:
            AgentConfig object with parsed configuration

        Raises:
            ValueError: If agent_name is unknown
            FileNotFoundError: If agent YAML file doesn't exist
        """
        # Return cached config if available
        if agent_name in self._agent_configs:
            if self.debug:
                print(f"[AgentFactory] Using cached config for {agent_name}")
            return self._agent_configs[agent_name]

        # Validate agent name
        if agent_name not in self.AGENT_FILES:
            raise ValueError(
                f"Unknown agent: {agent_name}. Available: {list(self.AGENT_FILES.keys())}"
            )

        # Load from YAML
        config_path = self.agents_dir / self.AGENT_FILES[agent_name]
        if self.debug:
            print(f"[AgentFactory] Loading config from {config_path}")

        config = AgentConfig.from_yaml(config_path)

        # Cache and return
        self._agent_configs[agent_name] = config
        return config

    async def create_subagent(
        self,
        agent_name: str,
        custom_id: str | None = None,
    ) -> DynamicSubagent:
        """
        Create or retrieve a dynamic subagent instance.

        In dynamic mode, this creates a lightweight subagent without MCP.
        The subagent can be used with the Task tool for execution.

        Args:
            agent_name: Name of the agent to create
            custom_id: Optional custom ID for the subagent instance

        Returns:
            DynamicSubagent instance with unique ID

        Raises:
            ValueError: If agent_name is unknown
            FileNotFoundError: If agent configuration is missing
        """
        # Check if we should use existing cached instance
        if agent_name in self._subagents:
            subagent = self._subagents[agent_name]
            # Check if still valid (not expired)
            import time

            age = time.time() - subagent.last_used
            if age < self.cache_ttl:
                subagent.touch()
                self._stats["reused"] += 1
                self._stats["cache_hits"] += 1
                if self.debug:
                    print(
                        f"[AgentFactory] Reusing cached subagent {subagent.id} "
                        f"(age={age:.1f}s, uses={subagent.use_count})"
                    )
                return subagent
            else:
                # Expired, remove from cache
                if self.debug:
                    print(f"[AgentFactory] Cache expired for {agent_name} (age={age:.1f}s)")
                del self._subagents[agent_name]

        # Load agent configuration
        config = self.get_agent_config(agent_name)

        # Generate unique ID
        subagent_id = custom_id or f"{agent_name}_{uuid.uuid4().hex[:8]}"

        # Create new subagent instance
        subagent = DynamicSubagent(
            id=subagent_id,
            name=agent_name,
            config=config,
        )

        # Cache the instance
        self._subagents[agent_name] = subagent

        self._stats["created"] += 1
        self._stats["cache_misses"] += 1

        if self.debug:
            print(f"[AgentFactory] Created subagent {subagent_id} for {agent_name}")

        return subagent

    def get_subagent(self, agent_name: str) -> DynamicSubagent | None:
        """
        Get cached subagent if it exists and is valid.

        Args:
            agent_name: Name of the agent

        Returns:
            DynamicSubagent if cached and valid, None otherwise
        """
        if agent_name not in self._subagents:
            return None

        subagent = self._subagents[agent_name]
        import time

        age = time.time() - subagent.last_used
        if age < self.cache_ttl:
            return subagent

        # Expired
        del self._subagents[agent_name]
        return None

    def destroy_subagent(self, agent_name: str) -> bool:
        """
        Remove a subagent from cache.

        Args:
            agent_name: Name of the agent to destroy

        Returns:
            True if subagent was found and removed, False otherwise
        """
        if agent_name in self._subagents:
            subagent = self._subagents.pop(agent_name)
            self._stats["destroyed"] += 1
            if self.debug:
                print(
                    f"[AgentFactory] Destroyed subagent {subagent.id} "
                    f"(total uses: {subagent.use_count})"
                )
            return True
        return False

    def cleanup_expired(self) -> int:
        """
        Remove expired subagents from cache.

        Returns:
            Number of subagents removed
        """
        import time

        now = time.time()
        expired = [
            name
            for name, subagent in self._subagents.items()
            if (now - subagent.last_used) >= self.cache_ttl
        ]

        for name in expired:
            subagent = self._subagents.pop(name)
            self._stats["destroyed"] += 1
            if self.debug:
                print(
                    f"[AgentFactory] Cleaned up expired subagent {subagent.id} "
                    f"(unused for {now - subagent.last_used:.1f}s)"
                )

        return len(expired)

    def cleanup_all(self) -> int:
        """
        Remove all subagents from cache.

        Returns:
            Number of subagents removed
        """
        count = len(self._subagents)
        if self.debug and count > 0:
            print(f"[AgentFactory] Cleaning up all {count} subagents")
        self._subagents.clear()
        self._stats["destroyed"] += count
        return count

    def get_stats(self) -> dict[str, Any]:
        """Get factory statistics"""
        import time

        now = time.time()
        active_subagents = {
            name: {
                "id": s.id,
                "age": now - s.created_at,
                "last_used": now - s.last_used,
                "use_count": s.use_count,
            }
            for name, s in self._subagents.items()
        }

        return {
            **self._stats,
            "active_count": len(self._subagents),
            "cached_configs": len(self._agent_configs),
            "active_subagents": active_subagents,
            "dynamic_mode": self.dynamic_mode,
            "cache_ttl": self.cache_ttl,
        }

    def get_system_prompt(self, agent_name: str) -> str:
        """
        Get the system prompt for an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            System prompt string
        """
        config = self.get_agent_config(agent_name)
        return config.system_prompt

    def get_agent_meta(self, agent_name: str) -> dict[str, str]:
        """
        Get metadata for an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Dictionary with name, role, description, icon
        """
        if agent_name not in self.AGENT_META:
            raise ValueError(f"Unknown agent: {agent_name}")
        return self.AGENT_META[agent_name]

    def list_agents(self) -> list[str]:
        """List all available agent names"""
        return list(self.AGENT_FILES.keys())


# Singleton instance for global access
_factory_instance: AgentFactory | None = None


def get_agent_factory(
    agents_dir: Path | str | None = None,
    cache_ttl: int | None = None,
) -> AgentFactory:
    """
    Get or create the global AgentFactory instance.

    This function provides a singleton pattern for the AgentFactory,
    ensuring that subagent caching works across the application.

    Args:
        agents_dir: Directory containing agent YAML files
        cache_ttl: Cache TTL in seconds

    Returns:
        AgentFactory instance
    """
    global _factory_instance

    if _factory_instance is None:
        _factory_instance = AgentFactory(agents_dir=agents_dir, cache_ttl=cache_ttl)

    return _factory_instance


def reset_agent_factory() -> None:
    """Reset the global factory instance (useful for testing)"""
    global _factory_instance
    if _factory_instance is not None:
        _factory_instance.cleanup_all()
    _factory_instance = None
