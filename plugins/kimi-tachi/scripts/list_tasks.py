#!/usr/bin/env python3
"""
Kimi-Tachi List Background Tasks Tool

List active and recent background tasks.
"""

import contextlib
import json
import sys
from pathlib import Path


def get_state_dir() -> Path:
    """Get kimi-tachi user state directory."""
    return Path.home() / ".kimi-tachi"


def get_all_sessions() -> list[dict]:
    """Load all session data from hooks storage."""
    hooks_dir = get_state_dir() / "memory" / "hooks"
    if not hooks_dir.exists():
        return []

    sessions = []
    for f in sorted(
        hooks_dir.glob("session_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append(data)
        except (OSError, json.JSONDecodeError):
            continue
    return sessions


def extract_tasks(sessions: list[dict], status_filter: str) -> list[dict]:
    """Extract tasks from session data with optional status filtering."""
    tasks = []

    for session in sessions:
        session_id = session.get("session_id", "unknown")

        # Decisions as tasks
        for decision in session.get("decisions", []):
            task = {
                "task_id": f"{session_id}-decision-{decision.get('fingerprint', 'na')[:8]}",
                "kind": "memory_decision",
                "status": "completed",
                "description": decision.get("content", "")[:100],
                "timestamp": decision.get("timestamp", ""),
                "session_id": session_id,
            }
            if status_filter == "all" or status_filter == task["status"]:
                tasks.append(task)

        # Compactions as tasks
        for compaction in session.get("compactions", []):
            task = {
                "task_id": f"{session_id}-compact-{len(tasks)}",
                "kind": "context_compaction",
                "status": "completed",
                "description": f"Context compaction triggered by {compaction.get('trigger', 'unknown')}",
                "timestamp": compaction.get("timestamp", ""),
                "session_id": session_id,
            }
            if status_filter == "all" or status_filter == task["status"]:
                tasks.append(task)

        # Agent calls as tasks
        for event in session.get("events", []):
            if event.get("type") == "agent_call":
                task = {
                    "task_id": f"{session_id}-agent-{len(tasks)}",
                    "kind": "agent_invocation",
                    "status": "completed",
                    "description": f"Agent call: {event.get('agent', 'unknown')}",
                    "timestamp": event.get("timestamp", ""),
                    "session_id": session_id,
                }
                if status_filter == "all" or status_filter == task["status"]:
                    tasks.append(task)

    return tasks


def main():
    """List background tasks."""
    # Parse params from stdin JSON (kimi-cli plugin protocol)
    params = {}
    if not sys.stdin.isatty():
        with contextlib.suppress(json.JSONDecodeError):
            params = json.load(sys.stdin)

    status_filter = params.get("status", "all")
    if status_filter not in {"all", "active", "completed", "failed"}:
        status_filter = "all"

    sessions = get_all_sessions()
    tasks = extract_tasks(sessions, status_filter)

    lines = [f"Kimi-Tachi Background Tasks (filter: {status_filter})", ""]

    if not tasks:
        lines.append("No tasks found.")
    else:
        lines.append(f"Total tasks: {len(tasks)}")
        lines.append("")
        for task in tasks[:20]:  # Show up to 20
            lines.append(f"  {task['task_id']}")
            lines.append(f"    kind: {task['kind']}")
            lines.append(f"    status: {task['status']}")
            lines.append(f"    description: {task['description']}")
            lines.append(f"    session: {task['session_id']}")
            lines.append("")
        if len(tasks) > 20:
            lines.append(f"... and {len(tasks) - 20} more tasks")

    result = {
        "success": True,
        "status_filter": status_filter,
        "total_tasks": len(tasks),
        "tasks": tasks[:50],
        "output": "\n".join(lines),
    }

    print(json.dumps(result, indent=2, default=str))
    sys.exit(0)


if __name__ == "__main__":
    main()
