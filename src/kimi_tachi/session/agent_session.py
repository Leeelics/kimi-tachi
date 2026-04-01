"""
Agent Session Manager

Tracks agent instances and enables resume functionality for the Agent tool.
This allows context preservation across multiple interactions with the same worker.

Example:
    # First interaction
    result = session.create_agent("nekobasu", "Find auth files")
    agent_id = result.agent_id  # e.g., "a1b2c3d4"

    # Later interaction - resume with context preserved
    result = session.resume_agent("a1b2c3d4", "Analyze those auth files")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class AgentInstance:
    """Record of an agent instance"""

    agent_id: str
    agent_type: str  # nekobasu, calcifer, etc.
    description: str
    created_at: float
    last_used_at: float
    interaction_count: int = 0
    task_history: list[str] = field(default_factory=list)
    is_active: bool = True


class AgentSessionManager:
    """
    Manages agent instances for resume functionality.

    This class tracks agent instances created via the Agent tool,
    allowing them to be resumed later with preserved context.
    """

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id
        self._agents: dict[str, AgentInstance] = {}
        self._type_to_agent: dict[str, str] = {}  # agent_type -> latest agent_id

    def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        description: str,
    ) -> AgentInstance:
        """
        Register a new agent instance.

        Args:
            agent_id: The agent ID returned by the Agent tool
            agent_type: The subagent_type used (nekobasu, calcifer, etc.)
            description: Description of the agent's purpose

        Returns:
            The created AgentInstance
        """
        now = time.time()
        instance = AgentInstance(
            agent_id=agent_id,
            agent_type=agent_type,
            description=description,
            created_at=now,
            last_used_at=now,
            interaction_count=1,
        )
        self._agents[agent_id] = instance
        self._type_to_agent[agent_type] = agent_id
        return instance

    def get_agent(self, agent_id: str) -> AgentInstance | None:
        """Get an agent instance by ID"""
        return self._agents.get(agent_id)

    def get_latest_agent_of_type(self, agent_type: str) -> AgentInstance | None:
        """Get the most recently created agent of a specific type"""
        agent_id = self._type_to_agent.get(agent_type)
        if agent_id:
            return self._agents.get(agent_id)
        return None

    def record_interaction(self, agent_id: str, task: str) -> bool:
        """
        Record an interaction with an agent.

        Args:
            agent_id: The agent ID
            task: Description of the task performed

        Returns:
            True if the agent was found and updated
        """
        agent = self._agents.get(agent_id)
        if agent:
            agent.interaction_count += 1
            agent.last_used_at = time.time()
            agent.task_history.append(task)
            return True
        return False

    def should_resume(self, agent_type: str, max_age_seconds: float = 1800) -> str | None:
        """
        Determine if we should resume an existing agent of this type.

        Args:
            agent_type: The type of agent (nekobasu, calcifer, etc.)
            max_age_seconds: Maximum age of agent to consider for resume (default 30 min)

        Returns:
            agent_id if should resume, None otherwise
        """
        agent = self.get_latest_agent_of_type(agent_type)
        if not agent:
            return None

        # Check if agent is still active and not too old
        age = time.time() - agent.last_used_at
        if not agent.is_active or age > max_age_seconds:
            return None

        # Resume if there have been previous interactions (context to preserve)
        if agent.interaction_count >= 1:
            return agent.agent_id

        return None

    def deactivate_agent(self, agent_id: str) -> bool:
        """Mark an agent as inactive (e.g., if it failed or was killed)"""
        agent = self._agents.get(agent_id)
        if agent:
            agent.is_active = False
            return True
        return False

    def list_active_agents(self) -> list[AgentInstance]:
        """List all currently active agents"""
        return [a for a in self._agents.values() if a.is_active]

    def get_stats(self) -> dict:
        """Get session statistics"""
        total = len(self._agents)
        active = len(self.list_active_agents())
        by_type: dict[str, int] = {}
        for agent in self._agents.values():
            by_type[agent.agent_type] = by_type.get(agent.agent_type, 0) + 1

        return {
            "total_agents": total,
            "active_agents": active,
            "by_type": by_type,
            "session_id": self.session_id,
        }

    def clear_inactive(self, max_age_seconds: float = 3600) -> int:
        """
        Remove inactive agents older than max_age_seconds.

        Returns:
            Number of agents removed
        """
        now = time.time()
        to_remove = [
            aid
            for aid, agent in self._agents.items()
            if not agent.is_active or (now - agent.last_used_at) > max_age_seconds
        ]
        for aid in to_remove:
            del self._agents[aid]
            # Clean up type mapping if this was the latest
            for atype, latest_id in list(self._type_to_agent.items()):
                if latest_id == aid:
                    del self._type_to_agent[atype]
        return len(to_remove)


# Global session manager instance
_session_manager: AgentSessionManager | None = None


def get_session_manager(session_id: str | None = None) -> AgentSessionManager:
    """Get or create the global session manager"""
    global _session_manager
    if _session_manager is None or (_session_manager.session_id != session_id and session_id is not None):
        _session_manager = AgentSessionManager(session_id)
    return _session_manager


def reset_session_manager():
    """Reset the global session manager (useful for testing)"""
    global _session_manager
    _session_manager = None
