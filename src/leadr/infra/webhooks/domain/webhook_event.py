"""WebhookEvent domain entity."""

from datetime import datetime

from pydantic import Field

from leadr.common.domain.models import ImmutableEntity
from leadr.infra.webhooks.domain.enums import WebhookProcessingStatus, WebhookSource
from leadr.infra.webhooks.domain.ids import WebhookEventID


class WebhookEvent(ImmutableEntity):
    """Represents a received webhook event from an external system.

    Tracks idempotency and processing status for external webhook events.
    Immutable after creation — processing state is updated via repository methods.
    """

    id: WebhookEventID = Field(
        frozen=True,
        default_factory=WebhookEventID,
        description="Unique identifier for this webhook event record",
    )
    external_event_id: str = Field(
        description="The event ID from the external system (e.g. Stripe event ID)",
    )
    source: WebhookSource = Field(
        description="The external system that sent this webhook",
    )
    event_type: str = Field(
        description="The event type (e.g. 'customer.subscription.created')",
    )
    processing_status: WebhookProcessingStatus = Field(
        default=WebhookProcessingStatus.PENDING,
        description="Current processing status of this event",
    )
    processed_at: datetime | None = Field(
        default=None,
        description="Timestamp when event was successfully processed (UTC)",
    )
    error: str | None = Field(
        default=None,
        description="Error message if processing failed",
    )
