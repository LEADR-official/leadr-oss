"""Tests for WebhookEventService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from leadr.infra.webhooks.domain.enums import WebhookProcessingStatus, WebhookSource
from leadr.infra.webhooks.domain.ids import WebhookEventID
from leadr.infra.webhooks.domain.webhook_event import WebhookEvent
from leadr.infra.webhooks.services.webhook_service import WebhookEventService


def make_event(
    external_id: str = "evt_123",
    status: WebhookProcessingStatus = WebhookProcessingStatus.PENDING,
    processed_at: datetime | None = None,
    error: str | None = None,
) -> WebhookEvent:
    """Create a test WebhookEvent."""
    return WebhookEvent(
        id=WebhookEventID(),
        external_event_id=external_id,
        source=WebhookSource.STRIPE,
        event_type="customer.subscription.created",
        processing_status=status,
        processed_at=processed_at,
        error=error,
    )


@pytest.mark.asyncio
class TestWebhookEventService:
    """Test WebhookEventService."""

    async def test_is_already_processed_returns_false_when_no_record(self, db_session) -> None:
        """Should return False when no record exists."""
        service = WebhookEventService(db_session)
        result = await service.is_already_processed(WebhookSource.STRIPE, "evt_not_exist")
        assert result is False

    async def test_is_already_processed_returns_false_for_pending(self, db_session) -> None:
        """Should return False for pending events."""
        service = WebhookEventService(db_session)
        await service.record_received(WebhookSource.STRIPE, "evt_pending_001", "invoice.paid")

        result = await service.is_already_processed(WebhookSource.STRIPE, "evt_pending_001")
        assert result is False

    async def test_is_already_processed_returns_true_for_processed(self, db_session) -> None:
        """Should return True for processed events."""
        service = WebhookEventService(db_session)
        event = await service.record_received(
            WebhookSource.STRIPE, "evt_processed_001", "invoice.paid"
        )
        await service.mark_processed(event.id)

        result = await service.is_already_processed(WebhookSource.STRIPE, "evt_processed_001")
        assert result is True

    async def test_is_already_processed_returns_false_for_failed(self, db_session) -> None:
        """Should return False for failed events (can be retried)."""
        service = WebhookEventService(db_session)
        event = await service.record_received(
            WebhookSource.STRIPE, "evt_failed_001", "invoice.paid"
        )
        await service.mark_failed(event.id, "Some error")

        result = await service.is_already_processed(WebhookSource.STRIPE, "evt_failed_001")
        assert result is False

    async def test_record_received_creates_pending_event(self, db_session) -> None:
        """Should create a WebhookEvent with PENDING status."""
        service = WebhookEventService(db_session)
        event = await service.record_received(
            WebhookSource.STRIPE, "evt_record_001", "checkout.session.completed"
        )

        assert event.external_event_id == "evt_record_001"
        assert event.source == WebhookSource.STRIPE
        assert event.event_type == "checkout.session.completed"
        assert event.processing_status == WebhookProcessingStatus.PENDING
        assert event.processed_at is None
        assert event.error is None

    async def test_mark_processed_updates_status(self, db_session) -> None:
        """Should mark event as processed."""
        service = WebhookEventService(db_session)
        event = await service.record_received(
            WebhookSource.STRIPE, "evt_mark_proc_001", "invoice.payment_succeeded"
        )

        await service.mark_processed(event.id)

        result = await service.is_already_processed(WebhookSource.STRIPE, "evt_mark_proc_001")
        assert result is True

    async def test_mark_failed_updates_status_and_error(self, db_session) -> None:
        """Should mark event as failed with error message."""
        service = WebhookEventService(db_session)
        event = await service.record_received(
            WebhookSource.STRIPE, "evt_mark_fail_001", "customer.subscription.updated"
        )

        await service.mark_failed(event.id, "Unexpected error occurred")

        result = await service.is_already_processed(WebhookSource.STRIPE, "evt_mark_fail_001")
        assert result is False
