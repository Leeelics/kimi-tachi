"""
Kimi-Tachi Configuration

Centralized configuration management with environment variable support.

Author: kimi-tachi Team
Version: 0.3.0
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

from .compatibility import check_compatibility, get_recommended_agent_mode


@dataclass
class KimiTachiConfig:
    """
    Kimi-tachi configuration.
    
    Configuration priority (highest to lowest):
    1. Constructor arguments
    2. Environment variables
    3. Auto-detection (CLI version)
    4. Default values
    
    Example:
        >>> # From environment
        >>> config = KimiTachiConfig.from_env()
        >>> 
        >>> # Manual configuration
        >>> config = KimiTachiConfig(agent_mode="native", debug_agents=True)
    """
    
    # Execution mode
    agent_mode: Literal["native", "legacy", "auto"] = "auto"
    """
    Agent execution mode:
    - "native": Use native Agent tool (requires kimi-cli 1.25.0+)
    - "auto": Auto-detect based on CLI version (default)
    
    Note: "legacy" mode (CreateSubagent + Task) was removed in v0.3.0
    as kimi-cli 1.25.0+ no longer supports those tools.
    """
    
    # Feature flags
    enable_personality: bool = True
    """Enable anime character personalities in responses"""
    
    enable_parallel: bool = True
    """Enable parallel task execution where possible"""
    
    enable_cache: bool = True
    """Enable context caching (Phase 2.4)"""
    
    enable_message_bus: bool = True
    """Enable message bus architecture (Phase 2.2)"""
    
    # Agent-specific settings
    subagent_cache_ttl: int = 300
    """Subagent cache TTL in seconds"""
    
    max_parallel_tasks: int = 4
    """Maximum number of parallel tasks"""
    
    default_timeout: int = 300
    """Default task timeout in seconds"""
    
    # Debug options
    debug_agents: bool = False
    """Enable agent debug logging"""
    
    show_agent_events: bool = False
    """Show Agent tool events in output"""
    
    trace_workflow: bool = False
    """Enable workflow tracing for vis"""
    
    # Internal
    _effective_mode: str = field(default="", repr=False)
    """Effective agent mode after auto-detection (cached)"""
    
    def __post_init__(self):
        """Resolve auto mode after initialization"""
        if self.agent_mode == "auto":
            self._effective_mode = get_recommended_agent_mode()
        else:
            self._effective_mode = self.agent_mode
    
    @property
    def effective_agent_mode(self) -> str:
        """Get effective agent mode (resolved from auto if needed)"""
        if not self._effective_mode:
            self._effective_mode = get_recommended_agent_mode()
        return self._effective_mode
    
    @property
    def use_native_agents(self) -> bool:
        """Check if native Agent tool should be used"""
        return self.effective_agent_mode == "native"
    
    @property
    def use_legacy_agents(self) -> bool:
        """Check if legacy CreateSubagent should be used (deprecated, always returns False)"""
        return False  # Legacy mode removed in v0.3.0
    
    @classmethod
    def from_env(cls) -> "KimiTachiConfig":
        """
        Create configuration from environment variables.
        
        Environment Variables:
            KIMI_TACHI_AGENT_MODE: "native", "legacy", or "auto"
            KIMI_TACHI_ENABLE_PERSONALITY: "true" or "false"
            KIMI_TACHI_ENABLE_PARALLEL: "true" or "false"
            KIMI_TACHI_ENABLE_CACHE: "true" or "false"
            KIMI_TACHI_ENABLE_MESSAGE_BUS: "true" or "false"
            KIMI_TACHI_SUBAGENT_CACHE_TTL: seconds (default: 300)
            KIMI_TACHI_MAX_PARALLEL_TASKS: number (default: 4)
            KIMI_TACHI_DEFAULT_TIMEOUT: seconds (default: 300)
            KIMI_TACHI_DEBUG_AGENTS: "true" or "false"
            KIMI_TACHI_SHOW_AGENT_EVENTS: "true" or "false"
            KIMI_TACHI_TRACE_WORKFLOW: "true" or "false"
        """
        def get_bool(key: str, default: bool) -> bool:
            value = os.getenv(key, "").lower()
            if value in ("1", "true", "yes", "on"):
                return True
            if value in ("0", "false", "no", "off"):
                return False
            return default
        
        def get_int(key: str, default: int) -> int:
            try:
                return int(os.getenv(key, str(default)))
            except ValueError:
                return default
        
        agent_mode = os.getenv("KIMI_TACHI_AGENT_MODE", "auto")
        if agent_mode not in ("native", "legacy", "auto"):
            agent_mode = "auto"
        
        return cls(
            agent_mode=agent_mode,  # type: ignore
            enable_personality=get_bool("KIMI_TACHI_ENABLE_PERSONALITY", True),
            enable_parallel=get_bool("KIMI_TACHI_ENABLE_PARALLEL", True),
            enable_cache=get_bool("KIMI_TACHI_ENABLE_CACHE", True),
            enable_message_bus=get_bool("KIMI_TACHI_ENABLE_MESSAGE_BUS", True),
            subagent_cache_ttl=get_int("KIMI_TACHI_SUBAGENT_CACHE_TTL", 300),
            max_parallel_tasks=get_int("KIMI_TACHI_MAX_PARALLEL_TASKS", 4),
            default_timeout=get_int("KIMI_TACHI_DEFAULT_TIMEOUT", 300),
            debug_agents=get_bool("KIMI_TACHI_DEBUG_AGENTS", False),
            show_agent_events=get_bool("KIMI_TACHI_SHOW_AGENT_EVENTS", False),
            trace_workflow=get_bool("KIMI_TACHI_TRACE_WORKFLOW", False),
        )
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary"""
        return {
            "agent_mode": self.agent_mode,
            "effective_agent_mode": self.effective_agent_mode,
            "enable_personality": self.enable_personality,
            "enable_parallel": self.enable_parallel,
            "enable_cache": self.enable_cache,
            "enable_message_bus": self.enable_message_bus,
            "subagent_cache_ttl": self.subagent_cache_ttl,
            "max_parallel_tasks": self.max_parallel_tasks,
            "default_timeout": self.default_timeout,
            "debug_agents": self.debug_agents,
            "show_agent_events": self.show_agent_events,
            "trace_workflow": self.trace_workflow,
        }
    
    def print_status(self):
        """Print configuration status"""
        print("=" * 50)
        print("Kimi-Tachi Configuration")
        print("=" * 50)
        
        for key, value in self.to_dict().items():
            print(f"  {key}: {value}")
        
        print("=" * 50)


# Global configuration instance
_config: KimiTachiConfig | None = None


def get_config() -> KimiTachiConfig:
    """
    Get global configuration instance.
    
    Creates the instance on first call using environment variables.
    """
    global _config
    if _config is None:
        _config = KimiTachiConfig.from_env()
    return _config


def set_config(config: KimiTachiConfig) -> None:
    """Set global configuration instance"""
    global _config
    _config = config


def reset_config() -> None:
    """Reset global configuration (useful for testing)"""
    global _config
    _config = None


if __name__ == "__main__":
    config = KimiTachiConfig.from_env()
    config.print_status()
