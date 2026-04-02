#!/usr/bin/env python3
from __future__ import annotations

"""
Test that built packages can be installed and imported.

Inspired by kimi-cli's smoke test for binaries.
"""

import subprocess
import sys
import tempfile
from pathlib import Path


def get_package_version() -> str:
    """Get version from pyproject.toml."""
    import tomllib

    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def find_wheel() -> Path | None:  # noqa: UP007
    """Find built wheel in dist/."""
    dist_dir = Path("dist")
    if not dist_dir.exists():
        return None

    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        return None

    # Return the most recent wheel
    return max(wheels, key=lambda p: p.stat().st_mtime)


def find_sdist() -> Path | None:
    """Find built source distribution in dist/."""
    dist_dir = Path("dist")
    if not dist_dir.exists():
        return None

    sdists = list(dist_dir.glob("*.tar.gz"))
    if not sdists:
        return None

    return max(sdists, key=lambda p: p.stat().st_mtime)


def test_wheel_install() -> bool:
    """Test wheel can be installed and imported."""
    wheel = find_wheel()
    if not wheel:
        print("❌ No wheel found in dist/")
        return False

    print(f"Testing wheel: {wheel.name}")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create virtual environment
        venv_path = Path(tmpdir) / "venv"
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)], capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to create venv: {result.stderr}")
            return False

        pip = venv_path / "bin" / "pip"
        python = venv_path / "bin" / "python"

        # Install wheel
        result = subprocess.run([str(pip), "install", str(wheel)], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to install wheel: {result.stderr}")
            return False

        # Test import
        result = subprocess.run(
            [str(python), "-c", "import kimi_tachi; print(f'kimi-tachi {kimi_tachi.__version__}')"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"❌ Failed to import: {result.stderr}")
            return False

        output = result.stdout.strip()
        expected_version = get_package_version()
        if expected_version not in output:
            print(f"❌ Version mismatch: expected {expected_version}, got {output}")
            return False

        print(f"  ✅ Installed and imported: {output}")

        # Test CLI
        result = subprocess.run(
            [str(python), "-m", "kimi_tachi", "--version"], capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  ⚠️  CLI --version failed: {result.stderr}")
        else:
            print(f"  ✅ CLI works: {result.stdout.strip()}")

        return True


def test_sdist_install() -> bool:
    """Test source distribution can be installed."""
    sdist = find_sdist()
    if not sdist:
        print("⚠️  No sdist found in dist/ (skipping)")
        return True

    print(f"Testing sdist: {sdist.name}")

    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir) / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], capture_output=True)

        pip = venv_path / "bin" / "pip"
        python = venv_path / "bin" / "python"

        # Install sdist
        result = subprocess.run([str(pip), "install", str(sdist)], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to install sdist: {result.stderr}")
            return False

        # Test import
        result = subprocess.run(
            [str(python), "-c", "import kimi_tachi; print('OK')"], capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to import from sdist: {result.stderr}")
            return False

        print("  ✅ sdist installs and imports correctly")
        return True


def main():
    """Main entry point."""
    print("Testing build artifacts...\n")

    success = True

    if not test_wheel_install():
        success = False

    print()

    if not test_sdist_install():
        success = False

    print()

    if success:
        print("✅ All build tests passed")
        sys.exit(0)
    else:
        print("❌ Some build tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
