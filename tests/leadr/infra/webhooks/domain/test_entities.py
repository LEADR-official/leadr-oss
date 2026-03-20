"""Tests for webhook domain entities."""

from datetime import UTC, datetime

from leadr.infra.webhooks.domain.enums import WebhookProcessingStatus, WebhookSource
from leadr.infra.webhooks.domain.ids import WebhookEventID
from leadr.infra.webhooks.domain.webhook_event import WebhookEvent


class TestWebhookEvent:
    """Test WebhookEvent entity."""

    def test_create_with_required_fields(self) -> None:
        """Should create entity with required fields."""
        event = WebhookEvent(
            external_event_id="evt_123",
            source=WebhookSource.STRIPE,
            event_type="customer.subscription.created",
            processing_status=WebhookProcessingStatus.PENDING,
        )
        assert event.external_event_id == "evt_123"
        assert event.source == WebhookSource.STRIPE
        assert event.event_type == "customer.subscription.created"
        assert event.processing_status == WebhookProcessingStatus.PENDING
        assert event.processed_at is None
        assert event.error is None

    def test_auto_generates_id(self) -> None:
        """Should auto-generate a WebhookEventID."""
        event = WebhookEvent(
            external_event_id="evt_123",
            source=WebhookSource.STRIPE,
            event_type="checkout.session.completed",
            processing_status=WebhookProcessingStatus.PENDING,
        )
        assert isinstance(event.id, WebhookEventID)
        assert str(event.id).startswith("whe_")

    def test_auto_generates_created_at(self) -> None:
        """Should auto-generate created_at timestamp."""
        event = WebhookEvent(
            external_event_id="evt_123",
            source=WebhookSource.STRIPE,
            event_type="checkout.session.completed",
            processing_status=WebhookProcessingStatus.PENDING,
        )
        assert event.created_at is not None
        assert event.created_at.tzinfo is not None

    def test_with_processed_at(self) -> None:
        """Should store processed_at timestamp."""
        now = datetime.now(UTC)
        event = WebhookEvent(
            external_event_id="evt_123",
            source=WebhookSource.STRIPE,
            event_type="checkout.session.completed",
            processing_status=WebhookProcessingStatus.PROCESSED,
            processed_at=now,
        )
        assert event.processed_at == now
        assert event.processing_status == WebhookProcessingStatus.PROCESSED

    def test_with_error(self) -> None:
        """Should store error message."""
        event = WebhookEvent(
            external_event_id="evt_123",
            source=WebhookSource.STRIPE,
            event_type="checkout.session.completed",
            processing_status=WebhookProcessingStatus.FAILED,
            error="Processing failed: unexpected state",
        )
        assert event.error == "Processing failed: unexpected state"
        assert event.processing_status == WebhookProcessingStatus.FAILED

    def test_equality_based_on_id(self) -> None:
        """Should compare entities by ID."""
        event_id = WebhookEventID()
        event1 = WebhookEvent(
            id=event_id,
            external_event_id="evt_123",
            source=WebhookSource.STRIPE,
            event_type="checkout.session.completed",
            processing_status=WebhookProcessingStatus.PENDING,
        )
        event2 = WebhookEvent(
            id=event_id,
            external_event_id="evt_456",
            source=WebhookSource.STRIPE,
            event_type="invoice.payment_succeeded",
            processing_status=WebhookProcessingStatus.PROCESSED,
        )
        assert event1 == event2
