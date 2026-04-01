"""
kimi-tachi Hooks 工具模块

与 kimi-cli 1.28.0+ Hooks 系统集成，实现自动记忆管理：
- PreCompact: 压缩前存储关键决策
- SessionStart: 会话开始时回忆上下文
- SessionEnd: 会话结束时生成总结

Author: kimi-tachi Team
Version: 0.5.2
"""

from .tools import (
    process_agent_decision,
    recall_on_session_start,
    store_before_compact,
    summarize_on_session_end,
)

__all__ = [
    "store_before_compact",
    "recall_on_session_start",
    "summarize_on_session_end",
    "process_agent_decision",
]
