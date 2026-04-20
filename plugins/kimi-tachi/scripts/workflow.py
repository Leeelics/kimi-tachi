#!/usr/bin/env python3
"""
Kimi-Tachi Workflow Planner

Generates a structured multi-agent workflow plan for the coordinator (Kamaji)
to execute using kimi-cli's native Agent tool.

This is a plan generator, NOT an executor. The actual agent execution happens
inside the kimi-cli runtime via native `Agent()` tool calls by Kamaji.

Supports multi-team workflow patterns and category-based parallel orchestration.

Usage:
    echo '{"task": "implement auth", "workflow_type": "feature"}' | python3 workflow.py
"""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

# Optional kimi-tachi imports for team/config lookup
try:
    from kimi_tachi.orchestrator.plan import WorkflowPhase, WorkflowPlan
    from kimi_tachi.team import TeamManager

    KIMI_TACHI_AVAILABLE = True
except ImportError:
    KIMI_TACHI_AVAILABLE = False

# Default heuristic keywords
_SIMPLE_KEYWORDS = ["fix typo", "rename", "update comment", "change color", "add log"]
_COMPLEX_KEYWORDS = ["implement", "design", "architecture", "refactor", "new feature"]

# Category-based orchestration rules
# Categories that can safely run in parallel with each other
_PARALLEL_CATEGORIES = {"research", "plan"}
# Categories that should run in background when independent
_BACKGROUND_CATEGORIES = {"research", "plan"}
# Maximum agents per batch to prevent resource exhaustion
_MAX_BATCH_SIZE = 3
# Timeout recommendations by category (seconds)
_CATEGORY_TIMEOUTS = {
    "coordinator": 120,
    "research": 300,
    "plan": 300,
    "design": 300,
    "create": 600,
    "review": 300,
}


def _heuristic_analysis(task: str) -> dict:
    """Simple heuristic-based task analysis."""
    task_lower = task.lower()
    simple_score = sum(1 for k in _SIMPLE_KEYWORDS if k in task_lower)
    complex_score = sum(1 for k in _COMPLEX_KEYWORDS if k in task_lower)
    is_short = len(task.split()) < 10

    if simple_score > 0 or (is_short and complex_score == 0):
        return {"complexity": "simple", "parallelizable": False}
    elif complex_score > 0:
        return {"complexity": "complex", "parallelizable": True}
    else:
        return {"complexity": "medium", "parallelizable": False}


def _get_team(team_id: str | None = None):
    """Get the effective team."""
    if KIMI_TACHI_AVAILABLE:
        try:
            manager = TeamManager()
            return manager.get_team(team_id) if team_id else manager.effective_team
        except Exception:
            pass
    return None


def _get_workflow_pattern(workflow_type: str, team_id: str | None = None) -> list[dict]:
    """Load workflow pattern from TeamManager or fallback to defaults."""
    team = _get_team(team_id)
    if team and workflow_type in team.workflow_patterns:
        pattern_str = team.workflow_patterns[workflow_type]
        return _parse_pattern(pattern_str, team.agents)

    # Fallback defaults (coding team)
    defaults = {
        "feature": [
            {"agent": "tasogare", "description": "Analyze and plan the implementation"},
            {"agent": "nekobasu", "description": "Explore relevant codebase"},
            {"agent": "shishigami", "description": "Design architecture"},
            {"agent": "calcifer", "description": "Implement the feature"},
            {"agent": "enma", "description": "Review code quality"},
        ],
        "bugfix": [
            {"agent": "nekobasu", "description": "Explore codebase to locate bug"},
            {"agent": "shishigami", "description": "Design fix approach"},
            {"agent": "calcifer", "description": "Implement fix"},
            {"agent": "enma", "description": "Verify fix quality"},
        ],
        "explore": [
            {"agent": "nekobasu", "description": "Fast codebase exploration"},
            {"agent": "phoenix", "description": "Document findings and patterns"},
        ],
        "refactor": [
            {"agent": "phoenix", "description": "Identify refactoring targets"},
            {"agent": "shishigami", "description": "Design refactor plan"},
            {"agent": "calcifer", "description": "Execute refactor"},
            {"agent": "enma", "description": "Review changes"},
        ],
        "test": [
            {"agent": "nekobasu", "description": "Explore code to test"},
            {"agent": "calcifer", "description": "Write tests"},
            {"agent": "enma", "description": "Review test coverage"},
        ],
        "docs": [
            {"agent": "phoenix", "description": "Identify documentation gaps"},
            {"agent": "calcifer", "description": "Update code docs and README"},
        ],
        "quick": [
            {"agent": "calcifer", "description": "Quick implementation or fix"},
        ],
    }
    steps = defaults.get(workflow_type, defaults["quick"])
    return [{"agent": s["agent"], "description": s["description"]} for s in steps]


