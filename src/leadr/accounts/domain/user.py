"""User domain model."""

from pydantic import EmailStr, Field

from leadr.common.domain.models import Entity, EntityID


class User(Entity):
    """User domain entity.

    Represents a user within an account (organization/team).
    Users are scoped to a specific account and have an email
    address and display name.
    """

    account_id: EntityID = Field(frozen=True)
    email: EmailStr
    display_name: str
