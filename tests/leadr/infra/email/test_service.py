"""Tests for email service."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.api.pagination import PaginationParams
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
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

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
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

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
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

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
    async def test_send_email_uses_default_from_email_when_not_provided(
        self, mock_settings, db_session: AsyncSession
    ):
        """Test that send_email uses default_from_email when from_email not provided."""
        mock_settings.ENV = "PROD"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-789"}

        service = EmailService(provider=mock_provider, db=db_session)

        await service.send_email(
            to="user@example.com",
            subject="Test",
            body="Body",
        )

        email_arg = mock_provider.send.call_args[0][0]
        assert email_arg.from_email == "noreply@mg.leadr.gg"

    @patch("leadr.infra.email.service.settings")
    async def test_send_email_accepts_valid_override_on_correct_domain(
        self, mock_settings, db_session: AsyncSession
    ):
        """Test that send_email accepts valid from_email override on MAILGUN_DOMAIN."""
        mock_settings.ENV = "PROD"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-custom"}

        service = EmailService(provider=mock_provider, db=db_session)

        await service.send_email(
            to="user@example.com",
            subject="Test",
            body="Body",
            from_email="support@mg.leadr.gg",  # Valid override on MAILGUN_DOMAIN
        )

        email_arg = mock_provider.send.call_args[0][0]
        assert email_arg.from_email == "support@mg.leadr.gg"

    @patch("leadr.infra.email.service.settings")
    async def test_send_email_raises_error_for_invalid_domain_override(
        self, mock_settings, db_session: AsyncSession
    ):
        """Test that send_email raises ValueError for from_email on wrong domain."""
        mock_settings.ENV = "PROD"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-invalid"}

        service = EmailService(provider=mock_provider, db=db_session)

        with pytest.raises(ValueError, match="from_email must be an address on mg.leadr.gg"):
            await service.send_email(
                to="user@example.com",
                subject="Test",
                body="Body",
                from_email="custom@otherdomain.com",  # Invalid domain
            )

    @patch("leadr.infra.email.service.settings")
    async def test_send_email_with_all_fields(self, mock_settings, db_session: AsyncSession):
        """Test sending email with all optional fields."""
        mock_settings.ENV = "PROD"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

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
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"message_id": "msg-success"}

        service = EmailService(provider=mock_provider, db=db_session)

        await service.send_email(to="user@example.com", subject="Test", body="Body")

        # Retrieve the email from database

        repository = EmailRepository(db_session)
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repository.filter(to="user@example.com", pagination=pagination)

        assert len(result.items) == 1
        assert result.items[0].status == EmailStatus.SENT
        assert result.items[0].provider_message_id == "msg-success"

    @patch("leadr.infra.email.service.settings")
    async def test_send_email_updates_status_on_failure(
        self, mock_settings, db_session: AsyncSession
    ):
        """Test that email status is updated to FAILED on error."""
        mock_settings.ENV = "PROD"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.side_effect = EmailSendError("Send failed", {"error": "Invalid"})

        service = EmailService(provider=mock_provider, db=db_session)

        with pytest.raises(EmailSendError):
            await service.send_email(to="user@example.com", subject="Test", body="Body")

        # Retrieve the email from database

        repository = EmailRepository(db_session)
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repository.filter(to="user@example.com", pagination=pagination)

        assert len(result.items) == 1
        assert result.items[0].status == EmailStatus.FAILED
        assert result.items[0].error_message == "Send failed"

    @patch("leadr.infra.email.service.settings")
    async def test_send_email_without_db(self, mock_settings):
        """Test sending email without database persistence."""
        mock_settings.ENV = "PROD"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

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
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

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
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repository.filter(pagination=pagination)
        assert len(result.items) == 1
        assert result.items[0].subject == "[TEST] Verify your LEADR account"
        assert "ABC123" in result.items[0].body
        assert result.items[0].priority == EmailPriority.HIGH

    @patch("leadr.infra.email.service.settings")
    async def test_send_welcome_email(self, mock_settings, db_session: AsyncSession):
        """Test send_welcome_email convenience method."""
        mock_settings.ENV = "TEST"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-welcome"}

        service = EmailService(provider=mock_provider, db=db_session)

        service._load_template = Mock(return_value="Welcome {user_name}!")
        service._footer = ""

        response = await service.send_welcome_email(
            to="user@example.com",
            user_name="Test User",
            account_name="TestCo",
            account_slug="testco",
        )

        assert response["id"] == "msg-welcome"

        repository = EmailRepository(db_session)
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repository.filter(pagination=pagination)
        assert len(result.items) == 1
        assert "Welcome to LEADR, TestCo!" in result.items[0].subject
        assert "Test User" in result.items[0].body
        assert result.items[0].priority == EmailPriority.NORMAL

    @patch("leadr.infra.email.service.settings")
    async def test_send_notification_email(self, mock_settings, db_session: AsyncSession):
        """Test send_notification_email convenience method."""
        mock_settings.ENV = "TEST"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

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
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repository.filter(pagination=pagination)
        assert len(result.items) == 1
        assert result.items[0].subject == "[TEST] Important Update"
        assert "Your account has been upgraded!" in result.items[0].body
        assert result.items[0].priority == EmailPriority.HIGH


class TestEmailServiceUtilityMethods:
    """Test EmailService utility methods."""

    @patch("leadr.infra.email.service.settings")
    def test_get_default_from_email_returns_config_value(self, mock_settings):
        """Test get_default_from_email returns settings.default_from_email."""
        mock_settings.default_from_email = "support@mail.example.com"

        mock_provider = Mock()
        service = EmailService(provider=mock_provider)

        assert service.get_default_from_email() == "support@mail.example.com"

    @patch("leadr.infra.email.service.settings")
    def test_get_default_from_email_uses_noreply_by_default(self, mock_settings):
        """Test get_default_from_email uses noreply when FROM_EMAIL is default."""
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

        mock_provider = Mock()
        service = EmailService(provider=mock_provider)

        assert service.get_default_from_email() == "noreply@mg.leadr.gg"

    def test_validate_provider_config(self):
        """Test validate_provider_config method."""
        mock_provider = Mock()
        mock_provider.validate_config.return_value = True

        service = EmailService(provider=mock_provider)

        assert service.validate_provider_config() is True
        mock_provider.validate_config.assert_called_once()


@pytest.mark.asyncio
class TestEmailTemplateIntegration:
    """Integration tests that verify email templates work with service code.

    These tests use real template files (no mocking of _load_template) to catch
    mismatches between template variables and service code.
    """

    @patch("leadr.infra.email.service.settings")
    async def test_welcome_email_template_integration(
        self, mock_settings, db_session: AsyncSession
    ):
        """Verify welcome email template variables match service code."""
        mock_settings.ENV = "TEST"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-123"}

        service = EmailService(provider=mock_provider, db=db_session)
        # Don't mock _load_template - use real templates

        # Should not raise KeyError if template variables match service code
        await service.send_welcome_email(
            to="user@example.com",
            user_name="Test User",
            account_name="TestCo",
            account_slug="testco",
        )

        # Verify email body contains expected content from real template
        email_arg = mock_provider.send.call_args[0][0]
        assert "Test User" in email_arg.body
        assert "TestCo" in email_arg.body

    @patch("leadr.infra.email.service.settings")
    async def test_verification_code_template_integration(
        self, mock_settings, db_session: AsyncSession
    ):
        """Verify verification code template variables match service code."""
        mock_settings.ENV = "TEST"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-123"}

        service = EmailService(provider=mock_provider, db=db_session)

        # Should not raise KeyError
        await service.send_verification_code(
            to="user@example.com",
            code="ABC123",
        )

        email_arg = mock_provider.send.call_args[0][0]
        assert "ABC123" in email_arg.body

    @patch("leadr.infra.email.service.settings")
    async def test_notification_email_template_integration(
        self, mock_settings, db_session: AsyncSession
    ):
        """Verify notification email template variables match service code."""
        mock_settings.ENV = "TEST"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-123"}

        service = EmailService(provider=mock_provider, db=db_session)

        # Should not raise KeyError
        await service.send_notification_email(
            to="user@example.com",
            subject="Important Update",
            message="Your account has been upgraded!",
        )

        email_arg = mock_provider.send.call_args[0][0]
        assert "Your account has been upgraded!" in email_arg.body

    @patch("leadr.infra.email.service.settings")
    async def test_invite_email_template_integration(self, mock_settings, db_session: AsyncSession):
        """Verify invite email template variables match service code."""
        mock_settings.ENV = "TEST"
        mock_settings.TESTING_EMAIL = "test@leadr.gg"
        mock_settings.MAILGUN_DOMAIN = "mg.leadr.gg"
        mock_settings.default_from_email = "noreply@mg.leadr.gg"

        mock_provider = Mock()
        mock_provider.send.return_value = {"id": "msg-123"}

        service = EmailService(provider=mock_provider, db=db_session)

        # Should not raise KeyError
        await service.send_invite_email(
            to="invited@example.com",
            account_name="TestCo",
            code="XYZ789",
        )

        email_arg = mock_provider.send.call_args[0][0]
        assert "TestCo" in email_arg.body
        assert "XYZ789" in email_arg.body