def _parse_pattern(pattern_str: str, team_agents: dict) -> list[dict]:
    """Parse workflow pattern string like 'tasogare → nekobasu → calcifer'."""
    steps = []
    seen = set()
    for token in pattern_str.replace(",", "→").split("→"):
        agent = token.strip()
        if agent and agent not in seen:
            seen.add(agent)
            info = team_agents.get(agent, {})
            steps.append(
                {
                    "agent": agent,
                    "description": info.get("description", f"Delegate to {agent}"),
                }
            )
    return steps


def _map_agent_to_subagent_type(agent: str) -> str:
    """Map agent names to kimi-cli native subagent types.

    For content team agents (guojia, chenlin, etc.), the agent name
    is already registered as a built-in subagent type.
    """
    mapping = {
        "nekobasu": "explore",
        "tasogare": "plan",
        "shishigami": "plan",
        "calcifer": "coder",
        "enma": "coder",
        "phoenix": "coder",
        "kamaji": "coder",
    }
    return mapping.get(agent, agent)


def _recommend_model(agent: str) -> str | None:
    """Recommend a model override for specific agents."""
    # Design and architecture benefit from stronger reasoning models
    if agent == "shishigami":
        return "kimi-k2.5"
    return None


def _resolve_resume(pattern: list[dict], idx: int) -> None:
    """
    Resume is determined at execution time by the orchestrator.

    workflow.py only knows agent names, not the actual agent_ids generated
    by kimi-cli's SubagentStore during execution. Therefore it cannot emit
    a valid resume value. The executor (Kamaji) should track agent_ids
    across phases and pass the previous phase's agent_id when the same
    agent type appears consecutively.
    """
    return None


def _get_agent_category(agent: str, team_id: str | None = None) -> str:
    """Get the category of an agent."""
    team = _get_team(team_id)
    if team:
        return team.agents.get(agent, {}).get("category", "unknown")
    # Fallback hardcoded mappings (all known agents across all teams)
    fallbacks = {
        # Coding team (七人衆)
        "kamaji": "coordinator",
        "nekobasu": "research",
        "calcifer": "create",
        "enma": "review",
        "tasogare": "plan",
        "shishigami": "design",
        "phoenix": "research",
        # Content team (三国·自媒体天团)
        "xunyu": "coordinator",
        "guojia": "research",
        "chenlin": "create",
        "zhugeliang": "review",
        "zhugejin": "design",
    }
    return fallbacks.get(agent, "unknown")


