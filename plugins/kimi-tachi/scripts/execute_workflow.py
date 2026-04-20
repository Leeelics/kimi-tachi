#!/usr/bin/env python3
"""
Kimi-Tachi Workflow Executor

Deterministic execution planner for multi-agent workflows.

Accepts either:
  - A pre-built plan:  {"plan": {...}, "state": {...}}
  - A raw task:        {"task": "...", "workflow_type": "auto", "state": {...}}

When given a raw task, it internally generates the plan before computing
execution instructions. Returns structured instructions for Kamaji to
execute via native tools (Agent, TaskOutput, etc.).

Usage:
    echo '{"plan": {...}, "state": {...}}' | python3 execute_workflow.py
    echo '{"task": "implement auth", "workflow_type": "feature"}' | python3 execute_workflow.py
"""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

# Ensure src is importable when running from plugin directory
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

try:
    from kimi_tachi.orchestrator.executor import ExecutionState, execute_workflow
    from kimi_tachi.orchestrator.plan import WorkflowPhase, WorkflowPlan
except Exception as _import_err:
    # Fallback for when kimi_tachi core modules cannot be imported
    # (e.g. running outside the project's venv where typer/rich are missing).
    _fallback_reason = str(_import_err)

    class ExecutionState:
        """Minimal fallback state."""

        def __init__(self):
            self.completed_phase_indices = []
            self.agent_ids = {}
            self.background_tasks = []
            self.current_batch_index = 0

        @classmethod
        def from_dict(cls, data):
            inst = cls()
            inst.completed_phase_indices = data.get("completed_phase_indices", [])
            inst.agent_ids = data.get("agent_ids", {})
            inst.background_tasks = data.get("background_tasks", [])
            inst.current_batch_index = data.get("current_batch_index", 0)
            return inst

        def to_dict(self):
            return {
                "completed_phase_indices": self.completed_phase_indices,
                "agent_ids": self.agent_ids,
                "background_tasks": self.background_tasks,
                "current_batch_index": self.current_batch_index,
            }

    class _ExecutionResult:
        def __init__(self, action, **kwargs):
            self.action = action
            self.spawn = kwargs.get("spawn", [])
            self.wait_tasks = kwargs.get("wait_tasks", [])
            self.todo_updates = kwargs.get("todo_updates", [])
            self.message = kwargs.get("message", "")
            self.error = kwargs.get("error")
            self.plan = kwargs.get("plan")
            self.spawn_mode = kwargs.get("spawn_mode", "sequential")

        def to_dict(self):
            return {
                "action": self.action,
                "spawn": self.spawn,
                "wait_tasks": self.wait_tasks,
                "todo_updates": self.todo_updates,
                "message": self.message,
                "error": self.error,
                "plan": self.plan,
                "spawn_mode": self.spawn_mode,
            }

    def execute_workflow(plan, state):
        """Fallback executor that simply returns a complete action."""
        return _ExecutionResult(
            action="complete",
            message="Fallback execution: kimi_tachi core not importable. "
            "The plan has been generated but cannot be executed by the fallback executor. "
            f"Import error: {_fallback_reason}",
        )

    class WorkflowPhase:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def to_dict(self):
            return dict(self.__dict__)

    class WorkflowPlan:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def to_dict(self):
            return dict(self.__dict__)


def _build_plan(data: dict) -> WorkflowPlan:
    """Deserialize a WorkflowPlan from JSON dict."""
    phases = [
        WorkflowPhase(
            agent=p["agent"],
            description=p["description"],
            prompt=p["prompt"],
            subagent_type=p["subagent_type"],
            can_background=p.get("can_background", False),
            recommended_timeout=p.get("recommended_timeout", 300),
            resume=p.get("resume"),
            model=p.get("model"),
        )
        for p in data.get("phases", [])
    ]
    return WorkflowPlan(
        success=data.get("success", False),
        workflow_type=data.get("workflow_type", "auto"),
        team=data.get("team", ""),
        task=data.get("task", ""),
        work_dir=data.get("work_dir", "."),
        complexity=data.get("complexity", "unknown"),
        phases=phases,
        parallel_batches=data.get("parallel_batches", []),
        recommendations=data.get("recommendations", {}),
        output=data.get("output", ""),
        todo_items=data.get("todo_items"),
        plan_file_path=data.get("plan_file_path"),
        error=data.get("error"),
    )


def _generate_plan_from_task(params: dict) -> dict:
    """Generate a plan dict from a raw task description.

    Imports generate_workflow_plan from the sibling workflow.py script.
    """
    script_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(script_dir))
    try:
        from workflow import generate_workflow_plan  # type: ignore[import-not-found]

        return generate_workflow_plan(
            task=params["task"],
            workflow_type=params.get("workflow_type", "auto"),
            work_dir=params.get("work_dir", "."),
            team_id=params.get("team"),
        )
    finally:
        sys.path.remove(str(script_dir))


def main():
    """Main entry point - reads JSON from stdin, outputs JSON to stdout."""
    params = {}
    if not sys.stdin.isatty():
        with contextlib.suppress(json.JSONDecodeError):
            params = json.load(sys.stdin)

    plan_data = params.get("plan")
    if not plan_data:
        task = params.get("task")
        if task:
            plan_data = _generate_plan_from_task(params)
        else:
            print(
                json.dumps(
                    {
                        "action": "error",
                        "error": "Missing required parameter: either 'plan' or 'task' must be provided",
                    }
                )
            )
            sys.exit(1)

    state_data = params.get("state", {})
    plan = _build_plan(plan_data)
    state = ExecutionState.from_dict(state_data)

    result = execute_workflow(plan, state)

    # Include the plan in the result so Kamaji can cache it for subsequent calls
    result.plan = plan_data

    print(json.dumps(result.to_dict(), indent=2, default=str))
    sys.exit(0 if result.action != "error" else 1)


if __name__ == "__main__":
    main()
