#!/usr/bin/env python3
"""
Category Router - List Categories Tool

List all available categories and their agents.
"""

import json

CATEGORIES = {
    "explore": {
        "agent": "nekobasu",
        "agent_name": "猫バス (Nekobasu)",
        "icon": "🚌",
        "description": "Code exploration, finding files",
        "triggers": ["@explore", "find all...", "where is...", "locate"],
    },
    "architect": {
        "agent": "shishigami",
        "agent_name": "シシ神 (Shishigami)",
        "icon": "🦌",
        "description": "System design, technology decisions",
        "triggers": ["@architect", "should we...", "design...", "architecture"],
    },
    "implement": {
        "agent": "calcifer",
        "agent_name": "カルシファー (Calcifer)",
        "icon": "🔥",
        "description": "Deep coding, refactoring",
        "triggers": ["@implement", "implement...", "create...", "add..."],
    },
    "review": {
        "agent": "enma",
        "agent_name": "閻魔大王 (Enma)",
        "icon": "👹",
        "description": "Code review, audit",
        "triggers": ["@review", "review...", "check...", "audit..."],
    },
    "research": {
        "agent": "tasogare",
        "agent_name": "黄昏時 (Tasogare)",
        "icon": "🌆",
        "description": "Large-scale analysis, planning",
        "triggers": ["plan...", "research...", "analyze...", "investigate..."],
    },
    "document": {
        "agent": "phoenix",
        "agent_name": "火の鳥 (Phoenix)",
        "icon": "🐦",
        "description": "Documentation",
        "triggers": ["document...", "docs...", "readme...", "explain how..."],
    },
}


def list_categories() -> dict:
    """List all categories"""
    lines = [
        "Available Categories",
        "",
        "Use @category or natural language to route tasks:",
        "",
    ]

    categories = []

    for cat_id, info in CATEGORIES.items():
        lines.append(f"  {info['icon']} @{cat_id}")
        lines.append(f"     Agent: {info['agent_name']}")
        lines.append(f"     Description: {info['description']}")
        lines.append(f"     Triggers: {', '.join(info['triggers'])}")
        lines.append("")

        categories.append({"id": cat_id, **info})

    lines.append("Auto-routing:")
    lines.append("  When no @tag is provided, the router analyzes intent")
    lines.append("  and automatically selects the appropriate category.")

    return {"success": True, "categories": categories, "output": "\n".join(lines)}


def main():
    """List categories"""
    result = list_categories()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
