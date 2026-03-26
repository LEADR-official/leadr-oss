"""Tests for webhook domain enums."""

from leadr.infra.webhooks.domain.enums import WebhookProcessingStatus, WebhookSource


class TestWebhookSource:
    """Test WebhookSource enum."""

    def test_stripe_value(self) -> None:
        """Should have 'stripe' value."""
        assert WebhookSource.STRIPE.value == "stripe"

    def test_is_string_enum(self) -> None:
        """Should be usable as a string value."""
        assert WebhookSource.STRIPE == "stripe"


class TestWebhookProcessingStatus:
    """Test WebhookProcessingStatus enum."""

    def test_pending_value(self) -> None:
        """Should have 'pending' value."""
        assert WebhookProcessingStatus.PENDING.value == "pending"

    def test_processed_value(self) -> None:
        """Should have 'processed' value."""
        assert WebhookProcessingStatus.PROCESSED.value == "processed"

    def test_failed_value(self) -> None:
        """Should have 'failed' value."""
        assert WebhookProcessingStatus.FAILED.value == "failed"
