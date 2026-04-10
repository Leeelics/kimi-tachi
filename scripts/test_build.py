#!/usr/bin/env python3
"""Test that built packages can be installed and imported.

Inspired by kimi-cli's smoke test for binaries.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def get_package_version() -> str:
    """Get version from pyproject.toml."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # Python < 3.11
        except ImportError:
            # Fallback: parse manually
            content = Path("pyproject.toml").read_text()
            for line in content.split("\n"):
                if line.startswith("version ="):
                    return line.split("=")[1].strip().strip('"')
            raise RuntimeError("Could not find version in pyproject.toml") from None

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
        # Use uv to create venv and install
        result = subprocess.run(["uv", "venv", str(tmpdir)], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to create venv with uv: {result.stderr}")
            return False

        # Install wheel using uv
        result = subprocess.run(
            ["uv", "pip", "install", "--python", str(tmpdir), str(wheel)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"❌ Failed to install wheel: {result.stderr}")
            return False

        # Test import using venv Python directly
        python = Path(tmpdir) / "bin" / "python"
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
            [str(python), "-m", "kimi_tachi", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  ⚠️  CLI --version failed: {result.stderr}")
        else:
            print(f"  ✅ CLI --version works: {result.stdout.strip()}")

        # Test CLI commands that exercise path resolution (critical for wheel installs)
        for cmd_name, cmd_args in [
            ("teams list", [str(python), "-m", "kimi_tachi", "teams", "list"]),
            ("status", [str(python), "-m", "kimi_tachi", "status"]),
        ]:
            result = subprocess.run(cmd_args, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  ❌ CLI '{cmd_name}' failed: {result.stderr}")
                return False
            print(f"  ✅ CLI '{cmd_name}' works")

        return True


def test_sdist_install() -> bool:
    """Test source distribution can be installed."""
    sdist = find_sdist()
    if not sdist:
        print("⚠️  No sdist found in dist/ (skipping)")
        return True

    print(f"Testing sdist: {sdist.name}")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Use uv to create venv and install
        subprocess.run(["uv", "venv", str(tmpdir)], capture_output=True)

        # Install sdist using uv
        result = subprocess.run(
            ["uv", "pip", "install", "--python", str(tmpdir), str(sdist)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"❌ Failed to install sdist: {result.stderr}")
            return False

        # Test import using venv Python directly
        python = Path(tmpdir) / "bin" / "python"
        result = subprocess.run(
            [str(python), "-c", "import kimi_tachi; print('OK')"],
            capture_output=True,
            text=True,
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
