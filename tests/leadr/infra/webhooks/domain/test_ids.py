"""Tests for webhook domain IDs."""

from uuid import UUID

import pytest

from leadr.infra.webhooks.domain.ids import WebhookEventID


class TestWebhookEventID:
    """Test WebhookEventID."""

    def test_prefix(self) -> None:
        """Should have 'whe' prefix."""
        event_id = WebhookEventID()
        assert str(event_id).startswith("whe_")

    def test_generates_unique_ids(self) -> None:
        """Should generate unique IDs."""
        id1 = WebhookEventID()
        id2 = WebhookEventID()
        assert id1 != id2

    def test_parses_from_string(self) -> None:
        """Should parse from prefixed string."""
        event_id = WebhookEventID()
        parsed = WebhookEventID(str(event_id))
        assert parsed == event_id

    def test_wraps_uuid(self) -> None:
        """Should wrap a UUID."""
        uuid = UUID("12345678-1234-5678-1234-567812345678")
        event_id = WebhookEventID(uuid)
        assert event_id.uuid == uuid

    def test_invalid_prefix_raises(self) -> None:
        """Should raise ValueError for wrong prefix."""
        with pytest.raises(ValueError, match="Invalid prefix"):
            WebhookEventID("acc_12345678-1234-5678-1234-567812345678")
