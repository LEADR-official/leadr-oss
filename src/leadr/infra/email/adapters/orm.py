"""Email ORM models."""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from leadr.common.domain.ids import EmailID
from leadr.common.orm import Base
from leadr.infra.email.domain.models import Email, EmailPriority, EmailStatus


class EmailStatusEnum(str, enum.Enum):
    """Email status enum for database."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class EmailPriorityEnum(str, enum.Enum):
    """Email priority enum for database."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EmailORM(Base):
    """Email ORM model.

    Represents an email in the database for tracking and auditing purposes.
    Maps to the emails table.
    """

    __tablename__ = "emails"

    # Core email fields
    to: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    from_email: Mapped[str | None] = mapped_column(String, nullable=True)
    reply_to: Mapped[str | None] = mapped_column(String, nullable=True)
    cc: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )
    bcc: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )
    priority: Mapped[EmailPriorityEnum] = mapped_column(
        Enum(
            EmailPriorityEnum,
            name="email_priority",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=EmailPriorityEnum.NORMAL,
        server_default="normal",
    )
    status: Mapped[EmailStatusEnum] = mapped_column(
        Enum(
            EmailStatusEnum,
            name="email_status",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=EmailStatusEnum.PENDING,
        server_default="pending",
        index=True,
    )
    template_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Provider tracking
    provider_message_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    provider_response: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Status tracking
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (Index("ix_emails_created_at", "created_at"),)

    @classmethod
    def from_domain(cls, domain: Email) -> "EmailORM":
        """Convert domain entity to ORM model.

        Args:
            domain: The domain entity to convert.

        Returns:
            The ORM model instance.
        """
        return cls(
            id=domain.id.uuid,
            to=domain.to,
            subject=domain.subject,
            body=domain.body,
            from_email=domain.from_email,
            reply_to=domain.reply_to,
            cc=domain.cc,
            bcc=domain.bcc,
            priority=EmailPriorityEnum(domain.priority.value),
            status=EmailStatusEnum(domain.status.value),
            template_data=domain.template_data,
            provider_message_id=domain.provider_message_id,
            provider_response=domain.provider_response,
            sent_at=domain.sent_at,
            failed_at=domain.failed_at,
            error_message=domain.error_message,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
            deleted_at=domain.deleted_at,
        )

    def to_domain(self) -> Email:
        """Convert ORM model to domain entity.

        Returns:
            The domain entity instance.
        """
        return Email(
            id=EmailID(self.id),
            to=self.to,
            subject=self.subject,
            body=self.body,
            from_email=self.from_email,
            reply_to=self.reply_to,
            cc=self.cc,
            bcc=self.bcc,
            priority=EmailPriority(self.priority.value),
            status=EmailStatus(self.status.value),
            template_data=self.template_data,
            provider_message_id=self.provider_message_id,
            provider_response=self.provider_response,
            sent_at=self.sent_at,
            failed_at=self.failed_at,
            error_message=self.error_message,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )
