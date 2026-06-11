"""Tests for webhook service dependencies."""

from unittest.mock import MagicMock

import pytest

from leadr.infra.webhooks.services.dependencies import get_webhook_event_service
from leadr.infra.webhooks.services.webhook_service import WebhookEventService


@pytest.mark.asyncio
async def test_get_webhook_event_service_returns_service():
    """Test that get_webhook_event_service returns a WebhookEventService instance."""
    mock_db = MagicMock()
    service = await get_webhook_event_service(mock_db)
    assert isinstance(service, WebhookEventService)
