"""Email infrastructure domain with factory functions for easy integration."""

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.config import settings
from leadr.infra.email.adapters.mailgun import MailgunEmailProvider
from leadr.infra.email.adapters.smtp import SMTPEmailProvider
from leadr.infra.email.domain.exceptions import (
    EmailError,
    EmailSendError,
    EmailValidationError,
)
from leadr.infra.email.domain.interfaces import EmailProvider
from leadr.infra.email.domain.models import Email, EmailPriority, EmailStatus
from leadr.infra.email.service import EmailService


def create_email_service(
    provider: EmailProvider | None = None,
    db: AsyncSession | None = None,
) -> EmailService:
    """Create an email service with the specified or default provider.

    Args:
        provider: Email provider instance. If None, uses MailgunEmailProvider
                 in production or SMTPEmailProvider in TEST environment.
        db: Optional database session for persisting email records.

    Returns:
        EmailService instance ready for use.

    Example:
        # Use default provider (Mailgun in prod, SMTP in test)
        email_service = create_email_service()

        # With database persistence
        email_service = create_email_service(db=session)

        # Use custom provider
        custom_provider = MyCustomEmailProvider()
        email_service = create_email_service(provider=custom_provider)
    """
    if provider is None:
        if settings.ENV == "TEST":
            provider = SMTPEmailProvider()
        else:
            provider = MailgunEmailProvider()

    return EmailService(provider=provider, db=db, validate_on_init=False)


# Export main classes and functions for easy import
__all__ = [
    "Email",
    "EmailStatus",
    "EmailPriority",
    "EmailProvider",
    "EmailError",
    "EmailValidationError",
    "EmailSendError",
    "EmailService",
    "MailgunEmailProvider",
    "SMTPEmailProvider",
    "create_email_service",
]
