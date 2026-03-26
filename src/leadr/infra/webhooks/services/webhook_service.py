"""Webhook event service for idempotency tracking."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.infra.webhooks.domain.enums import WebhookProcessingStatus, WebhookSource
from leadr.infra.webhooks.domain.ids import WebhookEventID
from leadr.infra.webhooks.domain.webhook_event import WebhookEvent
from leadr.infra.webhooks.services.repository import WebhookEventRepository


class WebhookEventService:
    """Service for tracking webhook event receipt and processing status.

    Provides idempotency by recording each event before processing and marking
    it as processed or failed afterwards. Callers should check is_already_processed()
    before performing domain logic to avoid duplicate side-effects.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service."""
        self._repository = WebhookEventRepository(session)

    async def is_already_processed(self, source: WebhookSource, external_event_id: str) -> bool:
        """Return True if this event has already been successfully processed.

        A PENDING or FAILED event is not considered processed — it can be retried.
        """
        event = await self._repository.get_by_source_and_external_id(source, external_event_id)
        if event is None:
            return False
        return event.processing_status == WebhookProcessingStatus.PROCESSED

    async def record_received(
        self, source: WebhookSource, external_event_id: str, event_type: str
    ) -> WebhookEvent:
        """Record that a webhook event has been received (status: PENDING)."""
        event = WebhookEvent(
            external_event_id=external_event_id,
            source=source,
            event_type=event_type,
            processing_status=WebhookProcessingStatus.PENDING,
        )
        return await self._repository.create(event)

    async def mark_processed(
        self, event_id: WebhookEventID, processed_at: datetime | None = None
    ) -> None:
        """Mark a webhook event as successfully processed."""
        if processed_at is None:
            processed_at = datetime.now(UTC)
        await self._repository.mark_processed(event_id, processed_at)

    async def mark_failed(self, event_id: WebhookEventID, error: str) -> None:
        """Mark a webhook event as failed with an error message."""
        await self._repository.mark_failed(event_id, error)
