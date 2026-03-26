"""Webhook domain IDs."""

from leadr.common.domain.ids import PrefixedID


class WebhookEventID(PrefixedID):
    """Webhook event entity identifier."""

    prefix = "whe"
