"""Background task failure alerting.

Provides email notification when background tasks exceed their maximum
retry attempts, allowing administrators to be alerted to persistent failures.
"""

import logging
import traceback

from leadr.config import settings
from leadr.infra.email import EmailPriority, create_email_service

logger = logging.getLogger(__name__)


async def send_task_failure_alert(
    task_name: str,
    failure_count: int,
    error: Exception,
) -> None:
    """Send admin email notification when a task exceeds max retry attempts.

    Args:
        task_name: Name of the failed task.
        failure_count: Number of consecutive failures.
        error: The last exception that was raised.
    """
    if not settings.ADMIN_NOTIFICATION_EMAIL:
        logger.warning(
            "Task '%s' failed %d times but no admin email configured",
            task_name,
            failure_count,
        )
        return

    error_tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))

    message = (
        f"Background task '{task_name}' failed after {failure_count} attempts.\n\n"
        f"Error: {type(error).__name__}: {error}\n\n"
        f"Task will retry on next scheduled interval.\n\n"
        f"Traceback:\n{error_tb}"
    )

    try:
        email_service = create_email_service()  # No DB session (fire-and-forget)
        await email_service.send_notification_email(
            to=settings.ADMIN_NOTIFICATION_EMAIL,
            subject=f"[LEADR] Background task failed: {task_name}",
            message=message,
            priority=EmailPriority.HIGH,
        )
        logger.info("Sent failure alert for task '%s'", task_name)
    except Exception:
        logger.exception("Failed to send alert email for '%s'", task_name)
