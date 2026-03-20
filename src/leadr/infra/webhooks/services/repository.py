"""Webhook event repository."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.infra.webhooks.adapters.orm import WebhookEventORM, WebhookProcessingStatusEnum
from leadr.infra.webhooks.domain.enums import WebhookProcessingStatus, WebhookSource
from leadr.infra.webhooks.domain.ids import WebhookEventID
from leadr.infra.webhooks.domain.webhook_event import WebhookEvent


class WebhookEventRepository:
    """Repository for WebhookEvent entities.

    Handles creation and status tracking of incoming webhook events.
    Uses direct SQL updates for status transitions (mark_processed, mark_failed).
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository."""
        self._session = session

    async def create(self, event: WebhookEvent) -> WebhookEvent:
        """Persist a new webhook event record."""
        orm = WebhookEventORM.from_domain(event)
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return orm.to_domain()

    async def get_by_source_and_external_id(
        self, source: WebhookSource, external_event_id: str
    ) -> WebhookEvent | None:
        """Look up a webhook event by (source, external_event_id) — the idempotency key."""
        stmt = select(WebhookEventORM).where(
            WebhookEventORM.source == source.value,
            WebhookEventORM.external_event_id == external_event_id,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return orm.to_domain() if orm is not None else None

    async def mark_processed(
        self, event_id: WebhookEventID, processed_at: datetime | None = None
    ) -> None:
        """Update the event to PROCESSED status."""
        if processed_at is None:
            processed_at = datetime.now(UTC)
        stmt = (
            update(WebhookEventORM)
            .where(WebhookEventORM.id == event_id.uuid)
            .values(
                processing_status=WebhookProcessingStatusEnum.PROCESSED,
                processed_at=processed_at,
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def mark_failed(self, event_id: WebhookEventID, error: str) -> None:
        """Update the event to FAILED status with an error message."""
        stmt = (
            update(WebhookEventORM)
            .where(WebhookEventORM.id == event_id.uuid)
            .values(
                processing_status=WebhookProcessingStatusEnum.FAILED,
                error=error,
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
