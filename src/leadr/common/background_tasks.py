"""Background task scheduler using asyncio.

Provides a simple background task scheduler that runs periodic tasks
within the FastAPI application process.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


class BackgroundTaskScheduler:
    """Manages periodic background tasks using asyncio.

    Tasks run in the same process as the FastAPI application,
    making them easy to test and deploy without additional infrastructure.

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
        self._task_handles: list[asyncio.Task] = []

    def add_task(
        self,
        name: str,
        func: Callable[[], Awaitable[None]],
        interval_seconds: int,
    ) -> None:
        """Register a periodic task.

        Args:
            name: Unique identifier for the task.
            func: Async function to call periodically.
            interval_seconds: How often to run the task (in seconds).

        Raises:
            ValueError: If task with the same name already exists.
        """
        if name in self.tasks:
            raise ValueError(f"Task '{name}' already registered")

        self.tasks[name] = {
            "func": func,
            "interval": interval_seconds,
        }
        logger.info("Registered background task: %s (interval: %ds)", name, interval_seconds)

    async def _run_task_loop(
        self, name: str, func: Callable[[], Awaitable[None]], interval: int
    ) -> None:
        """Run a single task in a loop.

        Args:
            name: Task name for logging.
            func: Async function to call.
            interval: Seconds between executions.
        """
        from datetime import UTC, datetime

        logger.info("Starting background task loop: %s", name)

        while self.running:
            try:
                start_time = datetime.now(UTC)
                logger.debug("Running task: %s", name)

                await func()

                elapsed = (datetime.now(UTC) - start_time).total_seconds()
                logger.debug("Task '%s' completed in %.2fs", name, elapsed)

            except Exception:
                logger.exception("Error in background task '%s'", name)

            # Wait for next interval
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
