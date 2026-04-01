"""
kimi-tachi Hooks CLI 入口

Usage:
    python -m kimi_tachi.hooks <action> [args...]

Actions:
    store-before-compact    Handle PreCompact event
    recall-on-start         Handle SessionStart event
    summarize-on-end        Handle SessionEnd event
    process-agent           Handle PostToolUse (Agent) event
"""

from .tools import main

if __name__ == "__main__":
    main()
