#!/usr/bin/env python3
"""
Todo Enforcer - Check Format Tool

Validate todo format and provide suggestions.
"""

import json
import sys


def check_todo_format(todos: list) -> dict:
    """Check todo format and provide suggestions"""
    issues = []
    suggestions = []

    valid_statuses = {"pending", "in_progress", "completed"}

    for i, todo in enumerate(todos):
        # Check title
        title = todo.get("title", "").strip()
        if not title:
            issues.append(f"Todo {i + 1}: Missing title")
        elif len(title) < 5:
            issues.append(f"Todo {i + 1}: Title too short ('{title}') - be more descriptive")
        elif title.lower() in ["do stuff", "fix things", "work on it"]:
            issues.append(f"Todo {i + 1}: Vague title ('{title}') - make it specific")

        # Check status
        status = todo.get("status", "")
        if not status:
            issues.append(f"Todo {i + 1}: Missing status")
        elif status not in valid_statuses:
            issues.append(
                f"Todo {i + 1}: Invalid status '{status}' - use: pending, in_progress, completed"
            )

        # Check for action verbs
        if title and not any(
            title.lower().startswith(v)
            for v in [
                "create",
                "update",
                "delete",
                "fix",
                "add",
                "remove",
                "implement",
                "test",
                "review",
                "analyze",
                "refactor",
                "write",
                "document",
                "check",
                "verify",
            ]
        ):
            suggestions.append(
                f"Todo {i + 1}: Consider starting with an action verb (e.g., 'Implement', 'Create', 'Fix')"
            )

    lines = ["Todo Format Check", ""]

    if issues:
        lines.append("❌ Issues Found:")
        for issue in issues:
            lines.append(f"   • {issue}")
        lines.append("")

    if suggestions:
        lines.append("💡 Suggestions:")
        for suggestion in suggestions:
            lines.append(f"   • {suggestion}")
        lines.append("")

    if not issues and not suggestions:
        lines.append("✅ All todos look good!")

    return {
        "success": True,
        "valid": len(issues) == 0,
        "issues": issues,
        "suggestions": suggestions,
        "output": "\n".join(lines),
    }


def main():
    """Check format from stdin"""
    try:
        params = json.load(sys.stdin)
        todos = params.get("todos", [])

        result = check_todo_format(todos)
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
