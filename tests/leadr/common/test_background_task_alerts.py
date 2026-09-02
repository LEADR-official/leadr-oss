"""Tests for background task failure alerting."""

from unittest.mock import AsyncMock, patch

import pytest

from leadr.common.background_task_alerts import send_task_failure_alert
from leadr.infra.email import EmailPriority


@pytest.mark.asyncio
class TestSendTaskFailureAlert:
    """Tests for send_task_failure_alert function."""

    @patch("leadr.common.background_task_alerts.settings")
    @patch("leadr.common.background_task_alerts.create_email_service")
    async def test_send_alert_calls_email_service(self, mock_create_email_service, mock_settings):
        """Test that alert sends email via EmailService."""
        mock_settings.ADMIN_NOTIFICATION_EMAIL = "admin@example.com"
        mock_email_service = AsyncMock()
        mock_create_email_service.return_value = mock_email_service

        error = RuntimeError("Test error")
        await send_task_failure_alert("test-task", 5, error)

        mock_email_service.send_notification_email.assert_called_once()
        call_kwargs = mock_email_service.send_notification_email.call_args[1]
        assert call_kwargs["to"] == "admin@example.com"
        assert "test-task" in call_kwargs["subject"]
        assert "failed" in call_kwargs["subject"].lower()

    @patch("leadr.common.background_task_alerts.settings")
    @patch("leadr.common.background_task_alerts.create_email_service")
    async def test_alert_includes_error_details(self, mock_create_email_service, mock_settings):
        """Test alert message includes error type and traceback."""
        mock_settings.ADMIN_NOTIFICATION_EMAIL = "admin@example.com"
        mock_email_service = AsyncMock()
        mock_create_email_service.return_value = mock_email_service

        error = ValueError("Specific error message")
        await send_task_failure_alert("failing-task", 3, error)

        call_kwargs = mock_email_service.send_notification_email.call_args[1]
        message = call_kwargs["message"]

        # Should contain error type
        assert "ValueError" in message
        # Should contain error message
        assert "Specific error message" in message
        # Should contain failure count
        assert "3" in message
        # Should contain task name
        assert "failing-task" in message
        # Should contain traceback indicator
        assert "Traceback" in message

    @patch("leadr.common.background_task_alerts.settings")
    @patch("leadr.common.background_task_alerts.create_email_service")
    @patch("leadr.common.background_task_alerts.logger")
    async def test_alert_skipped_when_no_admin_email(
        self, mock_logger, mock_create_email_service, mock_settings
    ):
        """Test alert is skipped when ADMIN_NOTIFICATION_EMAIL is empty."""
        mock_settings.ADMIN_NOTIFICATION_EMAIL = ""

        error = RuntimeError("Test error")
        await send_task_failure_alert("test-task", 5, error)

        # Email service should not be created
        mock_create_email_service.assert_not_called()
        # Warning should be logged
        mock_logger.warning.assert_called_once()
        assert "no admin email configured" in mock_logger.warning.call_args[0][0].lower()

    @patch("leadr.common.background_task_alerts.settings")
    @patch("leadr.common.background_task_alerts.create_email_service")
    @patch("leadr.common.background_task_alerts.logger")
    async def test_email_failure_handled_gracefully(
        self, mock_logger, mock_create_email_service, mock_settings
    ):
        """Test email send failure is logged but doesn't raise."""
        mock_settings.ADMIN_NOTIFICATION_EMAIL = "admin@example.com"
        mock_email_service = AsyncMock()
        mock_email_service.send_notification_email.side_effect = Exception("SMTP error")
        mock_create_email_service.return_value = mock_email_service

        error = RuntimeError("Test error")

        # Should not raise
        await send_task_failure_alert("test-task", 5, error)

        # Error should be logged
        mock_logger.exception.assert_called_once()
        # Check that task name is in the log args (format string uses %s)
        assert "test-task" in str(mock_logger.exception.call_args)

    @patch("leadr.common.background_task_alerts.settings")
    @patch("leadr.common.background_task_alerts.create_email_service")
    async def test_alert_uses_high_priority(self, mock_create_email_service, mock_settings):
        """Test alert is sent with HIGH priority."""
        mock_settings.ADMIN_NOTIFICATION_EMAIL = "admin@example.com"
        mock_email_service = AsyncMock()
        mock_create_email_service.return_value = mock_email_service

        error = RuntimeError("Test error")
        await send_task_failure_alert("test-task", 5, error)

        call_kwargs = mock_email_service.send_notification_email.call_args[1]
        assert call_kwargs["priority"] == EmailPriority.HIGH

    @patch("leadr.common.background_task_alerts.settings")
    @patch("leadr.common.background_task_alerts.create_email_service")
    @patch("leadr.common.background_task_alerts.logger")
    async def test_success_logged(self, mock_logger, mock_create_email_service, mock_settings):
        """Test successful alert send is logged."""
        mock_settings.ADMIN_NOTIFICATION_EMAIL = "admin@example.com"
        mock_email_service = AsyncMock()
        mock_create_email_service.return_value = mock_email_service

        error = RuntimeError("Test error")
        await send_task_failure_alert("test-task", 5, error)

        mock_logger.info.assert_called()
        assert "test-task" in str(mock_logger.info.call_args)
