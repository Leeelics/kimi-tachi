"""
Tests for kimi_tachi.memory module

Note: These tests may be skipped if memnexus is not installed.
"""

from unittest.mock import AsyncMock, Mock

import pytest

# Check if memory module is available
try:
    from kimi_tachi.memory import AGENT_PROFILES, TachiMemory
    from kimi_tachi.memory.agent_profiles import MemoryProfile

    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False


# Only apply asyncio mark to async tests
pytestmark = pytest.mark.skipif(not MEMORY_AVAILABLE, reason="memnexus not installed")


class TestAgentProfiles:
    """Test agent profile configurations."""

    def test_agent_profiles_exist(self):
        """Test that all Seven Samurai have memory profiles."""
        expected_agents = [
            "kamaji",
            "shishigami",
            "nekobasu",
            "calcifer",
            "enma",
            "tasogare",
            "phoenix",
        ]
        for agent in expected_agents:
            assert agent in AGENT_PROFILES, f"Missing profile for {agent}"

    def test_default_profile_exists(self):
        """Test that default profile exists."""
        assert "default" in AGENT_PROFILES

    def test_profile_structure(self):
        """Test that profiles are MemoryProfile instances."""
        for agent, profile in AGENT_PROFILES.items():
            assert isinstance(profile, MemoryProfile), f"{agent} is not MemoryProfile"
            # Check key attributes exist
            assert hasattr(profile, "remember_categories")
            assert hasattr(profile, "recall_on_start")
            assert hasattr(profile, "store_on_end")


class TestTachiMemory:
    """Test TachiMemory class."""

    def test_memory_without_init(self, tmp_path):
        """Test creating memory without init."""
        test_path = tmp_path / "test_project"
        memory = TachiMemory(str(test_path))
        # Use same resolution logic as TachiMemory
        assert memory.project_path == test_path.resolve()

    @pytest.mark.asyncio
    async def test_search_with_mock_store(self, tmp_path):
        """Test search with mocked store."""
        # Create a mock store
        mock_store = Mock()
        mock_result = Mock()
        mock_result.id = "1"
        mock_result.content = "test content"
        mock_result.memory_type = Mock(value="code")
        mock_result.source = "test.py"
        mock_result.score = 0.9

        mock_store.search = AsyncMock(return_value=[mock_result])

        # Create memory and inject mock
        memory = TachiMemory(str(tmp_path))
        memory.memory = Mock()
        memory.memory.store = mock_store

        results = await memory.search("test", limit=5)

        assert len(results) == 1
        assert results[0]["content"] == "test content"

    @pytest.mark.asyncio
    async def test_recall_agent_context_structure(self, tmp_path):
        """Test recall_agent_context returns correct structure."""
        memory = TachiMemory(str(tmp_path))
        memory.memory = None  # No store, should still work
        memory.global_memory = None

        context = await memory.recall_agent_context("kamaji", task="test task")

        assert "agent_type" in context
        assert context["agent_type"] == "kamaji"
        assert "task" in context
        assert context["task"] == "test task"
        assert "recent_context" in context
        assert "global_knowledge" in context
        assert "previous_decisions" in context

    @pytest.mark.asyncio
    async def test_store_agent_output_without_store(self, tmp_path):
        """Test store_agent_output handles missing store gracefully."""
        memory = TachiMemory(str(tmp_path))
        memory.memory = None  # No store

        result = await memory.store_agent_output(
            agent="kamaji", output="test output", task="test task"
        )

        # Should return None when no store available
        assert result is None
