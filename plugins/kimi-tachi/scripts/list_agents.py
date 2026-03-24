#!/usr/bin/env python3
"""
Kimi-Tachi List Agents Tool

List all available agents (七人衆) with their roles and icons.
"""

import json
import sys

AGENTS = {
    "kamaji": {
        "name": "釜爺 (Kamaji)",
        "icon": "◕‿◕",
        "role": "coordinator",
        "description": "Task coordinator and orchestrator - the six-armed boiler room chief",
        "best_for": ["General orchestration", "Task delegation", "Team coordination"]
    },
    "shishigami": {
        "name": "シシ神 (Shishigami)",
        "icon": "🦌",
        "role": "architect",
        "description": "Architecture and system design - the ancient forest deity",
        "best_for": ["System design", "Technology decisions", "Architecture review"]
    },
    "nekobasu": {
        "name": "猫バス (Nekobasu)",
        "icon": "🚌",
        "role": "explorer",
        "description": "Fast code exploration - the Cat Bus with twelve legs",
        "best_for": ["Finding code", "Code navigation", "Exploration"]
    },
    "calcifer": {
        "name": "カルシファー (Calcifer)",
        "icon": "🔥",
        "role": "builder",
        "description": "Implementation and coding - the fire demon powering the castle",
        "best_for": ["Implementation", "Coding", "Refactoring"]
    },
    "enma": {
        "name": "閻魔大王 (Enma)",
        "icon": "👹",
        "role": "reviewer",
        "description": "Code review and quality - the strict judge of the afterlife",
        "best_for": ["Code review", "Quality audit", "Bug detection"]
    },
    "tasogare": {
        "name": "黄昏時 (Tasogare)",
        "icon": "🌆",
        "role": "planner",
        "description": "Planning and research - the twilight hour connecting worlds",
        "best_for": ["Planning", "Research", "Requirements analysis"]
    },
    "phoenix": {
        "name": "火の鳥 (Phoenix)",
        "icon": "🐦",
        "role": "librarian",
        "description": "Documentation and knowledge - the eternal observer across time",
        "best_for": ["Documentation", "Knowledge retrieval", "Pattern recognition"]
    }
}


def main():
    """List all agents"""
    result = {
        "success": True,
        "output": "Kimi-Tachi Agents (七人衆):\n",
        "agents": []
    }
    
    lines = ["Kimi-Tachi Agents (七人衆):\n"]
    
    for key, info in AGENTS.items():
        lines.append(f"  {info['icon']} {key}")
        lines.append(f"     Name: {info['name']}")
        lines.append(f"     Role: {info['role']}")
        lines.append(f"     Description: {info['description']}")
        lines.append(f"     Best for: {', '.join(info['best_for'])}")
        lines.append("")
        
        result["agents"].append({
            "id": key,
            **info
        })
    
    result["output"] = "\n".join(lines)
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
