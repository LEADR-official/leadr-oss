"""Webhook event ORM model."""

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from leadr.common.orm import ImmutableBase
from leadr.infra.webhooks.domain.enums import WebhookProcessingStatus, WebhookSource
from leadr.infra.webhooks.domain.ids import WebhookEventID
from leadr.infra.webhooks.domain.webhook_event import WebhookEvent


class WebhookSourceEnum(str, enum.Enum):
    """Webhook source enum for database."""

    STRIPE = "stripe"


class WebhookProcessingStatusEnum(str, enum.Enum):
    """Webhook processing status enum for database."""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class WebhookEventORM(ImmutableBase):
    """Webhook event ORM model.

    Tracks received webhook events for idempotency and audit purposes.
    Uses a unique constraint on (source, external_event_id) to prevent duplicate processing.
    """

    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_event_id",
            name="uq_webhook_events_source_external_id",
        ),
        Index(
            "ix_webhook_events_source_type_created",
            "source",
            "event_type",
            "created_at",
        ),
    )

    external_event_id: Mapped[str] = mapped_column(String(256), nullable=False)
    source: Mapped[WebhookSourceEnum] = mapped_column(
        Enum(
            WebhookSourceEnum,
            name="webhook_source",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    processing_status: Mapped[WebhookProcessingStatusEnum] = mapped_column(
        Enum(
            WebhookProcessingStatusEnum,
            name="webhook_processing_status",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=WebhookProcessingStatusEnum.PENDING,
        server_default="pending",
        index=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_domain(self) -> WebhookEvent:
        """Convert ORM model to domain entity."""
        return WebhookEvent(
            id=WebhookEventID(self.id),
            external_event_id=self.external_event_id,
            source=WebhookSource(self.source.value),
            event_type=self.event_type,
            processing_status=WebhookProcessingStatus(self.processing_status.value),
            processed_at=self.processed_at,
            error=self.error,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(cls, entity: WebhookEvent) -> "WebhookEventORM":
        """Convert domain entity to ORM model."""
        return cls(
            id=entity.id.uuid,
            external_event_id=entity.external_event_id,
            source=WebhookSourceEnum(entity.source.value),
            event_type=entity.event_type,
            processing_status=WebhookProcessingStatusEnum(entity.processing_status.value),
            processed_at=entity.processed_at,
            error=entity.error,
            created_at=entity.created_at,
        )
