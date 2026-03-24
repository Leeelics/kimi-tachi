"""
Kimi-Tachi Session Management

Manages agent instances across interactions, enabling context preservation
through the Agent tool's resume functionality.

v0.4.0: Added Agent Resume support for kimi-cli 1.25.0+
"""

from .agent_session import AgentSessionManager, get_session_manager, reset_session_manager

__all__ = ["AgentSessionManager", "get_session_manager", "reset_session_manager"]
