"""
kimi-tachi (君たち) - Multi-agent task orchestration for Kimi CLI

A squad of specialized agents working together (七人衆):
- kamaji: Task coordinator (釜爺)
- shishigami: Architecture consultant (山兽神)
- nekobasu: Code explorer (猫巴士)
- calcifer: Implementation expert (火魔)
- enma: Code reviewer (阎魔王)
- tasogare: Research planner (黄昏)
- phoenix: Knowledge manager (火之鸟)

Phase 3.0: Native Agent Tool Support
- Compatible with kimi-cli 1.25.0+
- Native Agent tool integration (coder/explore/plan)
- Backward compatible with CreateSubagent
- Auto-detection of CLI version
"""

__version__ = "0.3.0-dev"
__compatible_cli_versions__ = ">=1.25.0"

__all__ = [
    "cli",
    "message_bus",
    "orchestrator",
    "metrics",
    "config",
    "compatibility",
]


def check_compatibility_at_import():
    """
    Check compatibility at package import time.
    
    This function is called automatically when the package is imported.
    It warns users if their CLI version is incompatible.
    """
    import os
    import warnings
    
    # Skip check if explicitly disabled
    if os.getenv("KIMI_TACHI_SKIP_COMPAT_CHECK", "").lower() in ("1", "true", "yes"):
        return
    
    try:
        from .compatibility import check_compatibility
        
        report = check_compatibility()
        
        if not report.is_compatible:
            warnings.warn(
                f"\n{'='*60}\n"
                f"Kimi-Tachi v{__version__} Compatibility Warning\n"
                f"{'='*60}\n"
                f"{report.message}\n\n"
                f"Recommendation: {report.recommendation}\n"
                f"{'='*60}\n",
                UserWarning,
                stacklevel=2,
            )
    except Exception:
        # Don't fail import if compatibility check fails
        pass


# Run compatibility check on import
check_compatibility_at_import()
