#!/usr/bin/env python3
"""
Kimi-Tachi Workflow Executor

Deterministic execution planner for multi-agent workflows.
Reads a workflow plan + execution state from stdin and returns structured
instructions for Kamaji to execute via native tools (Agent, TaskOutput, etc.).

Usage:
    echo '{"plan": {...}, "state": {...}}' | python3 execute_workflow.py
"""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

# Ensure src is importable when running from plugin directory
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from kimi_tachi.orchestrator.executor import ExecutionState, execute_workflow
from kimi_tachi.orchestrator.plan import WorkflowPhase, WorkflowPlan


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


def main():
    """Main entry point - reads JSON from stdin, outputs JSON to stdout."""
    params = {}
    if not sys.stdin.isatty():
        with contextlib.suppress(json.JSONDecodeError):
            params = json.load(sys.stdin)

    plan_data = params.get("plan")
    if not plan_data:
        print(json.dumps({"action": "error", "error": "Missing required parameter: plan"}))
        sys.exit(1)

    state_data = params.get("state", {})
    plan = _build_plan(plan_data)
    state = ExecutionState.from_dict(state_data)

    result = execute_workflow(plan, state)
    print(json.dumps(result.to_dict(), indent=2, default=str))
    sys.exit(0 if result.action != "error" else 1)


if __name__ == "__main__":
    main()
