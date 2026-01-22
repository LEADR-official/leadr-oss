"""SMTP email adapter implementation for testing."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from leadr.config import settings
from leadr.infra.email.domain.exceptions import EmailSendError
from leadr.infra.email.domain.interfaces import EmailProvider
from leadr.infra.email.domain.models import Email


class SMTPEmailProvider(EmailProvider):
    """SMTP email provider implementation for development/testing."""

    def __init__(self, host: str | None = None, port: int | None = None):
        """Initialize SMTP provider with configuration.

        Args:
            host: SMTP server hostname (defaults to settings.SMTP_HOST or localhost)
            port: SMTP server port (defaults to settings.SMTP_PORT or 1025)
        """
        self.host = host or getattr(settings, "SMTP_HOST", "localhost")
        self.port = port or getattr(settings, "SMTP_PORT", 1025)

    def validate_config(self) -> bool:
        """Validate SMTP configuration."""
        return bool(self.host and self.port)

    def send(self, email: Email) -> dict[str, Any]:
        """Send email via SMTP."""
        if not self.validate_config():
            raise EmailSendError("Invalid SMTP configuration")

        try:
            # Create MIME message
            msg = MIMEMultipart()
            msg["From"] = email.from_email or settings.default_from_email
            msg["To"] = email.to
            msg["Subject"] = email.subject

            if email.reply_to:
                msg["Reply-To"] = email.reply_to

            if email.cc:
                msg["Cc"] = ", ".join(email.cc)

            if email.bcc:
                msg["Bcc"] = ", ".join(email.bcc)

            # Attach body
            msg.attach(MIMEText(email.body, "plain"))

            # Send via SMTP
            with smtplib.SMTP(self.host, self.port) as server:
                server.send_message(msg)

            # Return response in similar format to Mailgun
            return {
                "id": f"smtp-{email.id.uuid}",
                "message": "Queued. Thank you.",
            }

        except smtplib.SMTPException as e:
            raise EmailSendError(f"SMTP error: {str(e)}", None) from e
        except Exception as e:
            raise EmailSendError(f"Unexpected error sending email: {str(e)}", None) from e
