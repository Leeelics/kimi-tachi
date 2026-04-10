"""
Tests for native agent orchestrator.

Author: kimi-tachi Team
"""

from unittest.mock import patch

import pytest

from kimi_tachi.orchestrator.native_agent_orchestrator import (
    AGENT_PERSONALITIES,
    PERSONALITY_TO_TYPE,
    AgentPersonality,
    AgentType,
    NativeAgentOrchestrator,
    get_personality_by_name,
    get_personality_by_role,
)


class TestAgentType:
    """Test AgentType enum."""

    def test_agent_type_values(self):
        assert str(AgentType.CODER) == "coder"
        assert str(AgentType.EXPLORE) == "explore"
        assert str(AgentType.PLAN) == "plan"


class TestAgentPersonality:
    """Test AgentPersonality enum."""

    def test_personality_values(self):
        assert str(AgentPersonality.NEKOBASU) == "nekobasu"
        assert str(AgentPersonality.CALCIFER) == "calcifer"
        assert str(AgentPersonality.TASOGARE) == "tasogare"
        assert str(AgentPersonality.SHISHIGAMI) == "shishigami"
        assert str(AgentPersonality.ENMA) == "enma"
        assert str(AgentPersonality.PHOENIX) == "phoenix"


class TestPersonalityToType:
    """Test personality to native type mapping."""

    def test_mapping(self):
        assert PERSONALITY_TO_TYPE[AgentPersonality.NEKOBASU] == AgentType.EXPLORE
        assert PERSONALITY_TO_TYPE[AgentPersonality.CALCIFER] == AgentType.CODER
        assert PERSONALITY_TO_TYPE[AgentPersonality.TASOGARE] == AgentType.PLAN
        assert PERSONALITY_TO_TYPE[AgentPersonality.SHISHIGAMI] == AgentType.PLAN
        assert PERSONALITY_TO_TYPE[AgentPersonality.ENMA] == AgentType.CODER
        assert PERSONALITY_TO_TYPE[AgentPersonality.PHOENIX] == AgentType.EXPLORE


class TestAgentPersonalities:
    """Test agent personalities configuration."""

    def test_all_personalities_have_config(self):
        for personality in AgentPersonality:
            assert personality in AGENT_PERSONALITIES
            config = AGENT_PERSONALITIES[personality]
            assert "icon" in config
            assert "name" in config
            assert "role" in config
            assert "system_prompt" in config


class TestGetPersonalityByRole:
    """Test get_personality_by_role function."""

    def test_valid_roles(self):
        assert get_personality_by_role("explorer") == AgentPersonality.NEKOBASU
        assert get_personality_by_role("builder") == AgentPersonality.CALCIFER
        assert get_personality_by_role("planner") == AgentPersonality.TASOGARE
        assert get_personality_by_role("architect") == AgentPersonality.SHISHIGAMI
        assert get_personality_by_role("reviewer") == AgentPersonality.ENMA
        assert get_personality_by_role("librarian") == AgentPersonality.PHOENIX

    def test_invalid_role(self):
        assert get_personality_by_role("invalid") is None

    def test_case_insensitive(self):
        assert get_personality_by_role("EXPLORER") == AgentPersonality.NEKOBASU
        assert get_personality_by_role("Builder") == AgentPersonality.CALCIFER


class TestGetPersonalityByName:
    """Test get_personality_by_name function."""

    def test_exact_match(self):
        assert get_personality_by_name("nekobasu") == AgentPersonality.NEKOBASU
        assert get_personality_by_name("calcifer") == AgentPersonality.CALCIFER

    def test_partial_match(self):
        assert get_personality_by_name("neko") == AgentPersonality.NEKOBASU
        assert get_personality_by_name("calc") == AgentPersonality.CALCIFER

    def test_invalid_name(self):
        assert get_personality_by_name("invalid") is None


class TestNativeAgentOrchestrator:
    """Test NativeAgentOrchestrator class."""

    def test_init_default(self):
        orch = NativeAgentOrchestrator()
        assert orch.cache_ttl == 300
        assert orch.debug is False
        assert len(orch._agents) == 0

    def test_init_with_params(self):
        orch = NativeAgentOrchestrator(cache_ttl=600, debug=True)
        assert orch.cache_ttl == 600
        assert orch.debug is True

    def test_init_from_env(self):
        with patch.dict(
            "os.environ",
            {
                "KIMI_TACHI_SUBAGENT_CACHE_TTL": "1200",
                "KIMI_TACHI_DEBUG_AGENTS": "true",
            },
        ):
            orch = NativeAgentOrchestrator()
            assert orch.cache_ttl == 1200
            assert orch.debug is True

    def test_get_agent_info(self):
        orch = NativeAgentOrchestrator()
        info = orch.get_agent_info(AgentPersonality.NEKOBASU)

        assert info["personality"] == "nekobasu"
        assert info["icon"] == "🚌"
        assert info["name"] == "猫バス"
        assert info["role"] == "explorer"
        assert info["native_type"] == "explore"
        assert info["cached"] is False

    def test_list_personalities(self):
        orch = NativeAgentOrchestrator()
        personalities = orch.list_personalities()

        # Coding team has 6 subagent personalities
        assert len(personalities) == 6

        # Check nekobasu entry
        neko = next(p for p in personalities if p["personality"] == "nekobasu")
        assert neko["icon"] == "🚌"
        assert neko["role"] == "explorer"
        assert neko["native_type"] == "explore"

    def test_get_stats_empty(self):
        orch = NativeAgentOrchestrator()
        stats = orch.get_stats()

        assert stats["created"] == 0
        assert stats["reused"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["active_agents"] == 0
        assert stats["cache_ttl"] == 300

    def test_cleanup_empty(self):
        orch = NativeAgentOrchestrator()
        count = orch.cleanup()
        assert count == 0


class TestNativeAgentOrchestratorAsync:
    """Test async methods of NativeAgentOrchestrator."""

    @pytest.mark.asyncio
    async def test_delegate(self):
        orch = NativeAgentOrchestrator()
        result = await orch.delegate(
            personality=AgentPersonality.NEKOBASU,
            task="Find all Python files",
        )

        assert result.agent == "nekobasu"
        assert result.personality == AgentPersonality.NEKOBASU
        assert result.task == "Find all Python files"
        assert result.returncode == 0
        assert "## Your Role" in result.stdout
        assert "Find all Python files" in result.stdout

    @pytest.mark.asyncio
    async def test_delegate_creates_cache(self):
        orch = NativeAgentOrchestrator()

        # First delegation should create agent
        await orch.delegate(
            personality=AgentPersonality.CALCIFER,
            task="Task 1",
        )

        stats = orch.get_stats()
        assert stats["created"] == 1
        assert stats["cache_misses"] == 1

        # Second delegation should reuse
        await orch.delegate(
            personality=AgentPersonality.CALCIFER,
            task="Task 2",
        )

        stats = orch.get_stats()
        assert stats["reused"] == 1
        assert stats["cache_hits"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
