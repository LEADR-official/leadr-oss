"""Webhook event service dependency injection."""

from typing import Annotated

from fastapi import Depends

from leadr.common.dependencies import DatabaseSession
from leadr.infra.webhooks.services.webhook_service import WebhookEventService


async def get_webhook_event_service(db: DatabaseSession) -> WebhookEventService:
    """Get WebhookEventService dependency."""
    return WebhookEventService(db)


WebhookEventServiceDep = Annotated[WebhookEventService, Depends(get_webhook_event_service)]
