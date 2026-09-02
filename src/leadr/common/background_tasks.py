"""Background task scheduler using asyncio.

Provides a simple background task scheduler that runs periodic tasks
within the FastAPI application process, with retry logic and failure alerting.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from leadr.config import settings

logger = logging.getLogger(__name__)

# Type alias for max retries exceeded callback
MaxRetriesExceededCallback = Callable[[str, int, Exception], Awaitable[None]]


class BackgroundTaskScheduler:
    """Manages periodic background tasks using asyncio.

    Tasks run in the same process as the FastAPI application,
    making them easy to test and deploy without additional infrastructure.

    Supports retry with configurable backoff delays and optional alerting
    when max retries are exceeded.

    Example:
        >>> scheduler = BackgroundTaskScheduler()
        >>> async def my_task():
        ...     print("Task running")
        >>> scheduler.add_task("my-task", my_task, interval_seconds=60)
        >>> await scheduler.start()
    """

    def __init__(self):
        """Initialize the scheduler."""
        self.tasks: dict[str, dict[str, Any]] = {}
        self.running = False
        self._task_handles: list[asyncio.Task[None]] = []
        self._on_max_retries_exceeded: MaxRetriesExceededCallback | None = None

    def set_on_max_retries_exceeded(
        self,
        callback: MaxRetriesExceededCallback,
    ) -> None:
        """Set callback for when a task exceeds max retries.

        Args:
            callback: Async function called with (task_name, failure_count, error).
        """
        self._on_max_retries_exceeded = callback

    def add_task(
        self,
        name: str,
        func: Callable[[], Awaitable[None]],
        interval_seconds: int,
        alert_on_max_retries: bool = False,
    ) -> None:
        """Register a periodic task.

        Args:
            name: Unique identifier for the task.
            func: Async function to call periodically.
            interval_seconds: How often to run the task (in seconds).
            alert_on_max_retries: If True, trigger callback when max retries exceeded.

        Raises:
            ValueError: If task with the same name already exists.
        """
        if name in self.tasks:
            raise ValueError(f"Task '{name}' already registered")

        self.tasks[name] = {
            "func": func,
            "interval": interval_seconds,
            "alert_on_max_retries": alert_on_max_retries,
        }
        logger.info("Registered background task: %s (interval: %ds)", name, interval_seconds)

    async def _run_task_loop(
        self,
        name: str,
        func: Callable[[], Awaitable[None]],
        interval: int,
        alert_on_max_retries: bool,
    ) -> None:
        """Run a single task in a loop with retry logic.

        Args:
            name: Task name for logging.
            func: Async function to call.
            interval: Seconds between executions.
            alert_on_max_retries: Whether to trigger alert callback on max retries.
        """
        logger.info("Starting background task loop: %s", name)

        retry_delays = settings.BACKGROUND_TASK_RETRY_DELAYS
        max_attempts = len(retry_delays)

        while self.running:
            attempt = 0  # Local counter per execution cycle

            # Retry loop
            while attempt < max_attempts:
                try:
                    start_time = datetime.now(UTC)
                    logger.debug(
                        "Running task: %s (attempt %d/%d)", name, attempt + 1, max_attempts
                    )

                    await func()

                    elapsed = (datetime.now(UTC) - start_time).total_seconds()
                    logger.debug("Task '%s' completed in %.2fs", name, elapsed)
                    break  # Success - exit retry loop

                except Exception as e:
                    attempt += 1
                    logger.exception(
                        "Error in background task '%s' (attempt %d/%d)",
                        name,
                        attempt,
                        max_attempts,
                    )

                    if attempt >= max_attempts:
                        logger.error(
                            "Task '%s' failed after %d attempts, giving up until next interval",
                            name,
                            attempt,
                        )
                        if alert_on_max_retries and self._on_max_retries_exceeded:
                            try:
                                await self._on_max_retries_exceeded(name, attempt, e)
                            except Exception:
                                logger.exception(
                                    "Error in max retries callback for task '%s'", name
                                )
                        break  # Exit retry loop

                    # Get delay from config list (attempt is 1-indexed, list is 0-indexed)
                    delay = retry_delays[attempt - 1]
                    logger.info("Retrying task '%s' in %.1fs", name, delay)

                    # Check running flag before sleep for graceful shutdown
                    if not self.running:
                        break
                    await asyncio.sleep(delay)

            # Wait for next scheduled interval
            if self.running:
                await asyncio.sleep(interval)

        logger.info("Stopped background task loop: %s", name)

    async def start(self) -> None:
        """Start all registered tasks.

        This method starts all background task loops concurrently.
        It returns immediately after starting the tasks.
        """
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        logger.info("Starting %d background tasks", len(self.tasks))

        # Start all task loops
        for name, task_config in self.tasks.items():
            task_handle = asyncio.create_task(
                self._run_task_loop(
                    name,
                    task_config["func"],
                    task_config["interval"],
                    task_config["alert_on_max_retries"],
                )
            )
            self._task_handles.append(task_handle)

        logger.info("All background tasks started")

    async def stop(self) -> None:
        """Stop all running tasks gracefully.

        Waits for currently executing tasks to complete before stopping.
        """
        if not self.running:
            return

        logger.info("Stopping background tasks...")
        self.running = False

        # Cancel all task handles
        for task in self._task_handles:
            task.cancel()

        # Wait for all tasks to complete (with timeout)
        await asyncio.gather(*self._task_handles, return_exceptions=True)

        self._task_handles.clear()
        logger.info("All background tasks stopped")


# Global scheduler instance
_scheduler = BackgroundTaskScheduler()


def get_scheduler() -> BackgroundTaskScheduler:
    """Get the global scheduler instance.

    Returns:
        The singleton BackgroundTaskScheduler instance.
    """
    return _scheduler
