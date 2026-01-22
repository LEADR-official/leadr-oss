"""Tests for SMTP email provider."""

from unittest.mock import Mock, patch

import pytest

from leadr.infra.email.adapters.smtp import SMTPEmailProvider
from leadr.infra.email.domain.exceptions import EmailSendError
from leadr.infra.email.domain.models import Email


class TestSMTPEmailProvider:
    """Test SMTPEmailProvider."""

    def test_init_with_defaults(self):
        """Test initialization with default settings."""
        provider = SMTPEmailProvider()

        assert provider.host == "localhost"
        assert provider.port == 1025

    def test_init_with_custom_values(self):
        """Test initialization with custom host and port."""
        provider = SMTPEmailProvider(host="smtp.example.com", port=587)

        assert provider.host == "smtp.example.com"
        assert provider.port == 587

    def test_validate_config_valid(self):
        """Test validate_config with valid configuration."""
        provider = SMTPEmailProvider(host="localhost", port=1025)
        assert provider.validate_config() is True

    def test_validate_config_missing_host(self):
        """Test validate_config with missing host."""
        provider = SMTPEmailProvider(host="localhost", port=1025)
        # Manually override host to test validation
        provider.host = ""
        assert provider.validate_config() is False

    def test_validate_config_missing_port(self):
        """Test validate_config with missing port."""
        provider = SMTPEmailProvider(host="localhost", port=1025)
        # Manually override port to test validation
        provider.port = 0
        assert provider.validate_config() is False

    def test_send_with_invalid_config(self):
        """Test send raises error with invalid configuration."""
        provider = SMTPEmailProvider(host="localhost", port=1025)
        # Manually invalidate config
        provider.host = ""
        provider.port = 0

        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Test body",
        )

        with pytest.raises(EmailSendError, match="Invalid SMTP configuration"):
            provider.send(email)

    @patch("leadr.infra.email.adapters.smtp.smtplib.SMTP")
    @patch("leadr.infra.email.adapters.smtp.settings")
    def test_send_uses_default_from_email_when_not_provided(self, mock_settings, mock_smtp_class):
        """Test that send uses settings.default_from_email when from_email is None."""
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

        mock_smtp_instance = Mock()
        mock_smtp_class.return_value.__enter__ = Mock(return_value=mock_smtp_instance)
        mock_smtp_class.return_value.__exit__ = Mock(return_value=False)

        provider = SMTPEmailProvider(host="localhost", port=1025)

        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Test body",
            from_email=None,  # No from_email provided
        )

        response = provider.send(email)

        # Verify the MIME message was created with the default from email
        mock_smtp_instance.send_message.assert_called_once()
        sent_message = mock_smtp_instance.send_message.call_args[0][0]
        assert sent_message["From"] == "noreply@mg.leadr.gg"

        # Verify response format
        assert "id" in response
        assert response["message"] == "Queued. Thank you."

    @patch("leadr.infra.email.adapters.smtp.smtplib.SMTP")
    @patch("leadr.infra.email.adapters.smtp.settings")
    def test_send_uses_provided_from_email(self, mock_settings, mock_smtp_class):
        """Test that send uses provided from_email when specified."""
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

        mock_smtp_instance = Mock()
        mock_smtp_class.return_value.__enter__ = Mock(return_value=mock_smtp_instance)
        mock_smtp_class.return_value.__exit__ = Mock(return_value=False)

        provider = SMTPEmailProvider(host="localhost", port=1025)

        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Test body",
            from_email="custom@mg.leadr.gg",  # Custom from_email
        )

        provider.send(email)

        # Verify the MIME message used the custom from email
        sent_message = mock_smtp_instance.send_message.call_args[0][0]
        assert sent_message["From"] == "custom@mg.leadr.gg"

    @patch("leadr.infra.email.adapters.smtp.smtplib.SMTP")
    @patch("leadr.infra.email.adapters.smtp.settings")
    def test_send_minimal_email(self, mock_settings, mock_smtp_class):
        """Test sending email with minimal fields."""
        mock_settings.default_from_email = "noreply@test.mailgun.org"

        mock_smtp_instance = Mock()
        mock_smtp_class.return_value.__enter__ = Mock(return_value=mock_smtp_instance)
        mock_smtp_class.return_value.__exit__ = Mock(return_value=False)

        provider = SMTPEmailProvider(host="localhost", port=1025)

        email = Email.create(
            to="user@example.com",
            subject="Test Subject",
            body="Test body content",
        )

        response = provider.send(email)

        assert "id" in response
        mock_smtp_instance.send_message.assert_called_once()

        # Verify message data
        sent_message = mock_smtp_instance.send_message.call_args[0][0]
        assert sent_message["To"] == "user@example.com"
        assert sent_message["Subject"] == "Test Subject"

    @patch("leadr.infra.email.adapters.smtp.smtplib.SMTP")
    @patch("leadr.infra.email.adapters.smtp.settings")
    def test_send_with_all_fields(self, mock_settings, mock_smtp_class):
        """Test sending email with all fields."""
        mock_settings.default_from_email = "noreply@test.mailgun.org"

        mock_smtp_instance = Mock()
        mock_smtp_class.return_value.__enter__ = Mock(return_value=mock_smtp_instance)
        mock_smtp_class.return_value.__exit__ = Mock(return_value=False)

        provider = SMTPEmailProvider(host="localhost", port=1025)

        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Body",
            from_email="sender@example.com",
            reply_to="reply@example.com",
            cc=["cc1@example.com", "cc2@example.com"],
            bcc=["bcc@example.com"],
        )

        response = provider.send(email)

        assert "id" in response
        sent_message = mock_smtp_instance.send_message.call_args[0][0]
        assert sent_message["From"] == "sender@example.com"
        assert sent_message["Reply-To"] == "reply@example.com"
        assert sent_message["Cc"] == "cc1@example.com, cc2@example.com"
        assert sent_message["Bcc"] == "bcc@example.com"
