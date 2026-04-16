"""Workflow plan models for structured multi-agent orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class WorkflowPhase:
    """A single phase in a multi-agent workflow."""

    agent: str
    description: str
    prompt: str
    subagent_type: str
    can_background: bool
    recommended_timeout: int
    resume: str | None = None
    model: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        result = {
            "agent": self.agent,
            "description": self.description,
            "prompt": self.prompt,
            "subagent_type": self.subagent_type,
            "can_background": self.can_background,
            "recommended_timeout": self.recommended_timeout,
            "resume": self.resume,
        }
        if self.model is not None:
            result["model"] = self.model
        return result


@dataclass
class WorkflowPlan:
    """A structured workflow plan for native Agent() execution."""

    success: bool
    workflow_type: str
    team: str
    task: str
    work_dir: str
    complexity: str
    phases: list[WorkflowPhase]
    parallel_batches: list[list[int]]
    recommendations: dict[str, Any]
    output: str
    todo_items: list[dict[str, str]] | None = None
    plan_file_path: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        result: dict[str, Any] = {
            "success": self.success,
            "workflow_type": self.workflow_type,
            "team": self.team,
            "task": self.task,
            "work_dir": str(Path(self.work_dir).resolve()),
            "complexity": self.complexity,
            "phases": [p.to_dict() for p in self.phases],
            "recommendations": self.recommendations,
            "output": self.output,
        }
        if self.todo_items is not None:
            result["todo_items"] = self.todo_items
        if self.plan_file_path is not None:
            result["plan_file_path"] = self.plan_file_path
        if self.error is not None:
            result["error"] = self.error
        return result

    def execution_batches(self) -> list[list[WorkflowPhase]]:
        """Return phases grouped into execution batches.

        Each batch contains phases that can run in parallel.
        """
        return [[self.phases[idx] for idx in batch] for batch in self.parallel_batches]
