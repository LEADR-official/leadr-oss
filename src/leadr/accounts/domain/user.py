"""User domain model - STUB for RED commit."""

from leadr.common.domain.models import Entity, EntityID


class User(Entity):
    """User domain entity - STUB."""

    account_id: EntityID
    email: str
    display_name: str
