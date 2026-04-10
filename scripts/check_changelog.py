#!/usr/bin/env python3
"""Check that CHANGELOG.md has an entry for the current project version."""

import tomllib
import sys


def main() -> int:
    with open("pyproject.toml", "rb") as f:
        version = tomllib.load(f)["project"]["version"]

    with open("CHANGELOG.md") as f:
        changelog = f.read()

    if f"## [{version}]" not in changelog:
        print(f"⚠️  No CHANGELOG entry for {version}")
        return 1

    print(f"✅ CHANGELOG has entry for {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