def _compute_parallel_steps(pattern: list[dict], team_id: str | None = None) -> list[list[int]]:
    """
    Compute parallel execution batches based on agent categories.

    Agents in parallel-friendly categories (research, plan) can run together.
    Create/review/design agents are generally sequential.
    Batches are capped at _MAX_BATCH_SIZE to prevent resource exhaustion.
    """
    if not pattern:
        return []

    categories = [_get_agent_category(step["agent"], team_id) for step in pattern]
    batches: list[list[int]] = []
    current_batch: list[int] = []
    current_categories: set[str] = set()

    for idx, cat in enumerate(categories):
        if cat in _PARALLEL_CATEGORIES:
            if current_batch and current_categories - _PARALLEL_CATEGORIES:
                # Previous batch had non-parallel work, flush it
                batches.append(current_batch)
                current_batch = [idx]
                current_categories = {cat}
            elif len(current_batch) >= _MAX_BATCH_SIZE:
                # Batch size limit reached, flush and start new batch
                batches.append(current_batch)
                current_batch = [idx]
                current_categories = {cat}
            else:
                current_batch.append(idx)
                current_categories.add(cat)
        else:
            if current_batch:
                batches.append(current_batch)
                current_batch = []
                current_categories = set()
            batches.append([idx])

    if current_batch:
        batches.append(current_batch)

    return batches


def _build_phase_prompt(
    agent: str, task: str, phase_idx: int, total_phases: int, team_id: str | None = None
) -> str:
    """Build a prompt for a specific workflow phase."""
    cat = _get_agent_category(agent, team_id)
    instructions = {
        "research": "Explore, gather information, and report clear findings. Use appropriate thoroughness level.",
        "plan": "Analyze the task, break it down, identify risks and dependencies. Present a clear plan.",
        "design": "Review the context and design the approach. Consider trade-offs and long-term impact.",
        "create": "Implement the work based on the plan and previous findings. Write tests if applicable. Use tools to modify files.",
        "review": "Review the quality, catch bugs, check for completeness. Report severity levels.",
        "coordinator": "Coordinate the team and synthesize results.",
    }
    return (
        f"You are phase {phase_idx + 1} of {total_phases} in a workflow.\n\n"
        f"Overall task: {task}\n\n"
        f"Your job: {instructions.get(cat, 'Execute your specialty on the task.')}\n\n"
        f"Important: Use kimi-cli tools directly. Do not ask clarifying questions unless critical information is missing."
    )


def _recommend_timeout(agent: str, task: str, team_id: str | None = None) -> int:
    """Recommend timeout based on agent category and task length."""
    cat = _get_agent_category(agent, team_id)
    base = _CATEGORY_TIMEOUTS.get(cat, 300)
    # Heuristic: very long tasks may need more time
    words = len(task.split())
    if words > 50:
        base += 300
    return min(base, 3600)


def _can_background(agent: str, team_id: str | None = None) -> bool:
    """Determine if this agent's phase can run in background."""
    cat = _get_agent_category(agent, team_id)
    return cat in _BACKGROUND_CATEGORIES


