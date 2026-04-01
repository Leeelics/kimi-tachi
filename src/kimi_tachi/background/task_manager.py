"""
Background Task Manager

Manages asynchronous task execution using kimi-cli 1.25.0+'s background task support.
This allows long-running operations (like full codebase analysis) to run without
blocking the main interaction.

Example:
    # Start a background task
    task = await manager.start_task(
        agent_type="nekobasu",
        description="Deep codebase analysis",
        prompt="Analyze the entire codebase architecture...",
    )

    # Continue with other work...

    # Check status later
    status = manager.get_task_status(task.task_id)
    if status.is_complete:
        result = status.result
"""

from __future__ import annotations

import asyncio
import time
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
    timeout: int | None = None  # Timeout in seconds (30-3600, kimi-cli 1.28.0+)

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
    Manages background task execution.

    This class provides a high-level interface for running agents asynchronously,
    tracking their progress, and retrieving results when complete.
    """

    def __init__(self):
        self._tasks: dict[str, TaskInfo] = {}
        self._callbacks: dict[str, list[Callable[[TaskInfo], None]]] = {}
        self._monitoring: bool = False
        self._monitor_task: asyncio.Task | None = None

    async def start_task(
        self,
        agent_type: str,
        description: str,
        prompt: str,
        task_id: str | None = None,
        timeout: int | None = None,
        on_complete: Callable[[TaskInfo], None] | None = None,
    ) -> TaskInfo:
        """
        Start a background task.

        In a real implementation, this would use the Agent tool with
        run_in_background=True. For now, we simulate the behavior.

        Args:
            agent_type: The subagent type (nekobasu, calcifer, etc.)
            description: Short description of the task
            prompt: The task prompt
            task_id: Optional custom task ID
            timeout: Optional timeout in seconds (30-3600, kimi-cli 1.28.0+)
            on_complete: Optional callback when task completes

        Returns:
            TaskInfo for the started task

        Note:
            Timeout feature requires kimi-cli >=1.28.0.
            The agent will be stopped if it exceeds the timeout.
        """
        # Generate IDs
        import uuid

        actual_task_id = task_id or f"task_{uuid.uuid4().hex[:8]}"
        agent_id = f"a{uuid.uuid4().hex[:8]}"

        # Validate timeout (kimi-cli 1.28.0+: 30-3600 seconds)
        if timeout is not None:
            timeout = max(30, min(3600, timeout))

        # Create task info
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

        # In real implementation, this would call:
        # Agent(
        #     description=description,
        #     prompt=prompt,
        #     subagent_type=agent_type,
        #     run_in_background=True,
        #     timeout=timeout,  # kimi-cli 1.28.0+
        # )
        # For now, simulate starting the task
        asyncio.create_task(self._simulate_task_execution(actual_task_id, prompt, timeout))

        return task

    async def _simulate_task_execution(self, task_id: str, prompt: str, timeout: int | None = None):
        """Simulate task execution (replace with actual Agent tool call)"""
        task = self._tasks.get(task_id)
        if not task:
            return

        # Mark as running
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()

        # Simulate work (in reality, this would be the background agent running)
        try:
            # Apply timeout if specified (kimi-cli 1.28.0+)
            if timeout:
                # Simulate work with timeout
                for i in range(10):
                    await asyncio.sleep(0.1)  # Replace with actual work
                    task.progress = (i + 1) / 10
                    # Check if we would exceed timeout
                    if task.started_at and (time.time() - task.started_at) > timeout:
                        raise TimeoutError(f"Task timed out after {timeout}s")
            else:
                # Simulate progress updates without timeout
                for i in range(10):
                    await asyncio.sleep(0.1)  # Replace with actual work
                    task.progress = (i + 1) / 10

            # Mark complete
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            task.result = f"Completed: {prompt[:50]}..."

        except TimeoutError as e:
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            task.error = f"Timeout: {str(e)}"

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            task.error = str(e)

        # Trigger callbacks
        await self._trigger_callbacks(task)

    async def _trigger_callbacks(self, task: TaskInfo):
        """Trigger completion callbacks for a task"""
        callbacks = self._callbacks.get(task.task_id, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
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
        """
        List tasks with optional filtering.

        Args:
            status: Filter by status
            agent_type: Filter by agent type

        Returns:
            List of matching TaskInfo objects
        """
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
        """
        Cancel a pending or running task.

        Args:
            task_id: The task ID to cancel

        Returns:
            True if cancelled, False if not found or already complete
        """
        task = self._tasks.get(task_id)
        if not task or task.is_complete:
            return False

        task.status = TaskStatus.CANCELLED
        task.completed_at = time.time()
        return True

    def get_stats(self) -> dict:
        """Get statistics about all tasks"""
        total = len(self._tasks)
        by_status = dict.fromkeys(TaskStatus, 0)
        by_type: dict[str, int] = {}

        for task in self._tasks.values():
            by_status[task.status] = by_status.get(task.status, 0) + 1
            by_type[task.agent_type] = by_type.get(task.agent_type, 0) + 1

        active = by_status[TaskStatus.PENDING] + by_status[TaskStatus.RUNNING]

        return {
            "total": total,
            "active": active,
            "completed": by_status[TaskStatus.COMPLETED],
            "failed": by_status[TaskStatus.FAILED],
            "cancelled": by_status[TaskStatus.CANCELLED],
            "by_type": by_type,
        }

    def cleanup_completed(self, max_age_seconds: float = 3600) -> int:
        """
        Remove completed tasks older than max_age_seconds.

        Returns:
            Number of tasks removed
        """
        now = time.time()
        to_remove = [
            tid
            for tid, task in self._tasks.items()
            if task.is_complete
            and task.completed_at
            and (now - task.completed_at) > max_age_seconds
        ]

        for tid in to_remove:
            del self._tasks[tid]
            self._callbacks.pop(tid, None)

        return len(to_remove)

    async def wait_for_task(
        self,
        task_id: str,
        timeout: float | None = None,
        poll_interval: float = 1.0,
    ) -> TaskInfo | None:
        """
        Wait for a task to complete.

        Args:
            task_id: The task ID to wait for
            timeout: Maximum time to wait (None for no timeout)
            poll_interval: How often to check status

        Returns:
            TaskInfo if complete, None if timeout or not found
        """
        start_time = time.time()

        while True:
            task = self._tasks.get(task_id)
            if not task:
                return None

            if task.is_complete:
                return task

            if timeout and (time.time() - start_time) > timeout:
                return None

            await asyncio.sleep(poll_interval)


# Global task manager instance
_task_manager: BackgroundTaskManager | None = None


def get_task_manager() -> BackgroundTaskManager:
    """Get or create the global task manager"""
    global _task_manager
    if _task_manager is None:
        _task_manager = BackgroundTaskManager()
    return _task_manager


def reset_task_manager():
    """Reset the global task manager (useful for testing)"""
    global _task_manager
    _task_manager = None
