#!/usr/bin/env python3
"""
Todo Enforcer - Generate Template Tool

Generate todo list templates for common task types.
"""

import json
import sys

TEMPLATES = {
    "feature": [
        {"title": "Analyze requirements and understand the feature", "status": "pending"},
        {"title": "Research existing code and patterns", "status": "pending"},
        {"title": "Design solution and architecture", "status": "pending"},
        {"title": "Implement core functionality", "status": "pending"},
        {"title": "Add tests and verify coverage", "status": "pending"},
        {"title": "Update documentation", "status": "pending"},
        {"title": "Review and refactor if needed", "status": "pending"},
    ],
    "bugfix": [
        {"title": "Reproduce the bug", "status": "pending"},
        {"title": "Analyze root cause", "status": "pending"},
        {"title": "Implement fix", "status": "pending"},
        {"title": "Add regression test", "status": "pending"},
        {"title": "Verify fix works", "status": "pending"},
        {"title": "Check for similar issues", "status": "pending"},
    ],
    "refactor": [
        {"title": "Analyze current implementation", "status": "pending"},
        {"title": "Identify refactoring targets", "status": "pending"},
        {"title": "Ensure tests exist (add if missing)", "status": "pending"},
        {"title": "Perform refactoring in small steps", "status": "pending"},
        {"title": "Run tests after each change", "status": "pending"},
        {"title": "Verify no behavior changes", "status": "pending"},
    ],
    "explore": [
        {"title": "Define exploration goals", "status": "pending"},
        {"title": "Search for relevant code", "status": "pending"},
        {"title": "Analyze patterns and architecture", "status": "pending"},
        {"title": "Document findings", "status": "pending"},
        {"title": "Summarize key insights", "status": "pending"},
    ],
    "document": [
        {"title": "Identify documentation gaps", "status": "pending"},
        {"title": "Gather information from code", "status": "pending"},
        {"title": "Write documentation draft", "status": "pending"},
        {"title": "Add code examples", "status": "pending"},
        {"title": "Review for clarity and accuracy", "status": "pending"},
        {"title": "Update related docs if needed", "status": "pending"},
    ],
}


def generate_template(task_type: str, task_description: str = "") -> dict:
    """Generate todo template for task type"""
    template = TEMPLATES.get(task_type, TEMPLATES["feature"])

    lines = [
        f"Generated Todo Template: {task_type}",
        "",
    ]

    if task_description:
        lines.append(f"Task: {task_description}")
        lines.append("")

    lines.append("```json")
    lines.append(json.dumps({"todos": template}, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("Copy the JSON above and use with SetTodoList tool.")

    return {
        "success": True,
        "template": template,
        "task_type": task_type,
        "output": "\n".join(lines),
    }


def main():
    """Generate template from stdin"""
    try:
        params = json.load(sys.stdin)
        task_type = params.get("task_type", "feature")
        task_description = params.get("task_description", "")

        result = generate_template(task_type, task_description)
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
