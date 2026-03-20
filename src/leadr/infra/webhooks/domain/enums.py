"""Webhook domain enums."""

from enum import Enum


class WebhookSource(str, Enum):
    """Source system that sent the webhook."""

    STRIPE = "stripe"


class WebhookProcessingStatus(str, Enum):
    """Processing status of a received webhook event."""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
