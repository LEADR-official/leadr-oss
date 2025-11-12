"""Tests for background task scheduler."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from leadr.common.background_tasks import BackgroundTaskScheduler, get_scheduler


@pytest.mark.asyncio
class TestBackgroundTaskScheduler:
    """Tests for BackgroundTaskScheduler."""

    async def test_add_task(self):
        """Test adding a task to the scheduler."""
        scheduler = BackgroundTaskScheduler()
        mock_func = AsyncMock()

        scheduler.add_task("test-task", mock_func, interval_seconds=60)

        assert "test-task" in scheduler.tasks
        assert scheduler.tasks["test-task"]["func"] == mock_func
        assert scheduler.tasks["test-task"]["interval"] == 60

    async def test_add_duplicate_task_raises_error(self):
        """Test that adding a task with duplicate name raises ValueError."""
        scheduler = BackgroundTaskScheduler()
        mock_func = AsyncMock()

        scheduler.add_task("test-task", mock_func, interval_seconds=60)

        with pytest.raises(ValueError, match="already registered"):
            scheduler.add_task("test-task", mock_func, interval_seconds=30)

    async def test_start_scheduler(self):
        """Test starting the scheduler."""
        scheduler = BackgroundTaskScheduler()
        call_count = [0]

        async def test_func():
            call_count[0] += 1
            await asyncio.sleep(0.1)

        scheduler.add_task("test-task", test_func, interval_seconds=1)

        await scheduler.start()
        # Give tasks time to start
        await asyncio.sleep(0.05)

        assert scheduler.running is True
        assert len(scheduler._task_handles) == 1

        # Wait for task to run once
        await asyncio.sleep(0.2)

        # Stop scheduler
        await scheduler.stop()

        assert call_count[0] >= 1

    async def test_start_already_running_scheduler(self):
        """Test starting a scheduler that's already running does nothing."""
        scheduler = BackgroundTaskScheduler()
        mock_func = AsyncMock()

        scheduler.add_task("test-task", mock_func, interval_seconds=60)

        await scheduler.start()
        assert scheduler.running is True

        # Try to start again - should not create duplicate tasks
        await scheduler.start()
        assert len(scheduler._task_handles) == 1

        await scheduler.stop()

    async def test_stop_scheduler(self):
        """Test stopping the scheduler."""
        scheduler = BackgroundTaskScheduler()
        call_count = [0]

        async def test_func():
            call_count[0] += 1
            await asyncio.sleep(0.1)

        scheduler.add_task("test-task", test_func, interval_seconds=1)

        await scheduler.start()
        await asyncio.sleep(0.1)

        assert scheduler.running is True

        await scheduler.stop()

        assert scheduler.running is False
        assert len(scheduler._task_handles) == 0

    async def test_stop_not_running_scheduler(self):
        """Test stopping a scheduler that's not running does nothing."""
        scheduler = BackgroundTaskScheduler()

        # Should not raise any error
        await scheduler.stop()

        assert scheduler.running is False

    async def test_task_execution_with_exception(self):
        """Test that exceptions in tasks are caught and logged."""
        scheduler = BackgroundTaskScheduler()
        call_count = [0]

        async def failing_func():
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("Test error")
            # Stop after second call
            scheduler.running = False

        scheduler.add_task("failing-task", failing_func, interval_seconds=1)

        with patch("leadr.common.background_tasks.logger") as mock_logger:
            await scheduler.start()
            await asyncio.sleep(0.1)

            # Wait for task to run and handle exception
            await asyncio.sleep(0.3)

            await scheduler.stop()

            # Should have logged the exception
            mock_logger.exception.assert_called()
            # Task should have continued running after exception
            assert call_count[0] >= 1

    async def test_multiple_tasks(self):
        """Test running multiple tasks concurrently."""
        scheduler = BackgroundTaskScheduler()
        call_counts = {"task1": 0, "task2": 0, "task3": 0}

        async def make_task_func(task_name):
            async def task_func():
                call_counts[task_name] += 1
                # Stop after first call for all tasks
                if all(count >= 1 for count in call_counts.values()):
                    scheduler.running = False

            return task_func

        scheduler.add_task("task1", await make_task_func("task1"), interval_seconds=1)
        scheduler.add_task("task2", await make_task_func("task2"), interval_seconds=1)
        scheduler.add_task("task3", await make_task_func("task3"), interval_seconds=1)

        await scheduler.start()
        await asyncio.sleep(0.1)

        # Wait for all tasks to run once
        await asyncio.sleep(0.3)

        await scheduler.stop()

        # All tasks should have run at least once
        assert call_counts["task1"] >= 1
        assert call_counts["task2"] >= 1
        assert call_counts["task3"] >= 1

    async def test_task_interval_timing(self):
        """Test that tasks respect their interval timing."""
        scheduler = BackgroundTaskScheduler()
        call_times = []

        async def timed_func():
            from datetime import UTC, datetime

            call_times.append(datetime.now(UTC))
            if len(call_times) >= 2:
                scheduler.running = False

        # Very short interval for testing
        scheduler.add_task("timed-task", timed_func, interval_seconds=1)

        await scheduler.start()
        await asyncio.sleep(0.1)

        # Wait for 2 calls
        await asyncio.sleep(1.5)

        await scheduler.stop()

        # Should have at least 2 calls
        assert len(call_times) >= 2

        # Check interval between calls (should be close to 1 second)
        if len(call_times) >= 2:
            interval = (call_times[1] - call_times[0]).total_seconds()
            # Allow some tolerance for execution time
            assert 0.8 <= interval <= 1.5

    async def test_get_scheduler_singleton(self):
        """Test that get_scheduler returns the same instance."""
        scheduler1 = get_scheduler()
        scheduler2 = get_scheduler()

        assert scheduler1 is scheduler2

    async def test_task_cleanup_on_stop(self):
        """Test that task handles are properly cleaned up on stop."""
        scheduler = BackgroundTaskScheduler()

        async def test_func():
            await asyncio.sleep(0.1)

        scheduler.add_task("cleanup-task", test_func, interval_seconds=1)

        await scheduler.start()
        await asyncio.sleep(0.1)

        assert len(scheduler._task_handles) > 0

        await scheduler.stop()

        assert len(scheduler._task_handles) == 0
        assert scheduler.running is False

    async def test_task_continues_after_error(self):
        """Test that a task continues running after encountering an error."""
        scheduler = BackgroundTaskScheduler()
        call_count = [0]

        async def sometimes_failing_func():
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("First call fails")
            if call_count[0] >= 3:
                scheduler.running = False

        scheduler.add_task("resilient-task", sometimes_failing_func, interval_seconds=1)

        await scheduler.start()
        await asyncio.sleep(0.1)

        # Wait for multiple calls
        await asyncio.sleep(2.5)

        await scheduler.stop()

        # Should have recovered and continued running
        assert call_count[0] >= 3

    async def test_no_tasks_registered(self):
        """Test starting scheduler with no tasks registered."""
        scheduler = BackgroundTaskScheduler()

        await scheduler.start()

        assert scheduler.running is True
        assert len(scheduler._task_handles) == 0

        await scheduler.stop()
