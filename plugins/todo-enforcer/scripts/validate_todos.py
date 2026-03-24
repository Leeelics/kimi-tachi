#!/usr/bin/env python3
"""
Todo Enforcer - Validate Todos Tool

Check if all todos are completed before claiming done.
"""

import json
import sys


def validate_todos(todos: list, strict: bool = True) -> dict:
    """
    Validate todo list.
    
    Args:
        todos: List of todo items with title and status
        strict: If True, fail if any todo is not completed
    
    Returns:
        Validation result
    """
    if not todos:
        return {
            "success": True,
            "valid": True,
            "message": "No todos to validate",
            "output": "ℹ️  No todos in list",
            "stats": {"total": 0, "completed": 0, "in_progress": 0, "pending": 0}
        }
    
    total = len(todos)
    completed = sum(1 for t in todos if t.get("status") == "completed")
    in_progress = sum(1 for t in todos if t.get("status") == "in_progress")
    pending = sum(1 for t in todos if t.get("status") == "pending")
    
    lines = [
        "Todo Validation Results",
        "",
        f"Total: {total}",
        f"  ✅ Completed: {completed}",
        f"  🔄 In Progress: {in_progress}",
        f"  ⏳ Pending: {pending}",
        "",
    ]
    
    if pending > 0:
        lines.append("❌ VALIDATION FAILED")
        lines.append("   Pending todos found:")
        for todo in todos:
            if todo.get("status") == "pending":
                lines.append(f"     • {todo.get('title', 'Untitled')}")
    
    if in_progress > 0:
        lines.append("⚠️  IN PROGRESS ITEMS")
        lines.append("   Still working on:")
        for todo in todos:
            if todo.get("status") == "in_progress":
                lines.append(f"     • {todo.get('title', 'Untitled')}")
    
    all_completed = completed == total and total > 0
    
    if all_completed:
        lines.append("✅ ALL TODOS COMPLETED")
        lines.append("   Ready to claim done!")
        message = "All todos completed"
        valid = True
    elif strict and (pending > 0 or in_progress > 0):
        lines.append("")
        lines.append("🚫 Cannot claim 'Done' yet!")
        lines.append("   Complete all todos first or explain blockers.")
        message = f"Incomplete todos: {pending} pending, {in_progress} in_progress"
        valid = False
    else:
        lines.append("")
        lines.append("⚠️  Todos incomplete (non-strict mode)")
        message = f"Progress: {completed}/{total} completed"
        valid = True
    
    return {
        "success": True,
        "valid": valid,
        "message": message,
        "output": "\n".join(lines),
        "stats": {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "completion_rate": round(completed / total * 100, 1) if total > 0 else 0
        }
    }


def main():
    """Validate todos from stdin"""
    try:
        params = json.load(sys.stdin)
        todos = params.get("todos", [])
        strict = params.get("strict", True)
        
        result = validate_todos(todos, strict)
        print(json.dumps(result, indent=2))
        
        sys.exit(0 if result["valid"] else 1)
        
    except json.JSONDecodeError as e:
        print(json.dumps({
            "success": False,
            "valid": False,
            "error": f"Invalid JSON: {e}",
            "output": f"❌ Error: {e}"
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "valid": False,
            "error": str(e),
            "output": f"❌ Error: {e}"
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
