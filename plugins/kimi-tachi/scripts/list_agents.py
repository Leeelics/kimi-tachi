#!/usr/bin/env python3
"""
Kimi-Tachi List Agents Tool

List all available agents for the current (or specified) team.
"""

import contextlib
import json
import sys

# Optional kimi-tachi imports for team lookup
try:
    from kimi_tachi.team import TeamManager

    KIMI_TACHI_AVAILABLE = True
except ImportError:
    KIMI_TACHI_AVAILABLE = False

# Fallback defaults (coding team)
FALLBACK_AGENTS = {
    "kamaji": {
        "name": "釜爺 (Kamaji)",
        "icon": "◕‿◕",
        "role": "coordinator",
        "category": "coordinator",
        "description": "Task coordinator and orchestrator - the six-armed boiler room chief",
        "best_for": ["General orchestration", "Task delegation", "Team coordination"],
    },
    "shishigami": {
        "name": "シシ神 (Shishigami)",
        "icon": "🦌",
        "role": "architect",
        "category": "design",
        "description": "Architecture and system design - the ancient forest deity",
        "best_for": ["System design", "Technology decisions", "Architecture review"],
    },
    "nekobasu": {
        "name": "猫バス (Nekobasu)",
        "icon": "🚌",
        "role": "explorer",
        "category": "research",
        "description": "Fast code exploration - the Cat Bus with twelve legs",
        "best_for": ["Finding code", "Code navigation", "Exploration"],
    },
    "calcifer": {
        "name": "カルシファー (Calcifer)",
        "icon": "🔥",
        "role": "builder",
        "category": "create",
        "description": "Implementation and coding - the fire demon powering the castle",
        "best_for": ["Implementation", "Coding", "Refactoring"],
    },
    "enma": {
        "name": "閻魔大王 (Enma)",
        "icon": "👹",
        "role": "reviewer",
        "category": "review",
        "description": "Code review and quality - the strict judge of the afterlife",
        "best_for": ["Code review", "Quality audit", "Bug detection"],
    },
    "tasogare": {
        "name": "黄昏時 (Tasogare)",
        "icon": "🌆",
        "role": "planner",
        "category": "plan",
        "description": "Planning and research - the twilight hour connecting worlds",
        "best_for": ["Planning", "Research", "Requirements analysis"],
    },
    "phoenix": {
        "name": "火の鳥 (Phoenix)",
        "icon": "🐦",
        "role": "librarian",
        "category": "research",
        "description": "Documentation and knowledge - the eternal observer across time",
        "best_for": ["Documentation", "Knowledge retrieval", "Pattern recognition"],
    },
}


def get_agents(team_id: str | None = None) -> dict:
    """Get agents for the specified team (or current team)."""
    if KIMI_TACHI_AVAILABLE:
        try:
            manager = TeamManager()
            team = manager.get_team(team_id) if team_id else manager.effective_team
            agents = {}
            for agent_name, info in team.agents.items():
                agents[agent_name] = {
                    "name": info.get("name", agent_name),
                    "icon": info.get("icon", "🤖"),
                    "role": info.get("role", "unknown"),
                    "category": info.get("category", "unknown"),
                    "description": info.get("description", ""),
                    "best_for": info.get("best_for", []),
                }
            return agents
        except Exception:
            pass
    return dict(FALLBACK_AGENTS)


def main():
    """List all agents"""
    params = {}
    if not sys.stdin.isatty():
        with contextlib.suppress(json.JSONDecodeError):
            params = json.load(sys.stdin)

    team_id = params.get("team")
    agents = get_agents(team_id)

    result = {"success": True, "output": "", "agents": [], "team": team_id}
    lines = []

    # Show team header if available
    if KIMI_TACHI_AVAILABLE and not team_id:
        try:
            manager = TeamManager()
            team = manager.effective_team
            lines.append(f"{team.icon} {team.name} Agents:\n")
            result["team"] = team.id
        except Exception:
            lines.append("Kimi-Tachi Agents:\n")
    else:
        lines.append("Kimi-Tachi Agents:\n")

    for key, info in agents.items():
        lines.append(f"  {info['icon']} {key}")
        lines.append(f"     Name: {info['name']}")
        lines.append(f"     Role: {info['role']}")
        lines.append(f"     Category: {info['category']}")
        lines.append(f"     Description: {info['description']}")
        if info.get("best_for"):
            lines.append(f"     Best for: {', '.join(info['best_for'])}")
        lines.append("")

        result["agents"].append({"id": key, **info})

    result["output"] = "\n".join(lines)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
