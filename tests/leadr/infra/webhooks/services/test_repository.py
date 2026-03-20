"""Tests for WebhookEventRepository."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from leadr.infra.webhooks.domain.enums import WebhookProcessingStatus, WebhookSource
from leadr.infra.webhooks.domain.webhook_event import WebhookEvent
from leadr.infra.webhooks.services.repository import WebhookEventRepository


@pytest.mark.asyncio
class TestWebhookEventRepository:
    """Test WebhookEventRepository."""

    async def test_create_and_get(self, db_session) -> None:
        """Should create and retrieve a webhook event."""
        repo = WebhookEventRepository(db_session)
        event = WebhookEvent(
            external_event_id="evt_test_001",
            source=WebhookSource.STRIPE,
            event_type="customer.subscription.created",
            processing_status=WebhookProcessingStatus.PENDING,
        )

        created = await repo.create(event)

        retrieved = await repo.get_by_source_and_external_id(WebhookSource.STRIPE, "evt_test_001")
        assert retrieved is not None
        assert retrieved.external_event_id == "evt_test_001"
        assert retrieved.source == WebhookSource.STRIPE
        assert retrieved.event_type == "customer.subscription.created"
        assert retrieved.processing_status == WebhookProcessingStatus.PENDING
        assert retrieved.id == created.id

    async def test_get_nonexistent_returns_none(self, db_session) -> None:
        """Should return None for nonexistent event."""
        repo = WebhookEventRepository(db_session)
        result = await repo.get_by_source_and_external_id(
            WebhookSource.STRIPE, "evt_does_not_exist"
        )
        assert result is None

    async def test_unique_constraint_on_source_and_external_id(self, db_session) -> None:
        """Should enforce uniqueness on (source, external_event_id)."""
        repo = WebhookEventRepository(db_session)
        event = WebhookEvent(
            external_event_id="evt_duplicate_001",
            source=WebhookSource.STRIPE,
            event_type="checkout.session.completed",
            processing_status=WebhookProcessingStatus.PENDING,
        )
        await repo.create(event)

        duplicate = WebhookEvent(
            external_event_id="evt_duplicate_001",
            source=WebhookSource.STRIPE,
            event_type="checkout.session.completed",
            processing_status=WebhookProcessingStatus.PENDING,
        )
        with pytest.raises(IntegrityError):
            await repo.create(duplicate)

    async def test_mark_processed(self, db_session) -> None:
        """Should update status to PROCESSED and set processed_at."""
        repo = WebhookEventRepository(db_session)
        event = WebhookEvent(
            external_event_id="evt_mark_processed",
            source=WebhookSource.STRIPE,
            event_type="invoice.payment_succeeded",
            processing_status=WebhookProcessingStatus.PENDING,
        )
        created = await repo.create(event)

        processed_at = datetime.now(UTC)
        await repo.mark_processed(created.id, processed_at)

        retrieved = await repo.get_by_source_and_external_id(
            WebhookSource.STRIPE, "evt_mark_processed"
        )
        assert retrieved is not None
        assert retrieved.processing_status == WebhookProcessingStatus.PROCESSED
        assert retrieved.processed_at is not None

    async def test_mark_failed(self, db_session) -> None:
        """Should update status to FAILED and store error message."""
        repo = WebhookEventRepository(db_session)
        event = WebhookEvent(
            external_event_id="evt_mark_failed",
            source=WebhookSource.STRIPE,
            event_type="customer.subscription.updated",
            processing_status=WebhookProcessingStatus.PENDING,
        )
        created = await repo.create(event)

        await repo.mark_failed(created.id, "Something went wrong")

        retrieved = await repo.get_by_source_and_external_id(
            WebhookSource.STRIPE, "evt_mark_failed"
        )
        assert retrieved is not None
        assert retrieved.processing_status == WebhookProcessingStatus.FAILED
        assert retrieved.error == "Something went wrong"