def generate_workflow_plan(
    task: str,
    workflow_type: str = "auto",
    work_dir: str = ".",
    team_id: str | None = None,
) -> dict:
    """
    Generate a workflow plan for Kamaji to execute.

    Returns a JSON dict with phases and execution recommendations.
    """
    if not task:
        return {"success": False, "error": "Missing required parameter: task"}

    team = _get_team(team_id)
    effective_team = team.id if team else (team_id or "coding")

    # Analyze task
    if workflow_type == "auto":
        analysis = _heuristic_analysis(task)
        complexity = analysis["complexity"]
        # Map complexity to a workflow type
        if team:
            patterns = list(team.workflow_patterns.keys())
            if complexity == "simple":
                workflow_type = "quick" if "quick" in patterns else patterns[0]
            elif complexity == "complex":
                workflow_type = "feature" if "feature" in patterns else patterns[0]
            else:
                workflow_type = "bugfix" if "bugfix" in patterns else patterns[0]
        else:
            workflow_type = (
                "quick"
                if complexity == "simple"
                else ("feature" if complexity == "complex" else "bugfix")
            )
    else:
        analysis = _heuristic_analysis(task)
        complexity = "unknown"

    # Validate workflow_type exists for this team
    if team and workflow_type not in team.workflow_patterns:
        available = list(team.workflow_patterns.keys())
        return {
            "success": False,
            "error": (
                f"Unknown workflow_type '{workflow_type}' for team '{effective_team}'. "
                f"Available: {available}"
            ),
        }

    # Get workflow pattern
    pattern = _get_workflow_pattern(workflow_type, team_id)

    # Compute parallel batches
    parallel_steps = _compute_parallel_steps(pattern, team_id)

    # Build phases
    phases: list[WorkflowPhase] = []
    for idx, step in enumerate(pattern):
        phase = WorkflowPhase(
            agent=step["agent"],
            description=step["description"],
            prompt=_build_phase_prompt(step["agent"], task, idx, len(pattern), team_id),
            subagent_type=_map_agent_to_subagent_type(step["agent"]),
            can_background=_can_background(step["agent"], team_id),
            recommended_timeout=_recommend_timeout(step["agent"], task, team_id),
            resume=_resolve_resume(pattern, idx),
            model=_recommend_model(step["agent"]),
        )
        phases.append(phase)

    # Determine if plan mode should be used
    if workflow_type in ("feature", "refactor", "series", "deep_dive") and len(phases) > 2:
        use_plan_mode = True
        plan_mode_reason = (
            f"This is a {complexity} {workflow_type} task with {len(phases)} phases. "
            "Using plan mode helps ensure a clear roadmap before execution."
        )
    elif complexity == "simple" and len(phases) <= 2:
        use_plan_mode = False
        plan_mode_reason = "Task is simple and can be executed directly without plan mode."
    else:
        use_plan_mode = False
        plan_mode_reason = "Plan mode is optional for this task; disable for faster execution."

    output_lines = [
        f"Workflow plan generated: {workflow_type}",
        f"Team: {effective_team}",
        f"Complexity: {complexity}",
        f"Phases: {len(phases)}",
        f"Parallel batches: {len(parallel_steps)}",
        "",
    ]
    for batch_idx, batch in enumerate(parallel_steps, 1):
        if len(batch) == 1:
            phase = phases[batch[0]]
            output_lines.append(f"{batch_idx}. {phase.agent} → {phase.description}")
        else:
            agents = " + ".join(phases[i].agent for i in batch)
            output_lines.append(f"{batch_idx}. [{agents}] (parallel)")

    # Build todo items when there are multiple phases
    todo_items: list[dict[str, str]] | None = None
    if len(phases) > 1:
        todo_items = [{"title": f"{p.agent}: {p.description}", "status": "pending"} for p in phases]

    # Recommend a plan file path for plan-mode tasks
    plan_file_path: str | None = None
    if use_plan_mode:
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_task = "".join(c if c.isalnum() else "_" for c in task[:30]).strip("_")
        plan_file_path = str(
            Path.home()
            / ".kimi"
            / "plans"
            / f"{effective_team}_{workflow_type}_{safe_task}_{timestamp}.md"
        )

    plan = WorkflowPlan(
        success=True,
        workflow_type=workflow_type,
        team=effective_team,
        task=task,
        work_dir=work_dir,
        complexity=complexity,
        phases=phases,
        parallel_batches=parallel_steps,
        recommendations={
            "use_plan_mode": use_plan_mode,
            "plan_mode_reason": plan_mode_reason,
            "use_todo_list": len(phases) > 1,
            "parallel_steps": parallel_steps,
            "estimated_duration": f"{len(phases) * 1}-{len(phases) * 4} min",
        },
        output="\n".join(output_lines),
        todo_items=todo_items,
        plan_file_path=plan_file_path,
    )

    return plan.to_dict()


def main():
    """Main entry point - reads JSON from stdin, outputs JSON to stdout."""
    params = {}
    if not sys.stdin.isatty():
        with contextlib.suppress(json.JSONDecodeError):
            params = json.load(sys.stdin)

    task = params.get("task", "")
    workflow_type = params.get("workflow_type", "auto")
    work_dir = params.get("work_dir", ".")
    team_id = params.get("team")

    result = generate_workflow_plan(task, workflow_type, work_dir, team_id)

    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
