"""Workflow execution engine for structured multi-agent orchestration.

This module provides deterministic execution planning for Kamaji.
It does NOT invoke native tools directly (plugins run in subprocess),
but returns precise instructions that Kamaji must follow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kimi_tachi.orchestrator.plan import WorkflowPlan


@dataclass
class ExecutionState:
    """Mutable execution state tracked across executor calls."""

    completed_phase_indices: list[int] = field(default_factory=list)
    agent_ids: dict[str, str] = field(default_factory=dict)
    background_tasks: list[str] = field(default_factory=list)
    current_batch_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "completed_phase_indices": self.completed_phase_indices,
            "agent_ids": self.agent_ids,
            "background_tasks": self.background_tasks,
            "current_batch_index": self.current_batch_index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionState:
        return cls(
            completed_phase_indices=list(data.get("completed_phase_indices", [])),
            agent_ids=dict(data.get("agent_ids", {})),
            background_tasks=list(data.get("background_tasks", [])),
            current_batch_index=int(data.get("current_batch_index", 0)),
        )


@dataclass
class SpawnInstruction:
    """Instruction to spawn a single agent for a phase."""

    phase_index: int
    agent: str
    description: str
    prompt: str
    subagent_type: str
    model: str | None
    timeout: int
    run_in_background: bool
    resume: str | None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "phase_index": self.phase_index,
            "agent": self.agent,
            "description": self.description,
            "prompt": self.prompt,
            "subagent_type": self.subagent_type,
            "timeout": self.timeout,
            "run_in_background": self.run_in_background,
            "resume": self.resume,
        }
        if self.model is not None:
            result["model"] = self.model
        return result


@dataclass
class ExecutionResult:
    """Result returned by the executor to Kamaji."""

    action: str  # "spawn", "wait", "complete", "error"
    spawn: list[SpawnInstruction] = field(default_factory=list)
    wait_tasks: list[str] = field(default_factory=list)
    todo_updates: list[dict[str, str]] = field(default_factory=list)
    message: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "action": self.action,
            "message": self.message,
        }
        if self.spawn:
            result["spawn"] = [s.to_dict() for s in self.spawn]
        if self.wait_tasks:
            result["wait_tasks"] = self.wait_tasks
        if self.todo_updates:
            result["todo_updates"] = self.todo_updates
        if self.error is not None:
            result["error"] = self.error
        return result


def _compute_todo_updates(
    plan: WorkflowPlan,
    state: ExecutionState,
    next_phase_indices: list[int],
) -> list[dict[str, str]]:
    """Compute todo list statuses for the current execution step."""
    if not plan.todo_items:
        return []

    updates: list[dict[str, str]] = []
    for i, item in enumerate(plan.todo_items):
        if i in state.completed_phase_indices:
            status = "done"
        elif i in next_phase_indices:
            status = "in_progress"
        else:
            status = "pending"
        updates.append({"title": item["title"], "status": status})
    return updates


def _resolve_resume_for_phase(
    plan: WorkflowPlan,
    state: ExecutionState,
    phase_index: int,
) -> str | None:
    """Determine resume agent_id for a phase based on execution state.

    Resume is used when the same agent appears consecutively in the workflow
    and the previous phase was already executed (agent_id is known).
    """
    if phase_index <= 0:
        return None

    prev_idx = phase_index - 1
    prev_phase = plan.phases[prev_idx]
    current_phase = plan.phases[phase_index]

    # Only resume if same agent and previous phase was completed
    if prev_phase.agent != current_phase.agent:
        return None

    if prev_idx not in state.completed_phase_indices:
        return None

    key = str(prev_idx)
    return state.agent_ids.get(key)


def execute_workflow(
    plan: WorkflowPlan,
    state: ExecutionState,
) -> ExecutionResult:
    """Compute the next execution step for a workflow plan.

    This is a pure function that inspects the plan and current execution state,
    then returns instructions for Kamaji to carry out.
    """
    if not plan.success:
        return ExecutionResult(
            action="error",
            error=plan.error or "Workflow plan was not successful",
        )

    if not plan.phases:
        return ExecutionResult(
            action="complete",
            message="Workflow has no phases to execute.",
        )

    total_batches = len(plan.parallel_batches)

    # If we have pending background tasks, wait for them before proceeding.
    # Background tasks always belong to a previous batch, and subsequent batches
    # may depend on their results, so we must block here.
    if state.background_tasks:
        todo_updates = _compute_todo_updates(plan, state, [])
        return ExecutionResult(
            action="wait",
            wait_tasks=list(state.background_tasks),
            todo_updates=todo_updates,
            message=(
                f"Waiting for {len(state.background_tasks)} background task(s) "
                f"to complete before proceeding."
            ),
        )

    # If we've processed all batches, the workflow is complete.
    if state.current_batch_index >= total_batches:
        todo_updates = _compute_todo_updates(plan, state, [])
        return ExecutionResult(
            action="complete",
            todo_updates=todo_updates,
            message="All workflow phases completed successfully.",
        )

    # Get the current batch of phases
    batch = plan.parallel_batches[state.current_batch_index]
    spawn_instructions: list[SpawnInstruction] = []
    next_phase_indices: list[int] = []

    for phase_index in batch:
        if phase_index in state.completed_phase_indices:
            continue

        phase = plan.phases[phase_index]
        resume = _resolve_resume_for_phase(plan, state, phase_index)

        spawn_instructions.append(
            SpawnInstruction(
                phase_index=phase_index,
                agent=phase.agent,
                description=phase.description,
                prompt=phase.prompt,
                subagent_type=phase.subagent_type,
                model=phase.model,
                timeout=phase.recommended_timeout,
                run_in_background=phase.can_background,
                resume=resume,
            )
        )
        next_phase_indices.append(phase_index)

    # If every phase in this batch is already completed, advance and recurse
    if not spawn_instructions:
        state.current_batch_index += 1
        return execute_workflow(plan, state)

    todo_updates = _compute_todo_updates(plan, state, next_phase_indices)

    if len(spawn_instructions) == 1:
        msg = (
            f"Spawn {spawn_instructions[0].agent} for batch {state.current_batch_index} "
            f"(phase {spawn_instructions[0].phase_index})"
        )
    else:
        agents = ", ".join(s.agent for s in spawn_instructions)
        msg = f"Spawn {len(spawn_instructions)} agents in parallel for batch {state.current_batch_index}: {agents}"

    return ExecutionResult(
        action="spawn",
        spawn=spawn_instructions,
        todo_updates=todo_updates,
        message=msg,
    )
