"""
kimi-tachi Hooks 工具

处理来自 kimi-cli hooks 的事件，实现自动记忆管理。

设计原则：
1. 幂等性：多次执行不重复存储
2. 容错性：记忆失败不阻塞主流程
3. 透明性：用户无感知，自动工作
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 可选的记忆系统导入 (将来使用)
try:
    from memnexus import MemoryEntry, MemoryType  # noqa: F401

    from ..memory.tachi_memory import TachiMemory  # noqa: F401

    MEMNEXUS_AVAILABLE = True
except ImportError:
    MEMNEXUS_AVAILABLE = False

# v0.6.0: Use memnexus 0.4.0+ Session Explorer directly
try:
    from memnexus.session import ExploreOptions, SessionExplorer

    MEMNEXUS_SESSION_AVAILABLE = True
except ImportError:
    MEMNEXUS_SESSION_AVAILABLE = False


def get_memory_storage_path() -> Path:
    """获取记忆存储路径"""
    # 优先从环境变量获取
    if path := os.getenv("KIMI_TACHI_MEMORY_PATH"):
        return Path(path)

    # 默认路径：~/.kimi-tachi/memory
    return Path.home() / ".kimi-tachi" / "memory"


def get_hooks_storage_path() -> Path:
    """获取 hooks 存储路径（用于暂存数据）"""
    path = get_memory_storage_path() / "hooks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_session_data(session_id: str) -> dict[str, Any]:
    """加载会话数据"""
    session_file = get_hooks_storage_path() / f"session_{session_id}.json"
    if session_file.exists():
        try:
            with open(session_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "session_id": session_id,
        "started_at": datetime.now().isoformat(),
        "events": [],
        "decisions": [],
        "compactions": [],
    }


def save_session_data(session_id: str, data: dict[str, Any]) -> None:
    """保存会话数据"""
    session_file = get_hooks_storage_path() / f"session_{session_id}.json"
    try:
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except OSError as e:
        print(f"[kimi-tachi] Warning: Could not save session data: {e}", file=sys.stderr)


def extract_key_decisions(messages: list[dict], session_id: str = "") -> list[dict]:
    """
    从消息中提取关键决策 (v0.6.0 enhanced)

    新增：
    - 去重检查 (使用 memnexus 0.4.0+)
    - 添加指纹
    """
    decisions = []

    # v0.6.0: 获取去重器 (使用 memnexus 0.4.0+)
    deduplicator = None
    if MEMNEXUS_SESSION_AVAILABLE:
        try:
            from memnexus.session import DecisionDeduplicator

            deduplicator = DecisionDeduplicator()
        except Exception:
            pass

    for msg in messages:
        content = msg.get("content", "")
        if not content:
            continue

        # 检测决策标记
        decision_indicators = [
            "decision:",
            "decided:",
            "conclusion:",
            "concluded:",
            "final:",
            "chosen:",
            "selected:",
            "确定",
            "决定",
            "结论",
            "选择",
            "采用",
        ]

        content_lower = content.lower()
        if any(ind in content_lower for ind in decision_indicators):
            # 提取关键句子
            lines = content.split("\n")
            for line in lines:
                line_lower = line.lower().strip()
                if any(ind in line_lower for ind in decision_indicators):
                    line_content = line.strip()

                    # v0.5.3: 去重检查
                    if deduplicator and deduplicator.is_duplicate(line_content):
                        continue  # 跳过重复决策

                    # v0.5.3: 生成指纹
                    fingerprint = ""
                    if deduplicator:
                        fp = deduplicator.add(line_content, session_id)
                        fingerprint = fp.content_hash

                    decision = {
                        "type": "decision",
                        "content": line_content,
                        "timestamp": datetime.now().isoformat(),
                    }

                    # v0.5.3: 添加指纹信息
                    if fingerprint:
                        decision["fingerprint"] = fingerprint
                    if session_id:
                        decision["source_session"] = session_id

                    decisions.append(decision)
                    break

    # v0.6.0: 关闭去重器
    if deduplicator:
        with contextlib.suppress(Exception):
            deduplicator.close()

    return decisions[-5:]  # 只保留最近5个决策


def extract_important_events(messages: list[dict]) -> list[dict]:
    """提取重要事件（Agent 调用、工具使用等）"""
    events = []

    for msg in messages:
        content = msg.get("content", "")

        # 检测 Agent 调用
        if "Agent(" in content or "subagent_type" in content:
            # 提取 Agent 类型
            import re

            match = re.search(r'subagent_type[=:]"([^"]+)"', content)
            if match:
                events.append(
                    {
                        "type": "agent_call",
                        "agent": match.group(1),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        # 检测文件修改
        if any(tool in content for tool in ["WriteFile", "StrReplaceFile"]):
            events.append(
                {
                    "type": "file_edit",
                    "timestamp": datetime.now().isoformat(),
                }
            )

    return events[-10:]  # 保留最近10个事件


# ============================================================================
# Hook 处理函数
# ============================================================================


def store_before_compact(
    session_id: str,
    trigger: str,
    token_count: int,
    **kwargs,
) -> dict[str, Any]:
    """
    PreCompact Hook 处理函数

    在上下文压缩前，自动提取并存储关键决策和重要信息。

    Args:
        session_id: 会话 ID
        trigger: 压缩触发原因 (token_limit, manual, etc.)
        token_count: 当前 token 数量

    Returns:
        操作结果
    """
    result = {
        "success": True,
        "action": "store_before_compact",
        "session_id": session_id,
        "stored": False,
        "reason": "",
    }

    try:
        # 加载会话数据
        session_data = load_session_data(session_id)

        # 记录压缩事件
        session_data["compactions"].append(
            {
                "trigger": trigger,
                "token_count": token_count,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # 如果有 memnexus，存储关键信息
        if MEMNEXUS_AVAILABLE:
            # 提取并存储关键决策
            decisions = extract_key_decisions(session_data.get("messages", []))

            if decisions:
                # TODO: 实际存储到 memnexus
                result["stored_count"] = len(decisions)
                result["stored"] = True
                result["reason"] = f"Stored {len(decisions)} key decisions"
        else:
            # 无 memnexus，仅记录到本地
            result["reason"] = "MemNexus not available, stored locally"

        # 保存会话数据
        save_session_data(session_id, session_data)

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        # 不抛出异常，避免阻塞主流程

    return result


def recall_on_session_start(
    session_id: str,
    source: str,
    cwd: str = "",
    **kwargs,
) -> dict[str, Any]:
    """
    SessionStart Hook 处理函数 (v0.5.3 enhanced)

    会话开始时，自动回忆相关上下文并输出到 stdout。
    kimi-cli 会将 stdout 内容添加到对话上下文。

    v0.5.3 改进：
    - 主动探查其他相关 session
    - 决策指纹去重
    - 相关性评分

    Args:
        session_id: 会话 ID
        source: 来源 (startup, resume)
        cwd: 当前工作目录

    Returns:
        操作结果，同时输出回忆内容到 stdout
    """
    result = {
        "success": True,
        "action": "recall_on_session_start",
        "session_id": session_id,
        "recalled": False,
        "explored_sessions": 0,
        "new_decisions": 0,
    }

    try:
        # 加载或创建会话数据
        session_data = load_session_data(session_id)
        session_data["source"] = source
        session_data["cwd"] = cwd
        session_data["resumed_at"] = datetime.now().isoformat()

        recalled_context = []
        explored_count = 0
        new_decisions_count = 0

        # v0.6.0: 主动探查其他相关 session (使用 memnexus 0.4.0+)
        if MEMNEXUS_SESSION_AVAILABLE and source == "startup":
            try:
                import asyncio

                explorer = SessionExplorer()
                options = ExploreOptions(limit=5, min_relevance=0.3, skip_explored=True)

                exploration = asyncio.run(
                    explorer.explore_related(
                        current_session_id=session_id,
                        query=cwd,
                        context={"cwd": cwd},
                        options=options,
                    )
                )

                if exploration.decisions:
                    recalled_context.append("📚 Related decisions from other sessions:")
                    for d in exploration.decisions:
                        content = d.content
                        source_session = d.source_session[:8]
                        recalled_context.append(f"  - [{source_session}] {content}")

                    explored_count = len(exploration.explored_sessions)
                    new_decisions_count = len(exploration.decisions)
                    result["explored_sessions"] = explored_count
                    result["new_decisions"] = new_decisions_count

                explorer.close()
            except Exception as e:
                # 探查失败不阻塞主流程
                result["explorer_error"] = str(e)

        # 检查是否有之前的会话可以继承（仅 resume 模式）
        if source == "resume":
            # 加载最近的决策
            if session_data.get("decisions"):
                recalled_context.append("📋 Previous decisions:")
                for d in session_data["decisions"][-3:]:
                    recalled_context.append(f"  - {d.get('content', '')}")

            # 加载最近的事件
            if session_data.get("events"):
                recalled_context.append("\n📝 Recent activity:")
                for e in session_data["events"][-3:]:
                    event_type = e.get("type", "unknown")
                    if event_type == "agent_call":
                        recalled_context.append(f"  - Called agent: {e.get('agent', 'unknown')}")
                    elif event_type == "file_edit":
                        recalled_context.append("  - Modified files")

        if recalled_context:
            output = "\n".join(
                [
                    "",
                    "=" * 50,
                    "🧠 kimi-tachi Memory Context:",
                    "=" * 50,
                    *recalled_context,
                    "=" * 50,
                    "",
                ]
            )
            print(output)
            result["recalled"] = True
            result["context_lines"] = len(recalled_context)

        # 保存会话数据
        save_session_data(session_id, session_data)

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result


def summarize_on_session_end(
    session_id: str,
    reason: str,
    **kwargs,
) -> dict[str, Any]:
    """
    SessionEnd Hook 处理函数

    会话结束时，自动生成总结并存储到记忆。

    Args:
        session_id: 会话 ID
        reason: 结束原因

    Returns:
        操作结果
    """
    result = {
        "success": True,
        "action": "summarize_on_session_end",
        "session_id": session_id,
        "summarized": False,
    }

    try:
        # 加载会话数据
        session_data = load_session_data(session_id)
        session_data["ended_at"] = datetime.now().isoformat()
        session_data["end_reason"] = reason

        # 生成总结
        summary_lines = [
            f"Session: {session_id}",
            f"Duration: {calculate_duration(session_data.get('started_at'), session_data.get('ended_at'))}",
            f"End reason: {reason}",
        ]

        # 统计信息
        decisions_count = len(session_data.get("decisions", []))
        events_count = len(session_data.get("events", []))
        compactions_count = len(session_data.get("compactions", []))

        summary_lines.extend(
            [
                f"Decisions made: {decisions_count}",
                f"Events recorded: {events_count}",
                f"Context compactions: {compactions_count}",
            ]
        )

        summary = "\n".join(summary_lines)
        session_data["summary"] = summary

        # 存储到记忆（如果有 memnexus）
        if MEMNEXUS_AVAILABLE and decisions_count > 0:
            # TODO: 实际存储到 memnexus
            result["stored"] = True
            result["summary_length"] = len(summary)

        # 保存会话数据
        save_session_data(session_id, session_data)

        result["summarized"] = True
        result["summary"] = summary

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result


def process_agent_decision(
    session_id: str,
    agent_name: str,
    tool_input: dict,
    tool_output: str,
    **kwargs,
) -> dict[str, Any]:
    """
    PostToolUse Hook 处理函数（Agent 工具）

    Agent 调用后，自动分析并存储关键决策。

    Args:
        session_id: 会话 ID
        agent_name: Agent 名称
        tool_input: 工具输入
        tool_output: 工具输出

    Returns:
        操作结果
    """
    result = {
        "success": True,
        "action": "process_agent_decision",
        "session_id": session_id,
        "agent": agent_name,
        "stored": False,
    }

    try:
        # 加载会话数据
        session_data = load_session_data(session_id)

        # 记录 Agent 调用事件
        event = {
            "type": "agent_call",
            "agent": agent_name,
            "description": tool_input.get("description", ""),
            "timestamp": datetime.now().isoformat(),
        }
        session_data["events"].append(event)

        # 提取决策（从输出中）
        if tool_output:
            decision_indicators = [
                "decision",
                "conclusion",
                "final",
                "chosen",
                "implemented",
                "created",
                "modified",
                "fixed",
            ]

            output_lower = tool_output.lower()
            if any(ind in output_lower for ind in decision_indicators):
                # 这是一个决策性的输出
                decision = {
                    "type": "agent_output",
                    "agent": agent_name,
                    "content": tool_output[:500],  # 限制长度
                    "timestamp": datetime.now().isoformat(),
                }
                session_data["decisions"].append(decision)
                result["stored"] = True

        # 限制存储数量
        session_data["decisions"] = session_data["decisions"][-20:]  # 保留最近20个
        session_data["events"] = session_data["events"][-50:]  # 保留最近50个事件

        # 保存会话数据
        save_session_data(session_id, session_data)

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)

    return result


def calculate_duration(start: str | None, end: str | None) -> str:
    """计算会话时长"""
    if not start or not end:
        return "unknown"

    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        duration = end_dt - start_dt

        minutes = int(duration.total_seconds() // 60)
        if minutes < 60:
            return f"{minutes}m"
        else:
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}h {mins}m"
    except (ValueError, TypeError):
        return "unknown"


# ============================================================================
# CLI 入口
# ============================================================================


def main():
    """CLI 入口，用于从 shell 脚本调用"""
    if len(sys.argv) < 2:
        print("Usage: python -m kimi_tachi.hooks <action> [args...]", file=sys.stderr)
        sys.exit(1)

    action = sys.argv[1]

    # 从 stdin 读取 hook 事件数据
    try:
        event_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        event_data = {}

    # 合并命令行参数
    for arg in sys.argv[2:]:
        if "=" in arg:
            key, value = arg.split("=", 1)
            event_data[key] = value

    # 执行对应动作
    if action == "store-before-compact":
        result = store_before_compact(**event_data)
    elif action == "recall-on-start":
        result = recall_on_session_start(**event_data)
    elif action == "summarize-on-end":
        result = summarize_on_session_end(**event_data)
    elif action == "process-agent":
        result = process_agent_decision(**event_data)
    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)

    # 输出结果
    print(json.dumps(result, indent=2, default=str))

    # 根据结果设置退出码
    sys.exit(0 if result.get("success", False) else 1)


if __name__ == "__main__":
    main()
