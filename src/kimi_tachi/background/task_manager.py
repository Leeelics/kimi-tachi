"""
Background Task Registry

Tracks background agent task metadata for coordination purposes.

NOTE: Actual background agent execution is performed by kimi-cli's native
Agent tool with run_in_background=True. This module provides local
task bookkeeping only.

Example:
    manager = BackgroundTaskManager()
    task = manager.register_task(
        agent_type="nekobasu",
        description="Deep codebase analysis",
        prompt="Analyze the entire codebase architecture...",
    )
    # Later, when the native background task completes:
    manager.mark_complete(task.task_id, result="...")
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class TaskStatus(Enum):
    """Status of a background task"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """Information about a background task"""

    task_id: str
    agent_id: str
    agent_type: str
    description: str
    status: TaskStatus
    created_at: float
    started_at: float | None = None
    completed_at: float | None = None
    result: str | None = None
    error: str | None = None
    progress: float = 0.0  # 0.0 to 1.0
    timeout: int | None = None  # Timeout in seconds (30-3600)

    @property
    def duration(self) -> float:
        """Get task duration in seconds"""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return time.time() - self.started_at
        return 0.0

    @property
    def is_complete(self) -> bool:
        """Check if task is complete (success or failure)"""
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": self.duration,
            "progress": self.progress,
            "has_result": self.result is not None,
            "error": self.error,
        }


class BackgroundTaskManager:
    """
    Local registry for background task metadata.

    This class does NOT execute agents. It tracks task state for
    coordination with kimi-cli's native background Agent execution.
    """

    def __init__(self):
        self._tasks: dict[str, TaskInfo] = {}
        self._callbacks: dict[str, list[Callable[[TaskInfo], None]]] = {}

    def register_task(
        self,
        agent_type: str,
        description: str,
        prompt: str,
        task_id: str | None = None,
        timeout: int | None = None,
        on_complete: Callable[[TaskInfo], None] | None = None,
    ) -> TaskInfo:
        """
        Register a background task locally.

        The actual agent execution must be triggered via kimi-cli's
        native Agent tool with run_in_background=True.
        """
        actual_task_id = task_id or f"task_{uuid.uuid4().hex[:8]}"
        agent_id = f"a{uuid.uuid4().hex[:8]}"

        if timeout is not None:
            timeout = max(30, min(3600, timeout))

        task = TaskInfo(
            task_id=actual_task_id,
            agent_id=agent_id,
            agent_type=agent_type,
            description=description,
            status=TaskStatus.PENDING,
            created_at=time.time(),
            timeout=timeout,
        )

        self._tasks[actual_task_id] = task

        if on_complete:
            self._callbacks.setdefault(actual_task_id, []).append(on_complete)

        return task

    # Legacy alias for backward compatibility
    start_task = register_task

    def mark_running(self, task_id: str) -> bool:
        """Mark a task as running."""
        task = self._tasks.get(task_id)
        if not task or task.is_complete:
            return False
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        return True

    def mark_progress(self, task_id: str, progress: float) -> bool:
        """Update task progress (0.0 to 1.0)."""
        task = self._tasks.get(task_id)
        if not task or task.is_complete:
            return False
        task.progress = max(0.0, min(1.0, progress))
        return True

    def mark_complete(self, task_id: str, result: str = "") -> bool:
        """Mark a task as completed."""
        task = self._tasks.get(task_id)
        if not task or task.is_complete:
            return False
        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.result = result
        task.progress = 1.0
        self._trigger_callbacks(task)
        return True

    def mark_failed(self, task_id: str, error: str = "") -> bool:
        """Mark a task as failed."""
        task = self._tasks.get(task_id)
        if not task or task.is_complete:
            return False
        task.status = TaskStatus.FAILED
        task.completed_at = time.time()
        task.error = error
        self._trigger_callbacks(task)
        return True

    def _trigger_callbacks(self, task: TaskInfo) -> None:
        """Trigger completion callbacks for a task"""
        callbacks = self._callbacks.get(task.task_id, [])
        for callback in callbacks:
            try:
                if callable(callback):
                    callback(task)
            except Exception as e:
                print(f"Callback error for task {task.task_id}: {e}")

    def get_task(self, task_id: str) -> TaskInfo | None:
        """Get task information by ID"""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        agent_type: str | None = None,
    ) -> list[TaskInfo]:
        """List tasks with optional filtering."""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        if agent_type:
            tasks = [t for t in tasks if t.agent_type == agent_type]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def list_active_tasks(self) -> list[TaskInfo]:
        """List all active (pending or running) tasks"""
        return self.list_tasks(status=TaskStatus.RUNNING) + self.list_tasks(
            status=TaskStatus.PENDING
        )

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task."""
        task = self._tasks.get(task_id)
        if not task or task.is_complete:
            return False
        task.status = TaskStatus.CANCELLED
        task.completed_at = time.time()
        return True

    def get_stats(self) -> dict:
        """Get statistics about all tasks"""
        total = len(self._tasks)
        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}

        for task in self._tasks.values():
            by_status[task.status.value] = by_status.get(task.status.value, 0) + 1
            by_type[task.agent_type] = by_type.get(task.agent_type, 0) + 1

        active = by_status.get(TaskStatus.PENDING.value, 0) + by_status.get(
            TaskStatus.RUNNING.value, 0
        )

        return {
            "total": total,
            "active": active,
            "by_status": by_status,
            "by_type": by_type,
        }

    def cleanup_completed(self, max_age: float = 3600) -> int:
        """Remove completed tasks older than max_age seconds."""
        cutoff = time.time() - max_age
        to_remove = [
            tid
            for tid, task in self._tasks.items()
            if task.is_complete and task.completed_at is not None and task.completed_at < cutoff
        ]
        for tid in to_remove:
            del self._tasks[tid]
            self._callbacks.pop(tid, None)
        return len(to_remove)

    async def wait_for_task(self, task_id: str, timeout: float | None = None) -> TaskInfo | None:
        """
        Wait for a task to complete.

        This is a simple polling wait since actual execution is handled
        by kimi-cli's native background Agent tool.
        """
        import asyncio

        start = asyncio.get_event_loop().time()
        while True:
            task = self.get_task(task_id)
            if task is None:
                return None
            if task.is_complete:
                return task
            if timeout is not None and (asyncio.get_event_loop().time() - start) > timeout:
                return task
            await asyncio.sleep(0.1)
