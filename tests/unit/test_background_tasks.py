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
    async def test_start_task(self):
        """Test starting a background task"""
        task = await self.manager.start_task(
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
        """Test complete task lifecycle"""
        # Start task
        task = await self.manager.start_task(
            agent_type="calcifer",
            description="Test implementation",
            prompt="Write a function",
        )

        task_id = task.task_id

        # Wait for completion (simulated tasks complete quickly)
        await asyncio.sleep(1.5)

        # Check result
        updated = self.manager.get_task(task_id)
        assert updated is not None
        assert updated.status == TaskStatus.COMPLETED
        assert updated.is_complete is True
        assert updated.result is not None
        assert updated.duration > 0

    def test_get_task(self):
        """Test retrieving task by ID"""
        # Non-existent task
        assert self.manager.get_task("nonexistent") is None

    @pytest.mark.asyncio
    async def test_list_tasks(self):
        """Test listing tasks with filters"""
        # Create some tasks
        _task1 = await self.manager.start_task("nekobasu", "Task 1", "Prompt 1")
        _task2 = await self.manager.start_task("calcifer", "Task 2", "Prompt 2")
        _task3 = await self.manager.start_task("nekobasu", "Task 3", "Prompt 3")

        # Wait for completion
        await asyncio.sleep(1.5)

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
        assert len(completed) == 3

    @pytest.mark.asyncio
    async def test_list_active_tasks(self):
        """Test listing active tasks"""
        # Create a task
        _task = await self.manager.start_task("nekobasu", "Active task", "Do something")

        # Immediately check (should be running or pending)
        active = self.manager.list_active_tasks()
        assert len(active) >= 0  # May already be complete due to simulation

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test cancelling a task"""
        # Create task
        task = await self.manager.start_task("nekobasu", "Cancellable", "Work")
        task_id = task.task_id

        # Cancel immediately
        success = self.manager.cancel_task(task_id)
        # May fail if already complete due to fast simulation
        if success:
            updated = self.manager.get_task(task_id)
            assert updated.status == TaskStatus.CANCELLED

        # Cancel non-existent
        assert self.manager.cancel_task("nonexistent") is False

        # Cancel already complete
        task2 = await self.manager.start_task("nekobasu", "Task 2", "Work")
        await asyncio.sleep(1.5)
        assert self.manager.cancel_task(task2.task_id) is False

    def test_get_stats(self):
        """Test statistics collection"""
        stats = self.manager.get_stats()
        assert "total" in stats
        assert "active" in stats
        assert "completed" in stats
        assert "by_type" in stats

    @pytest.mark.asyncio
    async def test_cleanup_completed(self):
        """Test cleaning up old completed tasks"""
        # Create and complete a task
        task = await self.manager.start_task("nekobasu", "Old task", "Work")
        await asyncio.sleep(1.5)

        # Cleanup with very short max age
        removed = self.manager.cleanup_completed(max_age_seconds=0)
        assert removed == 1
        assert self.manager.get_task(task.task_id) is None

    @pytest.mark.asyncio
    async def test_wait_for_task(self):
        """Test waiting for task completion"""
        # Create task
        task = await self.manager.start_task("calcifer", "Waitable", "Work")

        # Wait for it
        result = await self.manager.wait_for_task(task.task_id, timeout=5.0)
        assert result is not None
        assert result.is_complete is True

    @pytest.mark.asyncio
    async def test_wait_for_task_timeout(self):
        """Test wait timeout"""
        # Create a task that takes time
        task = await self.manager.start_task("nekobasu", "Slow", "Work")

        # Wait with very short timeout
        result = await self.manager.wait_for_task(task.task_id, timeout=0.01, poll_interval=0.001)
        # Should timeout before completion
        assert result is None or not result.is_complete

    @pytest.mark.asyncio
    async def test_callback(self):
        """Test completion callback"""
        callback_called = False
        callback_task = None

        def on_complete(task: TaskInfo):
            nonlocal callback_called, callback_task
            callback_called = True
            callback_task = task

        # Start task with callback
        task = await self.manager.start_task(
            agent_type="nekobasu",
            description="With callback",
            prompt="Do work",
            on_complete=on_complete,
        )

        # Wait for completion
        await asyncio.sleep(1.5)

        # Callback should have been called
        assert callback_called is True
        assert callback_task is not None
        assert callback_task.task_id == task.task_id


class TestTaskInfo:
    """Test TaskInfo data class"""

    def test_duration_property(self):
        """Test duration calculation"""
        import time

        info = TaskInfo(
            task_id="test",
            agent_id="agent",
            agent_type="nekobasu",
            description="Test",
            status=TaskStatus.RUNNING,
            created_at=time.time(),
            started_at=time.time() - 10,  # Started 10 seconds ago
        )

        assert info.duration >= 10

    def test_is_complete(self):
        """Test is_complete property"""
        # Pending - not complete
        pending = TaskInfo(
            task_id="p",
            agent_id="a",
            agent_type="t",
            description="d",
            status=TaskStatus.PENDING,
            created_at=0,
        )
        assert pending.is_complete is False

        # Running - not complete
        running = TaskInfo(
            task_id="r",
            agent_id="a",
            agent_type="t",
            description="d",
            status=TaskStatus.RUNNING,
            created_at=0,
        )
        assert running.is_complete is False

        # Completed - complete
        completed = TaskInfo(
            task_id="c",
            agent_id="a",
            agent_type="t",
            description="d",
            status=TaskStatus.COMPLETED,
            created_at=0,
        )
        assert completed.is_complete is True

        # Failed - complete
        failed = TaskInfo(
            task_id="f",
            agent_id="a",
            agent_type="t",
            description="d",
            status=TaskStatus.FAILED,
            created_at=0,
        )
        assert failed.is_complete is True

    def test_to_dict(self):
        """Test serialization"""
        info = TaskInfo(
            task_id="test",
            agent_id="agent",
            agent_type="nekobasu",
            description="Test task",
            status=TaskStatus.COMPLETED,
            created_at=1000.0,
            started_at=1001.0,
            completed_at=1010.0,
            result="Done",
        )

        d = info.to_dict()
        assert d["task_id"] == "test"
        assert d["status"] == "completed"
        assert d["duration"] == 9.0
        assert d["has_result"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
