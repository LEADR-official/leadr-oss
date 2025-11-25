"""Email service with dependency injection and convenience methods."""

import logging
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.config import settings
from leadr.infra.email.adapters.repositories import EmailRepository
from leadr.infra.email.domain.exceptions import EmailSendError
from leadr.infra.email.domain.interfaces import EmailProvider
from leadr.infra.email.domain.models import Email, EmailPriority

logger = logging.getLogger(__name__)


class EmailService:
    """Email service with dependency injection for testing and flexibility."""

    def __init__(
        self,
        provider: EmailProvider,
        db: AsyncSession | None = None,
        validate_on_init: bool = False,
    ):
        """Initialize email service with provider dependency injection.

        Args:
            provider: Email provider implementation (e.g., Mailgun).
            db: Optional database session for persisting email records.
            validate_on_init: Whether to validate provider config on initialization.
        """
        self.provider = provider
        self.db = db
        self.repository = EmailRepository(db) if db else None
        self.templates_dir = Path(__file__).parent / "templates"
        self._template_cache: dict[str, str] = {}

        if validate_on_init and not self.validate_provider_config():
            raise ValueError("Email provider configuration is invalid")

    def _load_template(self, template_name: str) -> str:
        """Load email template from file with caching.

        Args:
            template_name: Name of the template file (without .txt extension).

        Returns:
            Template content as string.

        Raises:
            FileNotFoundError: If template file doesn't exist.
        """
        if template_name not in self._template_cache:
            template_path = self.templates_dir / f"{template_name}.txt"
            self._template_cache[template_name] = template_path.read_text(encoding="utf-8")
        return self._template_cache[template_name]

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: str | None = None,
        reply_to: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        priority: EmailPriority = EmailPriority.NORMAL,
        template_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an email using the configured provider."""

        # Override so we never send to non-approved emails from DEV
        if settings.ENV in (
            "DEV",
            "TEST",
        ):
            to = settings.TESTING_EMAIL

        if from_email is not None:
            logger.warning("From email cannot be customised")
        from_email = f"postmaster@{settings.MAILGUN_DOMAIN}"
        reply_to = from_email

        # Create email domain object
        email = Email.create(
            to=to,
            subject=subject,
            body=body,
            from_email=from_email,
            reply_to=reply_to,
            cc=cc,
            bcc=bcc,
            priority=priority,
            template_data=template_data,
        )

        # Save email to database with PENDING status
        if self.repository and self.db:
            await self.repository.create(email)
            await self.db.commit()

        logger.info("Sending email: %s\tTo: %s\nFrom: %s", subject, to, from_email)

        try:
            response = self.provider.send(email)
            logger.debug(response)
            email.mark_as_sent(
                provider_message_id=response.get("message_id", response.get("id", "unknown")),
                provider_response=response,
            )

            # Update email status in database
            if self.repository and self.db:
                await self.repository.update(email)
                await self.db.commit()

            return response
        except EmailSendError as e:
            email.mark_as_failed(str(e), e.provider_response)

            # Update email status in database
            if self.repository and self.db:
                await self.repository.update(email)
                await self.db.commit()

            raise

    async def send_verification_code(self, to: str, code: str) -> dict[str, Any]:
        """Send a verification code email for LEADR registration."""
        subject = "Verify your LEADR account"
        template = self._load_template("verification_code")
        body = template.format(code=code)

        return await self.send_email(
            to=to,
            subject=subject,
            body=body,
            priority=EmailPriority.HIGH,
        )

    async def send_welcome_email(
        self,
        to: str,
        account_name: str,
        account_slug: str,
        from_email: str | None = None,
    ) -> dict[str, Any]:
        """Send a welcome email after successful LEADR registration."""
        subject = f"Welcome to LEADR, {account_name}!"
        template = self._load_template("welcome")
        body = template.format(account_name=account_name)

        return await self.send_email(
            to=to,
            subject=subject,
            body=body,
            from_email=from_email,
            priority=EmailPriority.NORMAL,
        )

    async def send_notification_email(
        self,
        to: str,
        subject: str,
        message: str,
        priority: EmailPriority = EmailPriority.NORMAL,
        from_email: str | None = None,
    ) -> dict[str, Any]:
        """Send a notification email."""
        template = self._load_template("notification")
        body = template.format(message=message)

        return await self.send_email(
            to=to, subject=subject, body=body, from_email=from_email, priority=priority
        )

    def get_default_from_email(self) -> str:
        """Get default from email address."""
        # This could be configurable or derived from provider settings
        return "noreply@leadr.gg"

    def validate_provider_config(self) -> bool:
        """Validate the email provider configuration."""
        return self.provider.validate_config()
