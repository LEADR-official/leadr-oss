"""Tests for background task scheduler."""

import asyncio
from datetime import UTC, datetime
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
        original_sleep = asyncio.sleep

        async def fast_sleep(duration: float) -> None:
            await original_sleep(0.001)  # Speed up test

        with (
            patch("leadr.common.background_tasks.settings") as mock_settings,
            patch("leadr.common.background_tasks.asyncio.sleep", side_effect=fast_sleep),
        ):
            mock_settings.BACKGROUND_TASK_RETRY_DELAYS = [0.01]  # Single fast retry

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
            # Wait for task to complete
            while scheduler.running:
                await original_sleep(0.01)
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


@pytest.mark.asyncio
class TestBackgroundTaskRetry:
    """Tests for background task retry logic."""

    async def test_add_task_with_alert_on_max_retries(self):
        """Test adding a task with alert_on_max_retries flag."""
        scheduler = BackgroundTaskScheduler()
        mock_func = AsyncMock()

        scheduler.add_task("test-task", mock_func, interval_seconds=60, alert_on_max_retries=True)

        assert scheduler.tasks["test-task"]["alert_on_max_retries"] is True

    async def test_add_task_without_alert_on_max_retries_defaults_false(self):
        """Test that alert_on_max_retries defaults to False."""
        scheduler = BackgroundTaskScheduler()
        mock_func = AsyncMock()

        scheduler.add_task("test-task", mock_func, interval_seconds=60)

        assert scheduler.tasks["test-task"]["alert_on_max_retries"] is False

    async def test_set_on_max_retries_exceeded_callback(self):
        """Test setting the max retries exceeded callback."""
        scheduler = BackgroundTaskScheduler()
        mock_callback = AsyncMock()

        scheduler.set_on_max_retries_exceeded(mock_callback)

        assert scheduler._on_max_retries_exceeded == mock_callback

    async def test_task_retries_on_failure_then_succeeds(self):
        """Test task retries on failure and succeeds on retry."""
        original_sleep = asyncio.sleep

        async def fast_sleep(duration: float) -> None:
            await original_sleep(0.001)  # Speed up test

        with (
            patch("leadr.common.background_tasks.settings") as mock_settings,
            patch("leadr.common.background_tasks.asyncio.sleep", side_effect=fast_sleep),
        ):
            mock_settings.BACKGROUND_TASK_RETRY_DELAYS = [0.01]  # 10ms for fast test

            scheduler = BackgroundTaskScheduler()
            call_count = [0]

            async def sometimes_failing_func():
                call_count[0] += 1
                if call_count[0] == 1:
                    raise RuntimeError("First call fails")
                # Second call succeeds, stop scheduler
                scheduler.running = False

            scheduler.add_task("retry-task", sometimes_failing_func, interval_seconds=1)

            await scheduler.start()
            # Wait for task to complete
            while scheduler.running:
                await original_sleep(0.01)
            await scheduler.stop()

            # Should have been called twice: fail, then succeed
            assert call_count[0] == 2

    async def test_task_uses_correct_delay_sequence(self):
        """Test that retries use delays from config in order."""
        sleep_calls: list[float] = []
        original_sleep = asyncio.sleep

        async def tracking_sleep(duration: float) -> None:
            sleep_calls.append(duration)
            await original_sleep(0.001)  # Speed up test

        with (
            patch("leadr.common.background_tasks.settings") as mock_settings,
            patch("leadr.common.background_tasks.asyncio.sleep", side_effect=tracking_sleep),
        ):
            mock_settings.BACKGROUND_TASK_RETRY_DELAYS = [0.01, 0.02, 0.03]

            scheduler = BackgroundTaskScheduler()
            call_count = [0]

            async def always_failing_func():
                call_count[0] += 1
                # Stop after all retries exhausted
                if call_count[0] >= 3:
                    scheduler.running = False
                raise RuntimeError(f"Failure {call_count[0]}")

            scheduler.add_task("delay-task", always_failing_func, interval_seconds=10)

            await scheduler.start()
            # Wait for retries to complete
            while scheduler.running:
                await original_sleep(0.01)
            await scheduler.stop()

        # Should have used first two delays from config (3 attempts = 2 retry delays)
        assert 0.01 in sleep_calls
        assert 0.02 in sleep_calls

    @patch("leadr.common.background_tasks.settings")
    async def test_task_max_retries_triggers_callback(self, mock_settings):
        """Test callback is invoked when max retries exceeded."""
        mock_settings.BACKGROUND_TASK_RETRY_DELAYS = [0.01, 0.01]  # 2 attempts, fast delays

        scheduler = BackgroundTaskScheduler()
        mock_callback = AsyncMock()
        scheduler.set_on_max_retries_exceeded(mock_callback)

        async def always_failing_func():
            raise RuntimeError("Always fails")

        scheduler.add_task(
            "failing-task",
            always_failing_func,
            interval_seconds=10,
            alert_on_max_retries=True,
        )

        await scheduler.start()
        await asyncio.sleep(0.2)
        scheduler.running = False
        await scheduler.stop()

        # Callback should have been called
        mock_callback.assert_called_once()
        args = mock_callback.call_args[0]
        assert args[0] == "failing-task"  # task_name
        assert args[1] == 2  # failure_count (matches len of delays)
        assert isinstance(args[2], RuntimeError)  # error

    @patch("leadr.common.background_tasks.settings")
    async def test_task_no_callback_when_alert_disabled(self, mock_settings):
        """Test callback not invoked when alert_on_max_retries is False."""
        mock_settings.BACKGROUND_TASK_RETRY_DELAYS = [0.01]  # 1 attempt

        scheduler = BackgroundTaskScheduler()
        mock_callback = AsyncMock()
        scheduler.set_on_max_retries_exceeded(mock_callback)

        async def always_failing_func():
            raise RuntimeError("Always fails")

        scheduler.add_task(
            "failing-task",
            always_failing_func,
            interval_seconds=10,
            alert_on_max_retries=False,  # Explicitly disabled
        )

        await scheduler.start()
        await asyncio.sleep(0.1)
        scheduler.running = False
        await scheduler.stop()

        # Callback should NOT have been called
        mock_callback.assert_not_called()

    async def test_task_continues_after_max_retries(self):
        """Test task waits for interval then retries fresh after max retries."""
        original_sleep = asyncio.sleep

        async def fast_sleep(duration: float) -> None:
            await original_sleep(0.001)

        with (
            patch("leadr.common.background_tasks.settings") as mock_settings,
            patch("leadr.common.background_tasks.asyncio.sleep", side_effect=fast_sleep),
        ):
            mock_settings.BACKGROUND_TASK_RETRY_DELAYS = [0.01]  # 1 attempt

            scheduler = BackgroundTaskScheduler()
            execution_cycles = [0]

            async def counting_func():
                execution_cycles[0] += 1
                if execution_cycles[0] <= 2:
                    raise RuntimeError("Fail first two cycles")
                # Third cycle succeeds
                scheduler.running = False

            scheduler.add_task("cycle-task", counting_func, interval_seconds=1)

            await scheduler.start()
            while scheduler.running:
                await original_sleep(0.01)
            await scheduler.stop()

            # Should have run multiple cycles (fail, wait interval, fail, wait interval, succeed)
            assert execution_cycles[0] >= 2

    @patch("leadr.common.background_tasks.settings")
    async def test_graceful_shutdown_during_backoff(self, mock_settings):
        """Test scheduler stops immediately when running=False during backoff."""
        mock_settings.BACKGROUND_TASK_RETRY_DELAYS = [10.0]  # Long delay

        scheduler = BackgroundTaskScheduler()
        call_count = [0]

        async def failing_func():
            call_count[0] += 1
            raise RuntimeError("Always fails")

        scheduler.add_task("shutdown-task", failing_func, interval_seconds=60)

        await scheduler.start()
        await asyncio.sleep(0.05)  # Let it fail once and start backoff

        # Signal shutdown during backoff wait
        start = asyncio.get_event_loop().time()
        await scheduler.stop()
        elapsed = asyncio.get_event_loop().time() - start

        # Should have stopped quickly, not waited for full 10s backoff
        assert elapsed < 1.0
        assert call_count[0] == 1  # Only ran once before shutdown
