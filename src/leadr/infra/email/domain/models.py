"""Email domain models."""

import re
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from leadr.common.domain.ids import EmailID
from leadr.common.domain.models import Entity
from leadr.infra.email.domain.exceptions import EmailValidationError


class EmailStatus(str, Enum):
    """Email status enumeration."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class EmailPriority(str, Enum):
    """Email priority enumeration."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Email(Entity):
    """Email domain entity."""

    id: EmailID = Field(
        frozen=True,
        default_factory=EmailID,
        description="Unique email identifier",
    )
    to: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body content")
    from_email: str | None = Field(None, description="Sender email address")
    reply_to: str | None = Field(None, description="Reply-to email address")
    cc: list[str] = Field(default_factory=list, description="CC recipients")
    bcc: list[str] = Field(default_factory=list, description="BCC recipients")
    priority: EmailPriority = Field(default=EmailPriority.NORMAL, description="Email priority")
    status: EmailStatus = Field(default=EmailStatus.PENDING, description="Email status")
    template_data: dict[str, Any] | None = Field(
        None, description="Template data for email rendering"
    )

    # Provider tracking fields
    provider_message_id: str | None = Field(None, description="Provider message ID")
    provider_response: dict[str, Any] | None = Field(None, description="Provider API response")

    # Status tracking
    sent_at: datetime | None = Field(None, description="Time email was sent")
    failed_at: datetime | None = Field(None, description="Time email failed")
    error_message: str | None = Field(None, description="Error message if failed")

    @field_validator("to")
    @classmethod
    def validate_to_email(cls, v):
        """Validate recipient email address."""
        if not cls._is_valid_email(v):
            raise EmailValidationError(f"Invalid email address: {v}")
        return v

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v):
        """Validate email subject."""
        if not v or not v.strip():
            raise EmailValidationError("Subject cannot be empty")
        return v.strip()

    @field_validator("body")
    @classmethod
    def validate_body(cls, v):
        """Validate email body."""
        if not v or not v.strip():
            raise EmailValidationError("Body cannot be empty")
        return v.strip()

    @field_validator("from_email")
    @classmethod
    def validate_from_email(cls, v):
        """Validate sender email address."""
        if v and not cls._is_valid_email(v):
            raise EmailValidationError(f"Invalid from email address: {v}")
        return v

    @field_validator("reply_to")
    @classmethod
    def validate_reply_to(cls, v):
        """Validate reply-to email address."""
        if v and not cls._is_valid_email(v):
            raise EmailValidationError(f"Invalid reply-to email address: {v}")
        return v

    @field_validator("cc")
    @classmethod
    def validate_cc_emails(cls, v):
        """Validate CC email addresses."""
        for email in v:
            if not cls._is_valid_email(email):
                raise EmailValidationError(f"Invalid CC email address: {email}")
        return v

    @field_validator("bcc")
    @classmethod
    def validate_bcc_emails(cls, v):
        """Validate BCC email addresses."""
        for email in v:
            if not cls._is_valid_email(email):
                raise EmailValidationError(f"Invalid BCC email address: {email}")
        return v

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Simple email validation."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    @classmethod
    def create(
        cls,
        to: str,
        subject: str,
        body: str,
        from_email: str | None = None,
        reply_to: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        priority: EmailPriority = EmailPriority.NORMAL,
        template_data: dict[str, Any] | None = None,
    ) -> "Email":
        """Create a new Email entity."""
        now = datetime.now(UTC)
        return cls(
            to=to,
            subject=subject,
            body=body,
            from_email=from_email,
            reply_to=reply_to,
            cc=cc or [],
            bcc=bcc or [],
            priority=priority,
            template_data=template_data,
            provider_message_id=None,
            provider_response=None,
            sent_at=None,
            failed_at=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )

    def mark_as_sent(self, provider_message_id: str, provider_response: dict[str, Any]) -> None:
        """Mark email as sent."""
        self.status = EmailStatus.SENT
        self.provider_message_id = provider_message_id
        self.provider_response = provider_response
        self.sent_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def mark_as_failed(
        self, error_message: str, provider_response: dict[str, Any] | None = None
    ) -> None:
        """Mark email as failed."""
        self.status = EmailStatus.FAILED
        self.error_message = error_message
        self.provider_response = provider_response
        self.failed_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def mark_as_delivered(self) -> None:
        """Mark email as delivered."""
        self.status = EmailStatus.DELIVERED
        self.updated_at = datetime.now(UTC)
