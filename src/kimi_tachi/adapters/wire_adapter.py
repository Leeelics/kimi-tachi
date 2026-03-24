"""
Wire Adapter for Message Bus Integration

This adapter bridges kimi-tachi's Message Bus with kimi-cli's Wire system,
enabling seamless communication between:
1. Agents running via the Agent tool (cross-process)
2. Local components using Message Bus (same-process)

Architecture:
```
Message Bus (kimi-tachi)
    ↓
WireAdapter (this module)
    ↓
Agent Tool / Wire / SubagentStore (kimi-cli)
```

v0.4.0: Initial implementation
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from ..message_bus import Message, MessageBus


@dataclass
class AgentInfo:
    """Information about an agent from kimi-cli's perspective"""

    agent_id: str
    agent_type: str
    status: str  # idle, running_foreground, running_background, completed, failed
    description: str
    context_path: Optional[str] = None
    wire_path: Optional[str] = None


class WireAdapter:
    """
    Adapter between Message Bus and kimi-cli's Wire system.

    This adapter provides a unified interface for:
    - Sending messages to agents (via Agent tool or direct call)
    - Receiving messages from agents (via Wire or callback)
    - Querying agent status (via SubagentStore)
    - Managing agent lifecycle (create, resume, terminate)

    Example:
        >>> adapter = WireAdapter()
        >>> 
        >>> # Send message to an agent
        >>> await adapter.send_to_agent(
        ...     agent_id="a1b2c3d4",
        ...     message={"type": "task", "content": "Analyze auth.py"}
        ... )
        >>> 
        >>> # Query agent status
        >>> info = await adapter.get_agent_info("a1b2c3d4")
        >>> print(info.status)  # "running_foreground"
        >>> 
        >>> # Resume an agent
        >>> result = await adapter.resume_agent(
        ...     agent_id="a1b2c3d4",
        ...     prompt="Continue analysis"
        ... )
    """

    def __init__(self):
        self._message_callbacks: dict[str, list[Callable[[dict], None]]] = {}
        self._agent_status_cache: dict[str, AgentInfo] = {}
        self._local_mode: bool = True  # True if running inside kimi-cli process

    async def send_to_agent(
        self,
        agent_id: str,
        message: dict[str, Any],
        wait_for_response: bool = False,
        timeout: float = 30.0,
    ) -> Optional[dict]:
        """
        Send a message to an agent.

        In local mode (same process): uses direct function call
        In remote mode (cross process): uses Agent tool with resume

        Args:
            agent_id: Target agent ID
            message: Message payload
            wait_for_response: Whether to wait for response
            timeout: Timeout for waiting

        Returns:
            Response dict if wait_for_response=True, None otherwise
        """
        if self._local_mode:
            # Local mode: direct callback or queue
            return await self._send_local(agent_id, message, wait_for_response, timeout)
        else:
            # Remote mode: use Agent tool
            return await self._send_remote(agent_id, message, wait_for_response, timeout)

    async def _send_local(
        self,
        agent_id: str,
        message: dict[str, Any],
        wait_for_response: bool,
        timeout: float,
    ) -> Optional[dict]:
        """Send message in local mode (direct)"""
        # In local mode, we can directly invoke callbacks
        callbacks = self._message_callbacks.get(agent_id, [])
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                print(f"Callback error for agent {agent_id}: {e}")

        if wait_for_response:
            # In local mode, response is immediate
            return {"status": "delivered", "agent_id": agent_id}
        return None

    async def _send_remote(
        self,
        agent_id: str,
        message: dict[str, Any],
        wait_for_response: bool,
        timeout: float,
    ) -> Optional[dict]:
        """Send message in remote mode (via Agent tool)"""
        # This would use the Agent tool with resume
        # For now, return a placeholder
        return {
            "status": "sent_via_agent_tool",
            "agent_id": agent_id,
            "note": "Remote mode not yet fully implemented",
        }

    async def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """
        Get information about an agent from SubagentStore.

        Args:
            agent_id: Agent ID to query

        Returns:
            AgentInfo if found, None otherwise
        """
        # Check cache first
        if agent_id in self._agent_status_cache:
            return self._agent_status_cache[agent_id]

        # Try to get from kimi-cli's SubagentStore
        # This requires access to the runtime, which may not be available
        # in all contexts
        try:
            info = await self._query_subagent_store(agent_id)
            if info:
                self._agent_status_cache[agent_id] = info
            return info
        except Exception:
            return None

    async def _query_subagent_store(self, agent_id: str) -> Optional[AgentInfo]:
        """Query kimi-cli's SubagentStore for agent info"""
        # This is a placeholder - actual implementation would need
        # access to the Runtime's subagent_store
        # 
        # Example (when running inside kimi-cli):
        # from kimi_cli.subagents.store import SubagentStore
        # store = SubagentStore(session)
        # record = store.get_instance(agent_id)
        # return AgentInfo(...)
        
        return None

    async def resume_agent(
        self,
        agent_id: str,
        prompt: str,
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Resume an existing agent with a new prompt.

        This uses the Agent tool with the resume parameter.

        Args:
            agent_id: Agent to resume
            prompt: New prompt to send
            description: Optional description override

        Returns:
            Result from the Agent tool
        """
        # This would construct an Agent tool call with resume
        # For now, return instructions
        return {
            "action": "use_agent_tool",
            "params": {
                "resume": agent_id,
                "prompt": prompt,
                "description": description or f"Resume agent {agent_id}",
            },
            "note": "Actual Agent tool call should be made by the LLM",
        }

    def register_message_handler(
        self,
        agent_id: str,
        handler: Callable[[dict], Any],
    ):
        """
        Register a handler to receive messages for an agent.

        Args:
            agent_id: Agent ID to handle messages for
            handler: Callback function for incoming messages
        """
        if agent_id not in self._message_callbacks:
            self._message_callbacks[agent_id] = []
        self._message_callbacks[agent_id].append(handler)

    def unregister_message_handler(
        self,
        agent_id: str,
        handler: Callable[[dict], Any],
    ):
        """Unregister a message handler"""
        if agent_id in self._message_callbacks:
            self._message_callbacks[agent_id] = [
                h for h in self._message_callbacks[agent_id] if h != handler
            ]

    async def broadcast_to_agents(
        self,
        message: dict[str, Any],
        agent_type: Optional[str] = None,
    ) -> list[dict]:
        """
        Broadcast a message to multiple agents.

        Args:
            message: Message to broadcast
            agent_type: Optional filter by agent type

        Returns:
            List of delivery results
        """
        # Get list of target agents
        # In real implementation, this would query SubagentStore
        target_agents = []  # Placeholder

        results = []
        for agent_id in target_agents:
            result = await self.send_to_agent(agent_id, message, wait_for_response=False)
            results.append({"agent_id": agent_id, "result": result})

        return results

    def set_local_mode(self, local: bool):
        """Set whether running in local (same-process) mode"""
        self._local_mode = local

    def clear_cache(self):
        """Clear the agent status cache"""
        self._agent_status_cache.clear()


# Global adapter instance
_wire_adapter: Optional[WireAdapter] = None


def get_wire_adapter() -> WireAdapter:
    """Get or create the global WireAdapter instance"""
    global _wire_adapter
    if _wire_adapter is None:
        _wire_adapter = WireAdapter()
    return _wire_adapter


def reset_wire_adapter():
    """Reset the global WireAdapter (useful for testing)"""
    global _wire_adapter
    _wire_adapter = None
