"""
Tests for kimi_tachi.cli module.

Author: kimi-tachi Team
"""

import sys
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from kimi_tachi import __version__
from kimi_tachi.cli import _resolve_data_dir, app, main

runner = CliRunner()


class TestVersionAndHelp:
    """Test version and help flags."""

    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_help_flag(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "kimi-tachi" in result.stdout


class TestStatus:
    """Test status command."""

    def test_status_output(self, monkeypatch):
        monkeypatch.setattr("kimi_tachi.cli.shutil.which", lambda x: None)
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert __version__ in result.stdout
        assert "Agent Mode" in result.stdout


class TestInstall:
    """Test install command."""

    def test_install_without_kimi_config(self, monkeypatch, tmp_path):
        """Install should fail if ~/.kimi does not exist."""
        monkeypatch.setattr("kimi_tachi.cli.KIMI_CONFIG_DIR", tmp_path / "no_such_dir")
        result = runner.invoke(app, ["install"])
        assert result.exit_code == 1
        assert "not found" in result.stderr

    def test_install_success(self, monkeypatch, tmp_path):
        """Install should copy agents/skills/plugins when config dir exists."""
        fake_config = tmp_path / ".kimi"
        fake_config.mkdir()
        fake_tachi = fake_config / "agents" / "kimi-tachi"
        monkeypatch.setattr("kimi_tachi.cli.KIMI_CONFIG_DIR", fake_config)
        monkeypatch.setattr("kimi_tachi.cli.KIMI_TACHI_DIR", fake_tachi)

        result = runner.invoke(app, ["install"])
        assert result.exit_code == 0
        assert "installed successfully" in result.stdout


class TestUninstall:
    """Test uninstall command."""

    def test_uninstall_not_installed(self, monkeypatch, tmp_path):
        """Uninstall should report not installed when nothing exists."""
        fake_config = tmp_path / ".kimi"
        fake_tachi = fake_config / "agents" / "kimi-tachi"
        monkeypatch.setattr("kimi_tachi.cli.KIMI_CONFIG_DIR", fake_config)
        monkeypatch.setattr("kimi_tachi.cli.KIMI_TACHI_DIR", fake_tachi)

        result = runner.invoke(app, ["uninstall"])
        assert result.exit_code == 0
        assert "not installed" in result.stdout

    def test_uninstall_force(self, monkeypatch, tmp_path):
        """Uninstall --force should remove directories without prompt."""
        fake_config = tmp_path / ".kimi"
        fake_tachi = fake_config / "agents" / "kimi-tachi"
        fake_tachi.mkdir(parents=True)
        (fake_config / "skills").mkdir(parents=True)
        (fake_config / "plugins").mkdir(parents=True)
        (fake_config / "kimi-tachi.config").write_text("test")

        monkeypatch.setattr("kimi_tachi.cli.KIMI_CONFIG_DIR", fake_config)
        monkeypatch.setattr("kimi_tachi.cli.KIMI_TACHI_DIR", fake_tachi)

        result = runner.invoke(app, ["uninstall", "--force"])
        assert result.exit_code == 0
        assert "uninstalled successfully" in result.stdout
        assert not fake_tachi.exists()


class TestTeams:
    """Test teams command."""

    def test_teams_when_not_available(self, monkeypatch):
        """Teams should exit with error when TEAM_AVAILABLE is False."""
        monkeypatch.setattr("kimi_tachi.cli.TEAM_AVAILABLE", False)
        result = runner.invoke(app, ["teams"])
        assert result.exit_code == 1
        assert "not available" in result.stderr

    def test_teams_list(self, monkeypatch):
        """Teams list should output available teams."""
        mock_team = MagicMock()
        mock_team.id = "default"
        mock_team.name = "Default Team"
        mock_team.description = "Test team"
        mock_team.coordinator = "kamaji"
        mock_team.agents = {}
        mock_team.workflow_patterns = {}

        mock_manager = MagicMock()
        mock_manager.list_teams.return_value = [mock_team]
        mock_manager.current_team = mock_team
        mock_manager._list_available_agents.return_value = ["kamaji"]

        monkeypatch.setattr("kimi_tachi.cli.TEAM_AVAILABLE", True)
        monkeypatch.setattr("kimi_tachi.cli.TeamManager", lambda: mock_manager)

        result = runner.invoke(app, ["teams", "list"])
        assert result.exit_code == 0
        assert "Default Team" in result.stdout

    def test_teams_switch_success(self, monkeypatch):
        """Teams switch should change current team."""
        old_team = MagicMock()
        old_team.name = "Old"
        new_team = MagicMock()
        new_team.name = "New"
        new_team.coordinator = "calcifer"

        mock_manager = MagicMock()
        mock_manager.current_team = old_team
        mock_manager.switch_team = MagicMock()
        type(mock_manager).current_team = MagicMock(side_effect=[old_team, new_team])

        monkeypatch.setattr("kimi_tachi.cli.TEAM_AVAILABLE", True)
        monkeypatch.setattr("kimi_tachi.cli.TeamManager", lambda: mock_manager)

        result = runner.invoke(app, ["teams", "switch", "new-team"])
        assert result.exit_code == 0
        assert "Switched" in result.stdout

    def test_teams_switch_missing_id(self, monkeypatch):
        """Teams switch without team_id should error."""
        monkeypatch.setattr("kimi_tachi.cli.TEAM_AVAILABLE", True)
        monkeypatch.setattr(
            "kimi_tachi.cli.TeamManager",
            lambda: MagicMock(),
        )
        result = runner.invoke(app, ["teams", "switch"])
        assert result.exit_code == 1
        assert "required" in result.stderr

    def test_teams_current(self, monkeypatch):
        """Teams current should show active team."""
        mock_team = MagicMock()
        mock_team.name = "Active"
        mock_team.id = "active"
        mock_team.coordinator = "kamaji"

        mock_manager = MagicMock()
        mock_manager.current_team = mock_team

        monkeypatch.setattr("kimi_tachi.cli.TEAM_AVAILABLE", True)
        monkeypatch.setattr("kimi_tachi.cli.TeamManager", lambda: mock_manager)

        result = runner.invoke(app, ["teams", "current"])
        assert result.exit_code == 0
        assert "Active" in result.stdout

    def test_teams_info(self, monkeypatch):
        """Teams info should show team details."""
        mock_team = MagicMock()
        mock_team.id = "info-team"
        mock_team.name = "Info Team"
        mock_team.description = "A team for info"
        mock_team.coordinator = "nekobasu"
        mock_team.workflow_patterns = {}

        mock_manager = MagicMock()
        mock_manager.current_team = mock_team
        mock_manager.get_team.return_value = mock_team
        mock_manager._list_available_agents.return_value = ["nekobasu"]

        monkeypatch.setattr("kimi_tachi.cli.TEAM_AVAILABLE", True)
        monkeypatch.setattr("kimi_tachi.cli.TeamManager", lambda: mock_manager)

        result = runner.invoke(app, ["teams", "info", "info-team"])
        assert result.exit_code == 0
        assert "Info Team" in result.stdout


class TestMainEntrypoint:
    """Test main() entrypoint behavior."""

    def test_main_with_no_args_runs_kimi(self, monkeypatch):
        """main() with no args should call _run_kimi."""
        called = {}

        def fake_run_kimi(agent, yolo, work_dir):
            called["agent"] = agent
            called["yolo"] = yolo
            called["work_dir"] = work_dir

        monkeypatch.setattr("kimi_tachi.cli._run_kimi", fake_run_kimi)
        monkeypatch.setattr(sys, "argv", ["kimi-tachi"])

        main()

        assert called["agent"] is None
        assert called["yolo"] is False
        assert called["work_dir"] == "."

    def test_main_with_help_uses_app(self, monkeypatch):
        """main() with --help should invoke typer app and exit cleanly."""
        monkeypatch.setattr(sys, "argv", ["kimi-tachi", "--help"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_main_with_subcommand_uses_app(self, monkeypatch):
        """main() with subcommand should invoke typer app and exit cleanly."""
        monkeypatch.setattr(sys, "argv", ["kimi-tachi", "status"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0


class TestResolveDataDir:
    """Test _resolve_data_dir helper."""

    def test_resolve_from_package_dir(self, monkeypatch, tmp_path):
        """Returns package dir when it exists."""
        fake_package = tmp_path / "pkg"
        fake_package.mkdir()
        target = fake_package / "agents"
        target.mkdir()

        monkeypatch.setattr("kimi_tachi.cli.PACKAGE_DIR", fake_package)
        result = _resolve_data_dir("agents")
        assert result == target

    def test_resolve_fallback_for_editable(self, monkeypatch, tmp_path):
        """Falls back to project root when package dir missing."""
        fake_package = tmp_path / "pkg"
        fake_package.mkdir()

        monkeypatch.setattr("kimi_tachi.cli.PACKAGE_DIR", fake_package)
        result = _resolve_data_dir("nonexistent_dir")
        # Fallback points to parent.parent.parent of cli.py
        assert "nonexistent_dir" in str(result)
