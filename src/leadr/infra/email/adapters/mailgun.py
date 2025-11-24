"""Mailgun email adapter implementation."""

from typing import Any

from mailgun.client import ApiError, Client

from leadr.config import settings
from leadr.infra.email.domain.exceptions import EmailSendError
from leadr.infra.email.domain.interfaces import EmailProvider
from leadr.infra.email.domain.models import Email, EmailPriority


class MailgunEmailProvider(EmailProvider):
    """Mailgun email service provider implementation."""

    def __init__(self):
        """Initialize Mailgun provider with settings configuration."""
        self.api_key = settings.MAILGUN_API_KEY
        self.domain = settings.MAILGUN_DOMAIN
        self.client = Client(auth=("api", self.api_key))

    def validate_config(self) -> bool:
        """Validate Mailgun configuration."""
        return bool(self.api_key and self.api_key.strip() and self.domain and self.domain.strip())

    def send(self, email: Email) -> dict[str, Any]:
        """Send email via Mailgun API."""
        if not self.validate_config():
            raise EmailSendError("Invalid Mailgun configuration")

        message_data = self._build_message_data(email)

        try:
            response = self.client.messages.create(data=message_data, domain=self.domain)
            return response.json()
        except ApiError as e:
            raise EmailSendError(f"Mailgun API error: {str(e)}", None) from e
        except Exception as e:
            raise EmailSendError(f"Unexpected error sending email: {str(e)}", None) from e

    def _build_message_data(self, email: Email) -> dict[str, str]:
        """Build message data for Mailgun API request."""
        message_data = {
            "to": email.to,
            "from": email.from_email or f"noreply@{self.domain}",
            "subject": email.subject,
            "text": email.body,
        }

        # Add optional fields
        if email.reply_to:
            message_data["h:Reply-To"] = email.reply_to

        if email.cc:
            message_data["cc"] = ",".join(email.cc)

        if email.bcc:
            message_data["bcc"] = ",".join(email.bcc)

        # Add priority as tag
        if email.priority != EmailPriority.NORMAL:
            message_data["o:tag"] = self._priority_to_tag(email.priority)

        return message_data

    def _priority_to_tag(self, priority: EmailPriority) -> str:
        """Convert email priority to Mailgun tag."""
        return priority.value
