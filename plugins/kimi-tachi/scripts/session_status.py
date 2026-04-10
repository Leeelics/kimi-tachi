#!/usr/bin/env python3
"""
Kimi-Tachi Session Status Tool

Get current kimi-tachi session status including active agents and tasks.
"""

import contextlib
import json
import sys
from pathlib import Path


def get_state_dir() -> Path:
    """Get kimi-tachi user state directory."""
    return Path.home() / ".kimi-tachi"


def get_current_team() -> str | None:
    """Read current team from state file."""
    team_file = get_state_dir() / "current_team"
    if team_file.exists():
        return team_file.read_text(encoding="utf-8").strip()
    return None


def get_session_data(session_id: str | None = None) -> dict:
    """Load session data from hooks storage."""
    hooks_dir = get_state_dir() / "memory" / "hooks"
    if not hooks_dir.exists():
        return {}

    sessions = []
    for f in sorted(
        hooks_dir.glob("session_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append(data)
        except (OSError, json.JSONDecodeError):
            continue

    if session_id:
        for s in sessions:
            if s.get("session_id") == session_id:
                return s
        return {}

    # Return most recent session if no specific ID given
    return sessions[0] if sessions else {}


def get_active_agents(session_data: dict) -> list[dict]:
    """Extract active agents from session events."""
    agents = set()
    for event in session_data.get("events", []):
        if event.get("type") == "agent_call" and event.get("agent"):
            agents.add(event["agent"])
    return [{"name": a, "status": "active"} for a in sorted(agents)]


def get_recent_tasks(session_data: dict) -> list[dict]:
    """Extract recent tasks from session decisions and events."""
    tasks = []
    for decision in session_data.get("decisions", [])[-5:]:
        tasks.append(
            {
                "type": "decision",
                "content": decision.get("content", "")[:100],
                "timestamp": decision.get("timestamp", ""),
            }
        )
    return tasks


def main():
    """Get session status."""
    # Parse optional session_id from stdin JSON (kimi-cli plugin protocol)
    params = {}
    if not sys.stdin.isatty():
        with contextlib.suppress(json.JSONDecodeError):
            params = json.load(sys.stdin)

    session_id = params.get("session_id")
    current_team = get_current_team()
    session_data = get_session_data(session_id)

    active_agents = get_active_agents(session_data)
    recent_tasks = get_recent_tasks(session_data)

    lines = [
        "Kimi-Tachi Session Status",
        "",
        f"Current team: {current_team or 'default (coding)'}",
    ]

    if session_data:
        lines.append(f"Session ID: {session_data.get('session_id', 'unknown')}")
        lines.append(f"Started at: {session_data.get('started_at', 'unknown')}")
        lines.append(f"Compactions: {len(session_data.get('compactions', []))}")
    else:
        lines.append("No session data found.")

    lines.append("")
    lines.append(f"Active agents: {len(active_agents)}")
    for agent in active_agents:
        lines.append(f"  - {agent['name']} ({agent['status']})")

    lines.append("")
    lines.append(f"Recent activities: {len(recent_tasks)}")
    for task in recent_tasks:
        lines.append(f"  - [{task['type']}] {task['content'][:60]}...")

    result = {
        "success": True,
        "current_team": current_team or "coding",
        "session_id": session_data.get("session_id") if session_data else None,
        "active_agents": active_agents,
        "recent_activities": recent_tasks,
        "output": "\n".join(lines),
    }

    print(json.dumps(result, indent=2, default=str))
    sys.exit(0)


if __name__ == "__main__":
    main()
