#!/usr/bin/env python3
"""
Category Router - Detect Category Tool

Detect the category of text without full routing.
"""

import json
import sys

KEYWORDS = {
    "explore": ["find", "search", "locate", "where", "discover", "navigate", "explore", "@explore"],
    "architect": [
        "design",
        "architecture",
        "structure",
        "pattern",
        "system",
        "tech stack",
        "@architect",
    ],
    "implement": ["implement", "create", "add", "build", "write", "develop", "code", "@implement"],
    "review": ["review", "check", "audit", "verify", "inspect", "validate", "@review"],
    "research": ["plan", "research", "analyze", "investigate", "study", "evaluate"],
    "document": ["document", "docs", "readme", "explain", "describe"],
}


def detect_category(text: str) -> dict:
    """Detect category from text"""
    text_lower = text.lower()
    scores = {}

    for category, keywords in KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[category] = score

    if not scores:
        detected = "implement"
        confidence = 0.3
    else:
        detected = max(scores, key=scores.get)
        confidence = min(scores[detected] / 3, 1.0)

    # Get all categories with scores
    all_categories = [{"category": cat, "score": score} for cat, score in scores.items()]
    all_categories.sort(key=lambda x: x["score"], reverse=True)

    lines = [
        "Category Detection",
        "",
        f"Input: {text[:60]}...",
        "",
        f"Detected: {detected} (confidence: {confidence:.0%})",
        "",
    ]

    if all_categories:
        lines.append("All matches:")
        for cat in all_categories:
            lines.append(f"  {cat['category']}: {cat['score']} matches")

    return {
        "success": True,
        "detected_category": detected,
        "confidence": confidence,
        "all_scores": scores,
        "output": "\n".join(lines),
    }


def main():
    """Detect category from stdin"""
    try:
        params = json.load(sys.stdin)
        text = params.get("text", "")

        if not text:
            print(json.dumps({"success": False, "error": "Missing required parameter: text"}))
            sys.exit(1)

        result = detect_category(text)
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
