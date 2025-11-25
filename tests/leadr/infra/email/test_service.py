"""Tests for email service."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.infra.email.adapters.repositories import EmailRepository
from leadr.infra.email.domain.exceptions import EmailSendError
from leadr.infra.email.domain.models import EmailPriority, EmailStatus
from leadr.infra.email.service import EmailService


class TestEmailServiceInit:
    """Test EmailService initialization."""

    def test_init_without_db(self):
        """Test initialization without database session."""
        mock_provider = Mock()
        mock_provider.validate_config.return_value = True

        service = EmailService(provider=mock_provider, db=None)

        assert service.provider == mock_provider
        assert service.db is None
        assert service.repository is None

    def test_init_with_db(self, db_session: AsyncSession):
        """Test initialization with database session."""
        mock_provider = Mock()
        mock_provider.validate_config.return_value = True

        service = EmailService(provider=mock_provider, db=db_session)

        assert service.provider == mock_provider
        assert service.db == db_session
        assert service.repository is not None

    def test_init_with_validation_success(self):
        """Test initialization with validation enabled and valid config."""
        mock_provider = Mock()
        mock_provider.validate_config.return_value = True

        service = EmailService(provider=mock_provider, validate_on_init=True)

        assert service.provider == mock_provider
        mock_provider.validate_config.assert_called_once()

    def test_init_with_validation_failure(self):
        """Test initialization with validation enabled and invalid config."""
        mock_provider = Mock()
        mock_provider.validate_config.return_value = False

        with pytest.raises(ValueError, match="Email provider configuration is invalid"):
            EmailService(provider=mock_provider, validate_on_init=True)

    def test_templates_dir_set(self):
        """Test that templates_dir is set correctly."""
        mock_provider = Mock()
        service = EmailService(provider=mock_provider)

        assert isinstance(service.templates_dir, Path)
        assert service.templates_dir.name == "templates"


@pytest.mark.asyncio
class TestEmailServiceSendEmail:
    """Test EmailService send_email method."""

    @patch("leadr.infra.email.service.settings")
    async def test_send_email_minimal_production(self, mock_settings, db_session: AsyncSession):
        """Test sending email with minimal fields in production."""
        mock_settings.ENV = "PROD"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-123", "message": "Queued"}

        service = EmailService(provider=mock_provider, db=db_session)

        response = await service.send_email(
            to="user@example.com",
            subject="Test Subject",
            body="Test body",
        )

        assert response == {"id": "msg-123", "message": "Queued"}
        mock_provider.send.assert_called_once()

        # Verify email was saved to database
        email_arg = mock_provider.send.call_args[0][0]
        assert email_arg.to == "user@example.com"
        assert email_arg.status == EmailStatus.SENT

    @patch("leadr.infra.email.service.settings")
    async def test_send_email_dev_overrides_recipient(
        self, mock_settings, db_session: AsyncSession
    ):
        """Test that DEV environment overrides recipient."""
        mock_settings.ENV = "DEV"
        mock_settings.TESTING_EMAIL = "dev-test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-456"}

        service = EmailService(provider=mock_provider, db=db_session)

        await service.send_email(
            to="original@example.com",
            subject="Test",
            body="Body",
        )

        # Verify email was sent to testing email instead
        email_arg = mock_provider.send.call_args[0][0]
        assert email_arg.to == "dev-test@leadr.gg"

    @patch("leadr.infra.email.service.settings")
    async def test_send_email_test_overrides_recipient(
        self, mock_settings, db_session: AsyncSession
    ):
        """Test that TEST environment overrides recipient to TESTING_EMAIL."""
        mock_settings.ENV = "TEST"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-test"}

        service = EmailService(provider=mock_provider, db=db_session)

        response = await service.send_email(
            to="user@example.com",
            subject="Test",
            body="Body",
        )

        # Should send to testing email
        assert response["id"] == "msg-test"

        # Verify email was sent to testing email instead
        email_arg = mock_provider.send.call_args[0][0]
        assert email_arg.to == "test@leadr.gg"

    @patch("leadr.infra.email.service.settings")
    async def test_send_email_overrides_from_email(self, mock_settings, db_session: AsyncSession):
        """Test that from_email is always overridden."""
        mock_settings.ENV = "PROD"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-789"}

        service = EmailService(provider=mock_provider, db=db_session)

        await service.send_email(
            to="user@example.com",
            subject="Test",
            body="Body",
            from_email="custom@example.com",  # This should be ignored
        )

        email_arg = mock_provider.send.call_args[0][0]
        # from_email should be overridden with postmaster
        assert email_arg.from_email == "postmaster@mg.leadr.gg"

    @patch("leadr.infra.email.service.settings")
    async def test_send_email_with_all_fields(self, mock_settings, db_session: AsyncSession):
        """Test sending email with all optional fields."""
        mock_settings.ENV = "PROD"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-all"}

        service = EmailService(provider=mock_provider, db=db_session)

        response = await service.send_email(
            to="user@example.com",
            subject="Test",
            body="Body",
            cc=["cc@example.com"],
            bcc=["bcc@example.com"],
            priority=EmailPriority.HIGH,
            template_data={"key": "value"},
        )

        assert response["id"] == "msg-all"
        email_arg = mock_provider.send.call_args[0][0]
        assert email_arg.cc == ["cc@example.com"]
        assert email_arg.bcc == ["bcc@example.com"]
        assert email_arg.priority == EmailPriority.HIGH
        assert email_arg.template_data == {"key": "value"}

    @patch("leadr.infra.email.service.settings")
    async def test_send_email_updates_status_on_success(
        self, mock_settings, db_session: AsyncSession
    ):
        """Test that email status is updated to SENT on success."""
        mock_settings.ENV = "PROD"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"message_id": "msg-success"}

        service = EmailService(provider=mock_provider, db=db_session)

        await service.send_email(to="user@example.com", subject="Test", body="Body")

        # Retrieve the email from database

        repository = EmailRepository(db_session)
        emails = await repository.filter(to="user@example.com")

        assert len(emails) == 1
        assert emails[0].status == EmailStatus.SENT
        assert emails[0].provider_message_id == "msg-success"

    @patch("leadr.infra.email.service.settings")
    async def test_send_email_updates_status_on_failure(
        self, mock_settings, db_session: AsyncSession
    ):
        """Test that email status is updated to FAILED on error."""
        mock_settings.ENV = "PROD"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.side_effect = EmailSendError("Send failed", {"error": "Invalid"})

        service = EmailService(provider=mock_provider, db=db_session)

        with pytest.raises(EmailSendError):
            await service.send_email(to="user@example.com", subject="Test", body="Body")

        # Retrieve the email from database

        repository = EmailRepository(db_session)
        emails = await repository.filter(to="user@example.com")

        assert len(emails) == 1
        assert emails[0].status == EmailStatus.FAILED
        assert emails[0].error_message == "Send failed"

    @patch("leadr.infra.email.service.settings")
    async def test_send_email_without_db(self, mock_settings):
        """Test sending email without database persistence."""
        mock_settings.ENV = "PROD"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-no-db"}

        service = EmailService(provider=mock_provider, db=None)

        response = await service.send_email(to="user@example.com", subject="Test", body="Body")

        assert response["id"] == "msg-no-db"
        mock_provider.send.assert_called_once()


@pytest.mark.asyncio
class TestEmailServiceConvenienceMethods:
    """Test EmailService convenience methods."""

    @patch("leadr.infra.email.service.settings")
    async def test_send_verification_code(self, mock_settings, db_session: AsyncSession):
        """Test send_verification_code convenience method."""
        mock_settings.ENV = "TEST"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-verification"}

        service = EmailService(provider=mock_provider, db=db_session)

        # Mock template loading
        service._load_template = Mock(
            return_value="Your verification code is {code}. Please use it within 10 minutes."
        )

        response = await service.send_verification_code(
            to="user@example.com",
            code="ABC123",
        )

        # Should send email in TEST env
        assert response["id"] == "msg-verification"

        # Verify email was created with correct content

        repository = EmailRepository(db_session)
        emails = await repository.filter()
        assert len(emails) == 1
        assert emails[0].subject == "Verify your LEADR account"
        assert "ABC123" in emails[0].body
        assert emails[0].priority == EmailPriority.HIGH

    @patch("leadr.infra.email.service.settings")
    async def test_send_welcome_email(self, mock_settings, db_session: AsyncSession):
        """Test send_welcome_email convenience method."""
        mock_settings.ENV = "TEST"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-welcome"}

        service = EmailService(provider=mock_provider, db=db_session)

        service._load_template = Mock(return_value="Welcome {account_name}!")

        response = await service.send_welcome_email(
            to="user@example.com",
            account_name="TestCo",
            account_slug="testco",
        )

        assert response["id"] == "msg-welcome"

        repository = EmailRepository(db_session)
        emails = await repository.filter()
        assert len(emails) == 1
        assert "Welcome to LEADR, TestCo!" in emails[0].subject
        assert "TestCo" in emails[0].body
        assert emails[0].priority == EmailPriority.NORMAL

    @patch("leadr.infra.email.service.settings")
    async def test_send_notification_email(self, mock_settings, db_session: AsyncSession):
        """Test send_notification_email convenience method."""
        mock_settings.ENV = "TEST"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-notification"}

        service = EmailService(provider=mock_provider, db=db_session)

        service._load_template = Mock(return_value="Notification: {message}")

        response = await service.send_notification_email(
            to="user@example.com",
            subject="Important Update",
            message="Your account has been upgraded!",
            priority=EmailPriority.HIGH,
        )

        assert response["id"] == "msg-notification"

        repository = EmailRepository(db_session)
        emails = await repository.filter()
        assert len(emails) == 1
        assert emails[0].subject == "Important Update"
        assert "Your account has been upgraded!" in emails[0].body
        assert emails[0].priority == EmailPriority.HIGH


class TestEmailServiceUtilityMethods:
    """Test EmailService utility methods."""

    def test_get_default_from_email(self):
        """Test get_default_from_email method."""
        mock_provider = Mock()
        service = EmailService(provider=mock_provider)

        assert service.get_default_from_email() == "noreply@leadr.gg"

    def test_validate_provider_config(self):
        """Test validate_provider_config method."""
        mock_provider = Mock()
        mock_provider.validate_config.return_value = True

        service = EmailService(provider=mock_provider)

        assert service.validate_provider_config() is True
        mock_provider.validate_config.assert_called_once()
