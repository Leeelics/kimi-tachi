"""
Kimi-Tachi Compatibility Module

Handles version detection and compatibility with different kimi-cli versions.

Author: kimi-tachi Team
Version: 0.3.0
"""

from __future__ import annotations

import re
import subprocess
import warnings
from dataclasses import dataclass
from typing import NamedTuple


class VersionInfo(NamedTuple):
    """Version information tuple"""
    major: int
    minor: int
    patch: int
    raw: str

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __ge__(self, other: tuple[int, int]) -> bool:
        """Compare with (major, minor) tuple"""
        return (self.major, self.minor) >= other

    def __lt__(self, other: tuple[int, int]) -> bool:
        """Compare with (major, minor) tuple"""
        return (self.major, self.minor) < other


@dataclass
class CompatibilityReport:
    """Compatibility check report"""
    is_compatible: bool
    cli_version: VersionInfo | None
    required_version: str
    message: str
    recommendation: str


def parse_version(version_string: str) -> VersionInfo:
    """
    Parse version string into VersionInfo.
    
    Args:
        version_string: Version string like "1.25.0" or "kimi 1.25.0"
    
    Returns:
        VersionInfo tuple
    
    Raises:
        ValueError: If version string cannot be parsed
    """
    # Extract version numbers from string
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', version_string)
    if not match:
        raise ValueError(f"Cannot parse version from: {version_string}")
    
    major, minor, patch = map(int, match.groups())
    return VersionInfo(major, minor, patch, version_string)


def get_cli_version(timeout: float = 5.0) -> VersionInfo | None:
    """
    Get installed kimi-cli version.
    
    Args:
        timeout: Timeout for subprocess call in seconds
    
    Returns:
        VersionInfo if successful, None otherwise
    """
    try:
        result = subprocess.run(
            ["kimi", "--version"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        if result.returncode != 0:
            return None
        
        version_line = result.stdout.strip()
        # Handle both "1.25.0" and "kimi version 1.25.0"
        return parse_version(version_line)
        
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError) as e:
        # kimi not installed or not in PATH
        return None


def check_compatibility(
    required_version: tuple[int, int] = (1, 25),
) -> CompatibilityReport:
    """
    Check if installed kimi-cli is compatible.
    
    Args:
        required_version: Minimum required (major, minor) version
    
    Returns:
        CompatibilityReport with details
    """
    cli_version = get_cli_version()
    required_str = f"{required_version[0]}.{required_version[1]}.0"
    
    if cli_version is None:
        return CompatibilityReport(
            is_compatible=False,
            cli_version=None,
            required_version=required_str,
            message="Cannot detect kimi-cli version. Is it installed?",
            recommendation="Install kimi-cli: https://github.com/your-org/kimi-cli",
        )
    
    if cli_version >= required_version:
        return CompatibilityReport(
            is_compatible=True,
            cli_version=cli_version,
            required_version=required_str,
            message=f"Compatible: kimi-cli {cli_version}",
            recommendation="You're good to go! Use native agent mode for best experience.",
        )
    else:
        return CompatibilityReport(
            is_compatible=False,
            cli_version=cli_version,
            required_version=required_str,
            message=f"kimi-cli {cli_version} is too old. Required: {required_str}+",
            recommendation="Upgrade: pip install -U kimi-cli",
        )


def ensure_compatibility(
    auto_fallback: bool = True,
    warn: bool = True,
) -> bool:
    """
    Ensure compatibility and optionally configure fallback mode.
    
    Args:
        auto_fallback: If True, set KIMI_TACHI_AGENT_MODE=legacy on incompatibility
        warn: If True, emit warnings
    
    Returns:
        True if compatible or fallback successful, False otherwise
    """
    import os
    
    report = check_compatibility()
    
    if report.is_compatible:
        return True
    
    # Not compatible
    if warn:
        warnings.warn(
            f"{report.message}\nRecommendation: {report.recommendation}",
            UserWarning,
            stacklevel=2,
        )
    
    if auto_fallback:
        os.environ["KIMI_TACHI_AGENT_MODE"] = "legacy"
        if warn:
            warnings.warn(
                "Auto-fallback to legacy mode enabled. "
                "Set KIMI_TACHI_AGENT_MODE=legacy to suppress this warning.",
                UserWarning,
                stacklevel=2,
            )
        return True
    
    return False


def get_recommended_agent_mode() -> str:
    """
    Get recommended agent mode based on CLI version.
    
    Returns:
        "native" if CLI >= 1.25.0, "legacy" otherwise
    """
    report = check_compatibility()
    return "native" if report.is_compatible else "legacy"


# Convenience function for CLI output
def print_compatibility_status():
    """Print compatibility status for CLI commands"""
    report = check_compatibility()
    
    print(f"Kimi CLI Version: {report.cli_version or 'Unknown'}")
    print(f"Required Version: {report.required_version}+")
    print(f"Status: {'✅ Compatible' if report.is_compatible else '❌ Incompatible'}")
    print(f"Message: {report.message}")
    
    if not report.is_compatible:
        print(f"Recommendation: {report.recommendation}")
        print(f"Current Mode: {get_recommended_agent_mode()}")


if __name__ == "__main__":
    print_compatibility_status()
