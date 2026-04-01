"""
Tests for compatibility module.

Author: kimi-tachi Team
"""

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from kimi_tachi.compatibility import (
    VersionInfo,
    check_compatibility,
    ensure_compatibility,
    get_cli_version,
    get_recommended_agent_mode,
    parse_version,
)


class TestVersionInfo:
    """Test VersionInfo named tuple."""

    def test_creation(self):
        v = VersionInfo(1, 25, 0, "1.25.0")
        assert v.major == 1
        assert v.minor == 25
        assert v.patch == 0
        assert v.raw == "1.25.0"

    def test_string_conversion(self):
        v = VersionInfo(1, 25, 3, "1.25.3")
        assert str(v) == "1.25.3"

    def test_comparison_ge(self):
        v = VersionInfo(1, 25, 0, "1.25.0")
        assert v >= (1, 25)
        assert v >= (1, 24)
        assert not (v >= (1, 26))

    def test_comparison_lt(self):
        v = VersionInfo(1, 24, 0, "1.24.0")
        assert v < (1, 25)
        assert not (v < (1, 24))


class TestParseVersion:
    """Test version parsing."""

    def test_simple_version(self):
        v = parse_version("1.25.0")
        assert v.major == 1
        assert v.minor == 25
        assert v.patch == 0

    def test_version_with_prefix(self):
        v = parse_version("kimi version 1.25.3")
        assert v.major == 1
        assert v.minor == 25
        assert v.patch == 3

    def test_version_with_v_prefix(self):
        v = parse_version("v1.26.0")
        assert v.major == 1
        assert v.minor == 26
        assert v.patch == 0

    def test_invalid_version(self):
        with pytest.raises(ValueError):
            parse_version("invalid")

        with pytest.raises(ValueError):
            parse_version("")


class TestGetCliVersion:
    """Test CLI version detection."""

    def test_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "1.25.0\n"

        with patch("subprocess.run", return_value=mock_result):
            version = get_cli_version()
            assert version is not None
            assert version.major == 1
            assert version.minor == 25

    def test_failure_not_found(self):
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            version = get_cli_version()
            assert version is None

    def test_failure_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("kimi", 5)):
            version = get_cli_version()
            assert version is None

    def test_failure_nonzero_exit(self):
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            version = get_cli_version()
            assert version is None


class TestCheckCompatibility:
    """Test compatibility checking."""

    def test_compatible(self):
        with patch(
            "kimi_tachi.compatibility.get_cli_version", return_value=VersionInfo(1, 25, 0, "1.25.0")
        ):
            report = check_compatibility()
            assert report.is_compatible is True
            assert "1.25.0" in report.message

    def test_too_old(self):
        with patch(
            "kimi_tachi.compatibility.get_cli_version", return_value=VersionInfo(1, 24, 0, "1.24.0")
        ):
            report = check_compatibility()
            assert report.is_compatible is False
            assert "too old" in report.message

    def test_not_installed(self):
        with patch("kimi_tachi.compatibility.get_cli_version", return_value=None):
            report = check_compatibility()
            assert report.is_compatible is False
            assert "Cannot detect" in report.message

    def test_newer_version(self):
        with patch(
            "kimi_tachi.compatibility.get_cli_version", return_value=VersionInfo(1, 26, 0, "1.26.0")
        ):
            report = check_compatibility()
            assert report.is_compatible is True


class TestEnsureCompatibility:
    """Test ensure_compatibility function."""

    def test_compatible_no_action(self):
        with (
            patch(
                "kimi_tachi.compatibility.get_cli_version",
                return_value=VersionInfo(1, 25, 0, "1.25.0"),
            ),
            patch("warnings.warn") as mock_warn,
        ):
            result = ensure_compatibility()
            assert result is True
            mock_warn.assert_not_called()

    def test_incompatible_no_fallback(self):
        """Legacy fallback removed in v0.3.0 - should return False"""
        with (
            patch(
                "kimi_tachi.compatibility.get_cli_version",
                return_value=VersionInfo(1, 24, 0, "1.24.0"),
            ),
            patch("warnings.warn"),
            patch.dict(os.environ, {}, clear=True),
        ):
            result = ensure_compatibility(auto_fallback=True)
            # v0.3.0: No fallback, returns False for incompatible
            assert result is False

    def test_incompatible_without_fallback(self):
        with (
            patch(
                "kimi_tachi.compatibility.get_cli_version",
                return_value=VersionInfo(1, 24, 0, "1.24.0"),
            ),
            patch("warnings.warn"),
        ):
            result = ensure_compatibility(auto_fallback=False)
            assert result is False


class TestGetRecommendedAgentMode:
    """Test get_recommended_agent_mode function."""

    def test_recommends_native_for_new_cli(self):
        with patch(
            "kimi_tachi.compatibility.get_cli_version", return_value=VersionInfo(1, 25, 0, "1.25.0")
        ):
            mode = get_recommended_agent_mode()
            assert mode == "native"

    def test_recommends_native_warns_for_old_cli(self):
        """v0.3.0: Always recommends native, but warns for old CLI"""
        with (
            patch(
                "kimi_tachi.compatibility.get_cli_version",
                return_value=VersionInfo(1, 24, 0, "1.24.0"),
            ),
            patch("warnings.warn") as mock_warn,
        ):
            mode = get_recommended_agent_mode()
            assert mode == "native"
            # Should warn about incompatibility
            mock_warn.assert_called()

    def test_recommends_native_warns_when_not_installed(self):
        """v0.3.0: Always recommends native, but warns when CLI not found"""
        with (
            patch("kimi_tachi.compatibility.get_cli_version", return_value=None),
            patch("warnings.warn") as mock_warn,
        ):
            mode = get_recommended_agent_mode()
            assert mode == "native"
            # Should warn about missing CLI
            mock_warn.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
