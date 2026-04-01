"""
Tests for config module.

Author: kimi-tachi Team
"""

import os
from unittest.mock import patch

import pytest

from kimi_tachi.config import KimiTachiConfig, get_config, reset_config, set_config


class TestKimiTachiConfig:
    """Test KimiTachiConfig dataclass."""

    def test_default_values(self):
        config = KimiTachiConfig()
        assert config.agent_mode == "auto"
        assert config.enable_personality is True
        assert config.enable_parallel is True
        assert config.enable_cache is True
        assert config.subagent_cache_ttl == 300

    def test_custom_values(self):
        config = KimiTachiConfig(
            agent_mode="native",
            enable_personality=False,
            debug_agents=True,
        )
        assert config.agent_mode == "native"
        assert config.enable_personality is False
        assert config.debug_agents is True

    def test_effective_mode_native(self):
        with patch("kimi_tachi.config.get_recommended_agent_mode", return_value="native"):
            config = KimiTachiConfig(agent_mode="auto")
            assert config.effective_agent_mode == "native"
            assert config.use_native_agents is True
            assert config.use_legacy_agents is False

    def test_legacy_mode_returns_false(self):
        """Legacy mode is deprecated and always returns False"""
        with patch("kimi_tachi.config.get_recommended_agent_mode", return_value="native"):
            config = KimiTachiConfig(agent_mode="auto")
            # use_legacy_agents now always returns False
            assert config.use_legacy_agents is False

    def test_explicit_native_mode(self):
        config = KimiTachiConfig(agent_mode="native")
        assert config.effective_agent_mode == "native"
        assert config.use_native_agents is True

    def test_from_env(self):
        env_vars = {
            "KIMI_TACHI_AGENT_MODE": "native",
            "KIMI_TACHI_ENABLE_PERSONALITY": "false",
            "KIMI_TACHI_DEBUG_AGENTS": "true",
            "KIMI_TACHI_SUBAGENT_CACHE_TTL": "600",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = KimiTachiConfig.from_env()
            assert config.agent_mode == "native"
            assert config.enable_personality is False
            assert config.debug_agents is True
            assert config.subagent_cache_ttl == 600

    def test_from_env_invalid_mode(self):
        with patch.dict(os.environ, {"KIMI_TACHI_AGENT_MODE": "invalid"}, clear=True):
            config = KimiTachiConfig.from_env()
            # Should fallback to auto
            assert config.agent_mode == "auto"

    def test_to_dict(self):
        config = KimiTachiConfig(agent_mode="native")
        d = config.to_dict()
        assert d["agent_mode"] == "native"
        assert d["enable_personality"] is True
        assert "effective_agent_mode" in d


class TestGlobalConfig:
    """Test global configuration functions."""

    def test_get_config_creates_instance(self):
        reset_config()
        with patch("kimi_tachi.config.get_recommended_agent_mode", return_value="native"):
            config = get_config()
            assert isinstance(config, KimiTachiConfig)
            assert config.effective_agent_mode == "native"

    def test_get_config_returns_same_instance(self):
        reset_config()
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_set_config(self):
        reset_config()
        new_config = KimiTachiConfig(agent_mode="native")
        set_config(new_config)
        assert get_config() is new_config

    def test_reset_config(self):
        reset_config()
        config1 = get_config()
        reset_config()
        config2 = get_config()
        assert config1 is not config2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
