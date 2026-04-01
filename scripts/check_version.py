#!/usr/bin/env python3
"""
Check version consistency across project files.

Inspired by kimi-cli's scripts/check_version_tag.py
"""

import argparse
import json
import re
import sys
import tomllib


def get_pyproject_version() -> str:
    """Get version from pyproject.toml."""
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def get_init_version() -> str:
    """Get version from __init__.py."""
    with open("src/kimi_tachi/__init__.py") as f:
        content = f.read()
    match = re.search(r'__version__ = "([^"]+)"', content)
    if not match:
        raise ValueError("Could not find __version__ in __init__.py")
    return match.group(1)


def get_plugin_version() -> str:
    """Get version from plugin.json."""
    with open("plugins/kimi-tachi/plugin.json") as f:
        data = json.load(f)
    return data["version"]


def get_changelog_version() -> str | None:
    """Get latest version from CHANGELOG.md."""
    with open("CHANGELOG.md") as f:
        content = f.read()
    # Look for ## [x.y.z] pattern
    match = re.search(r"## \[([\d.]+)\]", content)
    return match.group(1) if match else None


def check_versions(expected: str | None = None) -> bool:
    """Check all versions are consistent."""
    print("Checking version consistency...\n")

    versions = {
        "pyproject.toml": get_pyproject_version(),
        "__init__.py": get_init_version(),
        "plugin.json": get_plugin_version(),
    }

    # Display versions
    for source, version in versions.items():
        print(f"  {source:20s}: {version}")

    # Check consistency
    unique_versions = set(versions.values())
    if len(unique_versions) != 1:
        print("\n❌ Version mismatch!")
        return False

    version = list(unique_versions)[0]
    print(f"\n✅ All versions match: {version}")

    # Check against expected version
    if expected:
        # Remove 'v' prefix if present
        expected = expected.lstrip("v")
        if version != expected:
            print("\n❌ Version mismatch with expected!")
            print(f"   Expected: {expected}")
            print(f"   Got:      {version}")
            return False
        print(f"\n✅ Version matches expected: {expected}")

    # Check CHANGELOG
    changelog_version = get_changelog_version()
    if changelog_version:
        print(f"  CHANGELOG.md:         {changelog_version}")
        if changelog_version != version:
            print(f"\n⚠️  CHANGELOG version ({changelog_version}) doesn't match ({version})")
            return False
        print("\n✅ CHANGELOG is up to date")
    else:
        print("\n⚠️  No version found in CHANGELOG")

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check version consistency")
    parser.add_argument(
        "--expected", help="Expected version (for release validation)", default=None
    )
    args = parser.parse_args()

    try:
        if check_versions(args.expected):
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
