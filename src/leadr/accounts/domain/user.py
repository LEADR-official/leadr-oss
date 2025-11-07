"""User domain model."""

from pydantic import EmailStr, Field, field_validator

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

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        """Validate display name length and format."""
        if not value or not value.strip():
            raise ValueError("Display name cannot be empty")
        if len(value) < 2:
            raise ValueError("Display name must be at least 2 characters")
        if len(value) > 100:
            raise ValueError("Display name must not exceed 100 characters")
        return value.strip()
