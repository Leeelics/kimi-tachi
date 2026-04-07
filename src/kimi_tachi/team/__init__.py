"""
Team Management for Kimi-Tachi

Provides multi-team support with isolated contexts, sessions, and memory.
"""

from .exceptions import AgentNotFoundError, TeamConfigError, TeamNotFoundError
from .manager import ResolvedAgent, Team, TeamManager

__all__ = [
    "TeamManager",
    "Team",
    "ResolvedAgent",
    "TeamNotFoundError",
    "AgentNotFoundError",
    "TeamConfigError",
]
