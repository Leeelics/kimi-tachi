#!/usr/bin/env python3
"""
Category Router - Route Task Tool

Analyze a task and route it to the most appropriate agent.
"""

import json
import sys
import re


CATEGORIES = {
    "explore": {
        "agent": "nekobasu",
        "agent_name": "猫バス (Nekobasu)",
        "icon": "🚌",
        "description": "Code exploration and navigation",
        "patterns": [
            r"find\s+(all|any)",
            r"where\s+is",
            r"locate",
            r"search\s+for",
            r"explore",
            r"navigate",
            r"discover",
            r"@explore",
        ]
    },
    "architect": {
        "agent": "shishigami",
        "agent_name": "シシ神 (Shishigami)",
        "icon": "🦌",
        "description": "System design and architecture",
        "patterns": [
            r"should\s+we",
            r"design",
            r"architecture",
            r"how\s+to\s+structure",
            r"tech\s+stack",
            r"@architect",
        ]
    },
    "implement": {
        "agent": "calcifer",
        "agent_name": "カルシファー (Calcifer)",
        "icon": "🔥",
        "description": "Implementation and coding",
        "patterns": [
            r"implement",
            r"create\s+(a|the)",
            r"add\s+(a|the)",
            r"build",
            r"write\s+(code|function)",
            r"develop",
            r"@implement",
        ]
    },
    "review": {
        "agent": "enma",
        "agent_name": "閻魔大王 (Enma)",
        "icon": "👹",
        "description": "Code review and quality",
        "patterns": [
            r"review",
            r"check\s+(code|quality)",
            r"audit",
            r"is\s+this\s+correct",
            r"@review",
        ]
    },
    "research": {
        "agent": "tasogare",
        "agent_name": "黄昏時 (Tasogare)",
        "icon": "🌆",
        "description": "Planning and research",
        "patterns": [
            r"plan",
            r"research",
            r"analyze",
            r"investigate",
            r"how\s+should",
            r"what\s+is\s+the\s+best",
        ]
    },
    "document": {
        "agent": "phoenix",
        "agent_name": "火の鳥 (Phoenix)",
        "icon": "🐦",
        "description": "Documentation",
        "patterns": [
            r"document",
            r"write\s+(docs|documentation)",
            r"readme",
            r"explain\s+how",
        ]
    },
}


def detect_category(text: str) -> tuple[str, float]:
    """
    Detect category from text.
    
    Returns:
        (category, confidence)
    """
    text_lower = text.lower()
    scores = {}
    
    for category, info in CATEGORIES.items():
        score = 0
        for pattern in info["patterns"]:
            if re.search(pattern, text_lower):
                score += 1
        if score > 0:
            scores[category] = score
    
    if not scores:
        return "implement", 0.5  # Default to implement
    
    best_category = max(scores, key=scores.get)
    confidence = min(scores[best_category] / 2, 1.0)  # Normalize to 0-1
    
    return best_category, confidence


def route_task(task: str, context: str = "") -> dict:
    """Route task to appropriate agent"""
    category, confidence = detect_category(task)
    info = CATEGORIES[category]
    
    lines = [
        "Category Router Results",
        "",
        f"Task: {task[:80]}...",
        "",
        f"Detected Category: {category}",
        f"Confidence: {confidence:.0%}",
        "",
        f"Recommended Agent: {info['icon']} {info['agent_name']}",
        f"Agent ID: {info['agent']}",
        f"Description: {info['description']}",
        "",
        "Routing Suggestion:",
        f"  Use: Agent(subagent_type=\"{get_agent_type(category)}\", ...)",
        f"  Or:  Delegate to {info['agent']}",
    ]
    
    return {
        "success": True,
        "category": category,
        "confidence": confidence,
        "agent": info["agent"],
        "agent_name": info["agent_name"],
        "icon": info["icon"],
        "output": "\n".join(lines)
    }


def get_agent_type(category: str) -> str:
    """Map category to native agent type"""
    mapping = {
        "explore": "explore",
        "architect": "plan",
        "implement": "coder",
        "review": "coder",
        "research": "plan",
        "document": "explore",
    }
    return mapping.get(category, "coder")


def main():
    """Route task from stdin"""
    try:
        params = json.load(sys.stdin)
        task = params.get("task", "")
        context = params.get("context", "")
        
        if not task:
            print(json.dumps({
                "success": False,
                "error": "Missing required parameter: task"
            }))
            sys.exit(1)
        
        result = route_task(task, context)
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
