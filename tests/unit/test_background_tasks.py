"""Tests for BackgroundTaskManager"""

import asyncio

import pytest

from kimi_tachi.background import BackgroundTaskManager, TaskInfo, TaskStatus


class TestBackgroundTaskManager:
    """Test BackgroundTaskManager functionality"""

    def setup_method(self):
        """Create fresh task manager for each test"""
        self.manager = BackgroundTaskManager()

    @pytest.mark.asyncio
    async def test_register_task(self):
        """Test registering a background task"""
        task = self.manager.register_task(
            agent_type="nekobasu",
            description="Test exploration",
            prompt="Find all Python files",
        )

        assert task.task_id.startswith("task_")
        assert task.agent_type == "nekobasu"
        assert task.description == "Test exploration"
        assert task.status == TaskStatus.PENDING
        assert task.agent_id.startswith("a")

    @pytest.mark.asyncio
    async def test_task_lifecycle(self):
        """Test complete task lifecycle with explicit completion"""
        # Register task
        task = self.manager.register_task(
            agent_type="calcifer",
            description="Test implementation",
            prompt="Write a function",
        )

        task_id = task.task_id

        # Mark running
        assert self.manager.mark_running(task_id) is True
        updated = self.manager.get_task(task_id)
        assert updated.status == TaskStatus.RUNNING

        # Mark complete
        assert self.manager.mark_complete(task_id, result="Done!") is True
        updated = self.manager.get_task(task_id)
        assert updated.status == TaskStatus.COMPLETED
        assert updated.is_complete is True
        assert updated.result == "Done!"
        assert updated.duration > 0

    def test_get_task(self):
        """Test retrieving task by ID"""
        # Non-existent task
        assert self.manager.get_task("nonexistent") is None

        task = self.manager.register_task("nekobasu", "Task", "Prompt")
        assert self.manager.get_task(task.task_id) is not None

    @pytest.mark.asyncio
    async def test_list_tasks(self):
        """Test listing tasks with filters"""
        # Create some tasks
        task1 = self.manager.register_task("nekobasu", "Task 1", "Prompt 1")
        task2 = self.manager.register_task("calcifer", "Task 2", "Prompt 2")
        self.manager.register_task("nekobasu", "Task 3", "Prompt 3")

        # Complete two, leave one pending
        self.manager.mark_complete(task1.task_id)
        self.manager.mark_complete(task2.task_id)

        # List all
        all_tasks = self.manager.list_tasks()
        assert len(all_tasks) == 3

        # Filter by type
        nekobasu_tasks = self.manager.list_tasks(agent_type="nekobasu")
        assert len(nekobasu_tasks) == 2

        calcifer_tasks = self.manager.list_tasks(agent_type="calcifer")
        assert len(calcifer_tasks) == 1

        # Filter by status
        completed = self.manager.list_tasks(status=TaskStatus.COMPLETED)
        assert len(completed) == 2

        pending = self.manager.list_tasks(status=TaskStatus.PENDING)
        assert len(pending) == 1

    @pytest.mark.asyncio
    async def test_list_active_tasks(self):
        """Test listing active tasks"""
        # Create tasks
        task1 = self.manager.register_task("nekobasu", "Active task", "Do something")
        task2 = self.manager.register_task("calcifer", "Completed task", "Work")
        self.manager.mark_complete(task2.task_id)

        active = self.manager.list_active_tasks()
        assert len(active) == 1
        assert active[0].task_id == task1.task_id

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test cancelling a task"""
        # Create task
        task = self.manager.register_task("nekobasu", "Cancellable", "Work")
        task_id = task.task_id

        # Cancel immediately
        success = self.manager.cancel_task(task_id)
        assert success is True
        updated = self.manager.get_task(task_id)
        assert updated.status == TaskStatus.CANCELLED

        # Cancel non-existent
        assert self.manager.cancel_task("nonexistent") is False

        # Cancel already complete
        task2 = self.manager.register_task("nekobasu", "Task 2", "Work")
        self.manager.mark_complete(task2.task_id)
        assert self.manager.cancel_task(task2.task_id) is False

    @pytest.mark.asyncio
    async def test_mark_failed(self):
        """Test marking a task as failed"""
        task = self.manager.register_task("calcifer", "Failing task", "Work")
        assert self.manager.mark_failed(task.task_id, error="Something went wrong") is True
        updated = self.manager.get_task(task.task_id)
        assert updated.status == TaskStatus.FAILED
        assert updated.error == "Something went wrong"

    @pytest.mark.asyncio
    async def test_progress_tracking(self):
        """Test progress updates"""
        task = self.manager.register_task("nekobasu", "Progress task", "Work")
        assert self.manager.mark_progress(task.task_id, 0.5) is True
        updated = self.manager.get_task(task.task_id)
        assert updated.progress == 0.5

        # Completed task should reject progress updates
        self.manager.mark_complete(task.task_id)
        assert self.manager.mark_progress(task.task_id, 0.9) is False

    def test_get_stats(self):
        """Test statistics collection"""
        stats = self.manager.get_stats()
        assert stats["total"] == 0
        assert stats["active"] == 0

        t1 = self.manager.register_task("nekobasu", "T1", "P1")
        self.manager.register_task("calcifer", "T2", "P2")
        self.manager.mark_complete(t1.task_id)

        stats = self.manager.get_stats()
        assert stats["total"] == 2
        assert stats["active"] == 1
        assert stats["by_type"]["nekobasu"] == 1
        assert stats["by_type"]["calcifer"] == 1

    @pytest.mark.asyncio
    async def test_wait_for_task(self):
        """Test waiting for task completion"""
        task = self.manager.register_task("nekobasu", "Wait task", "Prompt")

        # Complete after a short delay
        async def complete_later():
            await asyncio.sleep(0.2)
            self.manager.mark_complete(task.task_id)

        asyncio.create_task(complete_later())
        result = await self.manager.wait_for_task(task.task_id, timeout=5.0)
        assert result is not None
        assert result.status == TaskStatus.COMPLETED

    def test_cleanup_completed(self):
        """Test cleaning up old completed tasks"""
        t1 = self.manager.register_task("nekobasu", "Old", "P1")
        t2 = self.manager.register_task("calcifer", "Recent", "P2")
        self.manager.mark_complete(t1.task_id)
        self.manager.mark_complete(t2.task_id)

        # Manually backdate t1
        self.manager.get_task(t1.task_id).completed_at = 0.0

        cleaned = self.manager.cleanup_completed(max_age=1)
        assert cleaned == 1
        assert self.manager.get_task(t1.task_id) is None
        assert self.manager.get_task(t2.task_id) is not None

    @pytest.mark.asyncio
    async def test_callbacks(self):
        """Test completion callbacks"""
        called_with = []

        def callback(task: TaskInfo):
            called_with.append(task.task_id)

        task = self.manager.register_task(
            "nekobasu", "Callback task", "Prompt", on_complete=callback
        )
        self.manager.mark_complete(task.task_id)

        assert task.task_id in called_with
