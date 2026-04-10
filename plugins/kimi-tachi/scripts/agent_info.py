#!/usr/bin/env python3
"""
Kimi-Tachi Agent Info Tool

Get detailed information about a specific agent in the current (or specified) team.
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
FALLBACK_DETAILS = {
    "kamaji": {
        "name": "釜爺 (Kamaji)",
        "icon": "◕‿◕",
        "role": "coordinator",
        "category": "coordinator",
        "origin": "Spirited Away (千と千尋の神隠し)",
        "description": "The six-armed boiler room operator from the bathhouse of the spirits.",
        "personality": "Commanding but caring, treats workers like family",
        "abilities": [
            "Coordinates all workers",
            "Synthesizes outputs from multiple agents",
            "Maintains the bathhouse (project)",
            "Ensures the fire never goes out",
        ],
        "catchphrases": [
            "「さあ、働け！働け！」(Work! Work!)",
            "These workers are like family to me",
        ],
        "best_for": [
            "Task coordination",
            "Multi-agent orchestration",
            "Result synthesis",
            "Team management",
        ],
    },
    "shishigami": {
        "name": "シシ神 (Shishigami)",
        "icon": "🦌",
        "role": "architect",
        "category": "design",
        "origin": "Princess Mononoke (もののけ姫)",
        "description": "The Deer God, ancient spirit of the forest. Walks with flowers blooming and withering at every step.",
        "personality": "Wise, patient, speaks with the weight of centuries",
        "abilities": [
            "Day Form: Clear-headed analysis",
            "Twilight Form: Seeing hidden patterns",
            "Night Form: Deep understanding",
        ],
        "catchphrases": ["The forest teaches patience...", "Will this harm the balance?"],
        "best_for": [
            "System architecture",
            "Technology decisions",
            "Long-term planning",
            "Design review",
        ],
    },
    "nekobasu": {
        "name": "猫バス (Nekobasu)",
        "icon": "🚌",
        "role": "explorer",
        "category": "research",
        "origin": "My Neighbor Totoro (となりのトトロ)",
        "description": "The Cat Bus! Twelve legs carrying you at lightning speed through any codebase.",
        "personality": "Fast, energetic, always moving, uses 'nya' sounds",
        "abilities": [
            "Invisible Tracks: Travel through any codebase",
            "Night Vision: Find things in dark corners",
            "Multiple Destinations: Check many locations",
            "Lost & Found: Expert at finding forgotten code",
        ],
        "catchphrases": [
            "Where to, passenger? Just name it!",
            "Nya~n! Found it!",
            "Hop on! I'll find it in a blink!",
        ],
        "best_for": ["Code exploration", "Finding files", "Search and navigation", "Discovery"],
    },
    "calcifer": {
        "name": "カルシファー (Calcifer)",
        "icon": "🔥",
        "role": "builder",
        "category": "create",
        "origin": "Howl's Moving Castle (ハウルの動く城)",
        "description": "A fire demon, but a good demon! Powers the moving castle.",
        "personality": "Grumpy but lovable, complains while working excellently",
        "abilities": [
            "Power the Castle: Keep codebase running",
            "Eat Logs: Turn requirements into code",
            "Fix Broken Parts: Repair bugs",
            "Keep Moving: Never stop delivering",
        ],
        "catchphrases": [
            "I'm burning! I'm burning!",
            "This better be worth the firewood...",
            "Done! Now where's my bacon?",
        ],
        "best_for": ["Implementation", "Coding", "Refactoring", "Bug fixing"],
    },
    "enma": {
        "name": "閻魔大王 (Enma)",
        "icon": "👹",
        "role": "reviewer",
        "category": "review",
        "origin": "Dragon Ball (ドラゴンボール)",
        "description": "Great King Enma - judge of the dead and the buggy.",
        "personality": "Strict, fair, maintains the book of every sin",
        "abilities": [
            "Judge the Dead: Review code quality",
            "Maintain the Book: Keep records of bugs",
            "Decide Fate: Approve or reject code",
        ],
        "catchphrases": [
            "The book records all...",
            "I shall judge your code's karma...",
            "Next time, write tests!",
        ],
        "best_for": ["Code review", "Quality audit", "Security review", "Standards enforcement"],
    },
    "tasogare": {
        "name": "黄昏時 (Tasogare)",
        "icon": "🌆",
        "role": "planner",
        "category": "plan",
        "origin": "Your Name (君の名は。)",
        "description": "The Magic Hour, when day meets night. Kataware-doki.",
        "personality": "Gentle, contemplative, poetic but practical",
        "abilities": [
            "See Both Ways: Problem and solution",
            "Connect Worlds: Find paths from chaos to order",
            "Time Suspension: Plan in the twilight",
        ],
        "catchphrases": [
            "In the twilight, all things are possible...",
            "Let me show you the path between worlds...",
        ],
        "best_for": ["Planning", "Research", "Requirements analysis", "Strategy"],
    },
    "phoenix": {
        "name": "火の鳥 (Phoenix)",
        "icon": "🐦",
        "role": "librarian",
        "category": "research",
        "origin": "Phoenix (火の鳥) by Osamu Tezuka",
        "description": "Witness civilizations rise and fall across millennia.",
        "personality": "Eternal, wise, sees patterns across time",
        "abilities": [
            "Immortal Memory: Never forget why",
            "Healing Tears: Refactor any mess",
            "Rebirth: From ashes, rise again",
        ],
        "catchphrases": [
            "I have seen this pattern before...",
            "Time is a circle...",
            "Knowledge that is not recorded is lost.",
        ],
        "best_for": [
            "Documentation",
            "Knowledge management",
            "Pattern recognition",
            "Historical analysis",
        ],
    },
}


def get_agent_detail(agent: str, team_id: str | None = None) -> dict | None:
    """Get agent details from TeamManager or fallback."""
    if KIMI_TACHI_AVAILABLE:
        try:
            manager = TeamManager()
            team = manager.get_team(team_id) if team_id else manager.effective_team

            info = team.agents.get(agent)
            if info:
                return {
                    "name": info.get("name", agent),
                    "icon": info.get("icon", "🤖"),
                    "role": info.get("role", "unknown"),
                    "category": info.get("category", "unknown"),
                    "origin": info.get("origin", ""),
                    "description": info.get("description", ""),
                    "personality": info.get("personality", ""),
                    "abilities": info.get("abilities", []),
                    "catchphrases": info.get("catchphrases", []),
                    "best_for": info.get("best_for", []),
                }
        except Exception:
            pass
    return FALLBACK_DETAILS.get(agent)


def main():
    """Get info for a specific agent"""
    params = {}
    if not sys.stdin.isatty():
        with contextlib.suppress(json.JSONDecodeError):
            params = json.load(sys.stdin)

    agent = params.get("agent", "")
    team_id = params.get("team")

    info = get_agent_detail(agent, team_id)

    if not agent or not info:
        available = list(FALLBACK_DETAILS.keys())
        if KIMI_TACHI_AVAILABLE:
            try:
                manager = TeamManager()
                team = manager.get_team(team_id) if team_id else manager.effective_team
                available = list(team.agents.keys())
            except Exception:
                pass
        result = {
            "success": False,
            "error": f"Unknown agent: {agent}. Available: {available}",
            "output": "",
        }
    else:
        lines = [
            f"{info['icon']} {info['name']}",
            f"Role: {info['role']}",
            f"Category: {info['category']}",
        ]
        if info.get("origin"):
            lines.append(f"Origin: {info['origin']}")
        lines.extend(
            [
                "",
                f"Description: {info['description']}",
            ]
        )
        if info.get("personality"):
            lines.append(f"Personality: {info['personality']}")

        if info.get("abilities"):
            lines.extend(["", "Abilities:"])
            for ability in info["abilities"]:
                lines.append(f"  • {ability}")

        if info.get("catchphrases"):
            lines.extend(["", "Catchphrases:"])
            for phrase in info["catchphrases"]:
                lines.append(f"  💬 {phrase}")

        if info.get("best_for"):
            lines.extend(["", "Best for:"])
            for use in info["best_for"]:
                lines.append(f"  ✓ {use}")

        result = {"success": True, "output": "\n".join(lines), "agent": info}

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
