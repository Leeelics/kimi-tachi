"""
End-to-end tests for kimi-tachi CLI.

These tests invoke the real CLI binary via subprocess with an isolated HOME.
"""

import os
import subprocess
import sys

from kimi_tachi import __version__

CLI = [sys.executable, "-m", "kimi_tachi.cli"]


class TestCLIVersion:
    """Test version output."""

    def test_version_flag(self):
        result = subprocess.run(
            [*CLI, "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert __version__ in result.stdout


class TestCLIInstallFlow:
    """Test install -> status flow with isolated HOME."""

    def test_install_and_status(self, tmp_path):
        """Install creates agents/skills dirs; status reports them."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        fake_kimi = fake_home / ".kimi"
        fake_kimi.mkdir()

        env = os.environ.copy()
        env["HOME"] = str(fake_home)
        # Also ensure no real config leaks in
        env.pop("KIMI_CONFIG_DIR", None)

        install_result = subprocess.run(
            [*CLI, "install"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert install_result.returncode == 0
        assert "installed successfully" in install_result.stdout

        # Verify directories were created
        tachi_dir = fake_kimi / "agents" / "kimi-tachi"
        assert tachi_dir.exists()
        assert (fake_kimi / "skills").exists()

        # Status should report the installation
        status_result = subprocess.run(
            [*CLI, "status"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert status_result.returncode == 0
        assert __version__ in status_result.stdout
        assert "Agents installed" in status_result.stdout

    def test_uninstall_force(self, tmp_path):
        """Uninstall --force removes everything without prompt."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        (fake_home / ".kimi").mkdir()
        env = os.environ.copy()
        env["HOME"] = str(fake_home)

        # Install first
        subprocess.run([*CLI, "install"], capture_output=True, text=True, env=env, check=True)

        # Uninstall
        uninstall_result = subprocess.run(
            [*CLI, "uninstall", "--force"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert uninstall_result.returncode == 0
        assert "uninstalled successfully" in uninstall_result.stdout

        # Verify removal
        assert not (fake_home / ".kimi" / "agents" / "kimi-tachi").exists()
