#!/usr/bin/env python3
"""
Kimi-Tachi Compatibility Check Tool

Check kimi-cli version compatibility.
"""

import json
import re
import subprocess
import sys


def get_cli_version():
    """Get installed kimi-cli version"""
    try:
        result = subprocess.run(
            ["kimi", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Parse version from output like "kimi, version 1.25.0"
            match = re.search(r"(\d+)\.(\d+)\.(\d+)", result.stdout)
            if match:
                return {
                    "version": match.group(0),
                    "major": int(match.group(1)),
                    "minor": int(match.group(2)),
                    "patch": int(match.group(3)),
                    "raw": result.stdout.strip(),
                }
        return None
    except Exception:
        return None


def check_compatibility():
    """Check compatibility with kimi-cli"""
    cli_version = get_cli_version()

    if cli_version is None:
        return {
            "success": False,
            "compatible": False,
            "cli_version": None,
            "required_version": ">=1.25.0",
            "message": "Cannot detect kimi-cli. Is it installed?",
            "recommendation": "Install kimi-cli first",
            "output": "❌ kimi-cli not found",
        }

    major, minor = cli_version["major"], cli_version["minor"]
    is_compatible = (major, minor) >= (1, 25)

    lines = [
        "Kimi-Tachi Compatibility Check",
        "",
        f"kimi-cli version: {cli_version['version']}",
        "Required: >= 1.25.0",
        "",
    ]

    if is_compatible:
        lines.append("✅ Compatible! You can use native agent mode.")
        lines.append("   Agent mode: native")
        recommendation = "You're good to go!"
    else:
        lines.append(f"⚠️  kimi-cli {cli_version['version']} is too old.")
        lines.append("   Required: 1.25.0+")
        lines.append("   Agent mode: legacy (fallback)")
        recommendation = "Upgrade: pip install -U kimi-cli"

    lines.append("")
    lines.append(f"Recommendation: {recommendation}")

    return {
        "success": True,
        "compatible": is_compatible,
        "cli_version": cli_version["version"],
        "required_version": ">=1.25.0",
        "message": f"kimi-cli {cli_version['version']} detected",
        "recommendation": recommendation,
        "output": "\n".join(lines),
    }


def main():
    """Check compatibility"""
    result = check_compatibility()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
