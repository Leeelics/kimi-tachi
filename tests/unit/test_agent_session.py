"""Tests for AgentSessionManager"""

import time

import pytest

from kimi_tachi.session import AgentSessionManager, get_session_manager, reset_session_manager


class TestAgentSessionManager:
    """Test AgentSessionManager functionality"""

    def setup_method(self):
        """Reset session manager before each test"""
        reset_session_manager()

    def test_register_agent(self):
        """Test registering a new agent"""
        manager = AgentSessionManager("test-session")

        agent = manager.register_agent(
            agent_id="a1b2c3d4",
            agent_type="nekobasu",
            description="Explore auth code",
        )

        assert agent.agent_id == "a1b2c3d4"
        assert agent.agent_type == "nekobasu"
        assert agent.interaction_count == 1
        assert agent.is_active is True

    def test_get_agent(self):
        """Test retrieving an agent by ID"""
        manager = AgentSessionManager()
        manager.register_agent("a1b2c3d4", "nekobasu", "Explore auth")

        retrieved = manager.get_agent("a1b2c3d4")
        assert retrieved is not None
        assert retrieved.agent_type == "nekobasu"

        # Non-existent agent
        assert manager.get_agent("nonexistent") is None

    def test_get_latest_agent_of_type(self):
        """Test getting the latest agent of a specific type"""
        manager = AgentSessionManager()

        # Register multiple agents of same type
        manager.register_agent("a1b2c3d4", "nekobasu", "First")
        time.sleep(0.01)  # Ensure different timestamps
        manager.register_agent("e5f6g7h8", "nekobasu", "Second")

        latest = manager.get_latest_agent_of_type("nekobasu")
        assert latest.agent_id == "e5f6g7h8"
        assert latest.description == "Second"

    def test_record_interaction(self):
        """Test recording agent interactions"""
        manager = AgentSessionManager()
        manager.register_agent("a1b2c3d4", "calcifer", "Implement feature")

        # Record additional interaction
        success = manager.record_interaction("a1b2c3d4", "Fix bug")
        assert success is True

        agent = manager.get_agent("a1b2c3d4")
        assert agent.interaction_count == 2
        assert "Fix bug" in agent.task_history

        # Non-existent agent
        assert manager.record_interaction("nonexistent", "Task") is False

    def test_should_resume(self):
        """Test resume decision logic"""
        manager = AgentSessionManager()

        # No agents yet
        assert manager.should_resume("nekobasu") is None

        # Register agent
        manager.register_agent("a1b2c3d4", "nekobasu", "Explore")

        # Should suggest resume
        agent_id = manager.should_resume("nekobasu")
        assert agent_id == "a1b2c3d4"

        # Deactivate and check
        manager.deactivate_agent("a1b2c3d4")
        assert manager.should_resume("nekobasu") is None

    def test_should_resume_age_check(self):
        """Test that old agents are not suggested for resume"""
        manager = AgentSessionManager()

        # Register agent with very short max age
        manager.register_agent("a1b2c3d4", "nekobasu", "Explore")
        time.sleep(0.1)

        # Should not suggest resume if max_age is very short
        assert manager.should_resume("nekobasu", max_age_seconds=0.05) is None

        # Should suggest resume with longer max age
        assert manager.should_resume("nekobasu", max_age_seconds=10) == "a1b2c3d4"

    def test_list_active_agents(self):
        """Test listing active agents"""
        manager = AgentSessionManager()

        # Register and deactivate one
        manager.register_agent("a1b2c3d4", "nekobasu", "Explore")
        manager.deactivate_agent("a1b2c3d4")

        # Register active one
        manager.register_agent("e5f6g7h8", "calcifer", "Implement")

        active = manager.list_active_agents()
        assert len(active) == 1
        assert active[0].agent_id == "e5f6g7h8"

    def test_get_stats(self):
        """Test statistics collection"""
        manager = AgentSessionManager("stats-test")

        manager.register_agent("a1b2c3d4", "nekobasu", "Explore")
        manager.register_agent("e5f6g7h8", "calcifer", "Implement")
        manager.deactivate_agent("a1b2c3d4")

        stats = manager.get_stats()
        assert stats["total_agents"] == 2
        assert stats["active_agents"] == 1
        assert stats["by_type"]["nekobasu"] == 1
        assert stats["by_type"]["calcifer"] == 1
        assert stats["session_id"] == "stats-test"

    def test_clear_inactive(self):
        """Test clearing old/inactive agents"""
        manager = AgentSessionManager()

        # Register and immediately deactivate
        manager.register_agent("old1", "nekobasu", "Old task")
        manager.deactivate_agent("old1")

        # Register active
        manager.register_agent("active", "calcifer", "Active task")

        # Clear inactive (with very short max age to clear all)
        removed = manager.clear_inactive(max_age_seconds=0)

        assert removed == 2  # Both should be removed (one inactive, one old)
        assert len(manager._agents) == 0


class TestGlobalSessionManager:
    """Test global session manager functions"""

    def setup_method(self):
        reset_session_manager()

    def test_get_session_manager_singleton(self):
        """Test that get_session_manager returns singleton"""
        manager1 = get_session_manager()
        manager2 = get_session_manager()

        assert manager1 is manager2

    def test_get_session_manager_with_session_id(self):
        """Test session manager with specific session ID"""
        manager1 = get_session_manager("session-1")
        assert manager1.session_id == "session-1"

        # Same session ID returns same manager
        manager2 = get_session_manager("session-1")
        assert manager1 is manager2

        # Different session ID creates new manager
        manager3 = get_session_manager("session-2")
        assert manager3 is not manager1
        assert manager3.session_id == "session-2"

    def test_reset_session_manager(self):
        """Test resetting the global session manager"""
        manager1 = get_session_manager("test")
        reset_session_manager()
        manager2 = get_session_manager()

        assert manager1 is not manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
