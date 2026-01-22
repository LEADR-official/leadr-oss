"""Tests for Mailgun email provider."""

from unittest.mock import Mock, patch

import pytest
from mailgun.client import ApiError

from leadr.infra.email.adapters.mailgun import MailgunEmailProvider
from leadr.infra.email.domain.exceptions import EmailSendError
from leadr.infra.email.domain.models import Email, EmailPriority


class TestMailgunEmailProvider:
    """Test MailgunEmailProvider."""

    @patch("leadr.infra.email.adapters.mailgun.Client")
    @patch("leadr.infra.email.adapters.mailgun.settings")
    def test_init_with_valid_settings(self, mock_settings, mock_client):
        """Test initialization with valid settings."""
        mock_settings.MAILGUN_API_KEY = "test-api-key"
        mock_settings.MAILGUN_DOMAIN = "test.mailgun.org"

        provider = MailgunEmailProvider()

        assert provider.api_key == "test-api-key"
        assert provider.domain == "test.mailgun.org"
        assert provider.client is not None

    @patch("leadr.infra.email.adapters.mailgun.Client")
    @patch("leadr.infra.email.adapters.mailgun.settings")
    def test_validate_config_valid(self, mock_settings, mock_client):
        """Test validate_config with valid configuration."""
        mock_settings.MAILGUN_API_KEY = "test-api-key"
        mock_settings.MAILGUN_DOMAIN = "test.mailgun.org"

        provider = MailgunEmailProvider()
        assert provider.validate_config() is True

    @patch("leadr.infra.email.adapters.mailgun.Client")
    @patch("leadr.infra.email.adapters.mailgun.settings")
    def test_validate_config_missing_api_key(self, mock_settings, mock_client):
        """Test validate_config with missing API key."""
        mock_settings.MAILGUN_API_KEY = ""
        mock_settings.MAILGUN_DOMAIN = "test.mailgun.org"

        provider = MailgunEmailProvider()
        assert provider.validate_config() is False

    @patch("leadr.infra.email.adapters.mailgun.Client")
    @patch("leadr.infra.email.adapters.mailgun.settings")
    def test_validate_config_whitespace_api_key(self, mock_settings, mock_client):
        """Test validate_config with whitespace-only API key."""
        mock_settings.MAILGUN_API_KEY = "   "
        mock_settings.MAILGUN_DOMAIN = "test.mailgun.org"

        provider = MailgunEmailProvider()
        assert provider.validate_config() is False

    @patch("leadr.infra.email.adapters.mailgun.Client")
    @patch("leadr.infra.email.adapters.mailgun.settings")
    def test_validate_config_missing_domain(self, mock_settings, mock_client):
        """Test validate_config with missing domain."""
        mock_settings.MAILGUN_API_KEY = "test-api-key"
        mock_settings.MAILGUN_DOMAIN = ""

        provider = MailgunEmailProvider()
        assert provider.validate_config() is False

    @patch("leadr.infra.email.adapters.mailgun.Client")
    @patch("leadr.infra.email.adapters.mailgun.settings")
    def test_validate_config_none_values(self, mock_settings, mock_client):
        """Test validate_config with None values."""
        mock_settings.MAILGUN_API_KEY = None
        mock_settings.MAILGUN_DOMAIN = None

        provider = MailgunEmailProvider()
        assert provider.validate_config() is False

    @patch("leadr.infra.email.adapters.mailgun.Client")
    @patch("leadr.infra.email.adapters.mailgun.settings")
    def test_send_with_invalid_config(self, mock_settings, mock_client):
        """Test send raises error with invalid configuration."""
        mock_settings.MAILGUN_API_KEY = ""
        mock_settings.MAILGUN_DOMAIN = ""

        provider = MailgunEmailProvider()
        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Test body",
        )

        with pytest.raises(EmailSendError, match="Invalid Mailgun configuration"):
            provider.send(email)

    @patch("leadr.infra.email.adapters.mailgun.Client")
    @patch("leadr.infra.email.adapters.mailgun.settings")
    def test_send_minimal_email(self, mock_settings, mock_client):
        """Test sending email with minimal fields."""
        mock_settings.MAILGUN_API_KEY = "test-api-key"
        mock_settings.MAILGUN_DOMAIN = "test.mailgun.org"

        provider = MailgunEmailProvider()

        # Mock the Mailgun client
        mock_response = Mock()
        mock_response.json.return_value = {"id": "msg-123", "message": "Queued"}
        provider.client.messages.create = Mock(return_value=mock_response)

        email = Email.create(
            to="user@example.com",
            subject="Test Subject",
            body="Test body content",
        )

        response = provider.send(email)

        assert response == {"id": "msg-123", "message": "Queued"}
        provider.client.messages.create.assert_called_once()

        # Verify message data structure
        call_args = provider.client.messages.create.call_args
        assert call_args.kwargs["domain"] == "test.mailgun.org"
        message_data = call_args.kwargs["data"]
        assert message_data["to"] == "user@example.com"
        assert message_data["subject"] == "Test Subject"
        assert message_data["text"] == "Test body content"

    @patch("leadr.infra.email.adapters.mailgun.Client")
    @patch("leadr.infra.email.adapters.mailgun.settings")
    def test_send_with_all_fields(self, mock_settings, mock_client):
        """Test sending email with all fields."""
        mock_settings.MAILGUN_API_KEY = "test-api-key"
        mock_settings.MAILGUN_DOMAIN = "test.mailgun.org"

        provider = MailgunEmailProvider()

        mock_response = Mock()
        mock_response.json.return_value = {"id": "msg-456"}
        provider.client.messages.create = Mock(return_value=mock_response)

        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Body",
            from_email="sender@example.com",
            reply_to="reply@example.com",
            cc=["cc1@example.com", "cc2@example.com"],
            bcc=["bcc@example.com"],
            priority=EmailPriority.HIGH,
        )

        response = provider.send(email)

        assert response == {"id": "msg-456"}

        call_args = provider.client.messages.create.call_args
        message_data = call_args.kwargs["data"]
        assert message_data["from"] == "sender@example.com"
        assert message_data["h:Reply-To"] == "reply@example.com"
        assert message_data["cc"] == "cc1@example.com,cc2@example.com"
        assert message_data["bcc"] == "bcc@example.com"
        assert message_data["o:tag"] == "high"

    @patch("leadr.infra.email.adapters.mailgun.Client")
    @patch("leadr.infra.email.adapters.mailgun.settings")
    def test_send_without_from_email_uses_default(self, mock_settings, mock_client):
        """Test that send uses settings.default_from_email when not provided."""
        mock_settings.MAILGUN_API_KEY = "test-api-key"
        mock_settings.MAILGUN_DOMAIN = "test.mailgun.org"
        mock_settings.default_from_email = "noreply@test.mailgun.org"

        provider = MailgunEmailProvider()

        mock_response = Mock()
        mock_response.json.return_value = {"id": "msg-789"}
        provider.client.messages.create = Mock(return_value=mock_response)

        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Body",
        )

        provider.send(email)

        call_args = provider.client.messages.create.call_args
        message_data = call_args.kwargs["data"]
        assert message_data["from"] == "noreply@test.mailgun.org"

    @patch("leadr.infra.email.adapters.mailgun.Client")
    @patch("leadr.infra.email.adapters.mailgun.settings")
    def test_send_without_from_email_uses_custom_config(self, mock_settings, mock_client):
        """Test that send uses custom FROM_EMAIL from settings."""
        mock_settings.MAILGUN_API_KEY = "test-api-key"
        mock_settings.MAILGUN_DOMAIN = "mail.example.com"
        mock_settings.default_from_email = "support@mail.example.com"

        provider = MailgunEmailProvider()

        mock_response = Mock()
        mock_response.json.return_value = {"id": "msg-custom"}
        provider.client.messages.create = Mock(return_value=mock_response)

        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Body",
        )

        provider.send(email)

        call_args = provider.client.messages.create.call_args
        message_data = call_args.kwargs["data"]
        assert message_data["from"] == "support@mail.example.com"

    @patch("leadr.infra.email.adapters.mailgun.Client")
    @patch("leadr.infra.email.adapters.mailgun.settings")
    def test_send_handles_api_error(self, mock_settings, mock_client):
        """Test that send handles Mailgun API errors."""
        mock_settings.MAILGUN_API_KEY = "test-api-key"
        mock_settings.MAILGUN_DOMAIN = "test.mailgun.org"

        provider = MailgunEmailProvider()
        provider.client.messages.create = Mock(side_effect=ApiError("Invalid API key"))

        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Body",
        )

        with pytest.raises(EmailSendError, match="Mailgun API error"):
            provider.send(email)

    @patch("leadr.infra.email.adapters.mailgun.Client")
    @patch("leadr.infra.email.adapters.mailgun.settings")
    def test_send_handles_unexpected_error(self, mock_settings, mock_client):
        """Test that send handles unexpected errors."""
        mock_settings.MAILGUN_API_KEY = "test-api-key"
        mock_settings.MAILGUN_DOMAIN = "test.mailgun.org"

        provider = MailgunEmailProvider()
        provider.client.messages.create = Mock(side_effect=RuntimeError("Network error"))

        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Body",
        )

        with pytest.raises(EmailSendError, match="Unexpected error sending email"):
            provider.send(email)

    @patch("leadr.infra.email.adapters.mailgun.Client")
    @patch("leadr.infra.email.adapters.mailgun.settings")
    def test_priority_to_tag(self, mock_settings, mock_client):
        """Test priority to tag conversion."""
        mock_settings.MAILGUN_API_KEY = "test-api-key"
        mock_settings.MAILGUN_DOMAIN = "test.mailgun.org"

        provider = MailgunEmailProvider()

        assert provider._priority_to_tag(EmailPriority.LOW) == "low"
        assert provider._priority_to_tag(EmailPriority.NORMAL) == "normal"
        assert provider._priority_to_tag(EmailPriority.HIGH) == "high"
        assert provider._priority_to_tag(EmailPriority.URGENT) == "urgent"

    @patch("leadr.infra.email.adapters.mailgun.Client")
    @patch("leadr.infra.email.adapters.mailgun.settings")
    def test_normal_priority_no_tag(self, mock_settings, mock_client):
        """Test that NORMAL priority doesn't add a tag."""
        mock_settings.MAILGUN_API_KEY = "test-api-key"
        mock_settings.MAILGUN_DOMAIN = "test.mailgun.org"

        provider = MailgunEmailProvider()

        mock_response = Mock()
        mock_response.json.return_value = {"id": "msg-999"}
        provider.client.messages.create = Mock(return_value=mock_response)

        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Body",
            priority=EmailPriority.NORMAL,
        )

        provider.send(email)

        call_args = provider.client.messages.create.call_args
        message_data = call_args.kwargs["data"]
        # NORMAL priority should not add a tag
        assert "o:tag" not in message_data
