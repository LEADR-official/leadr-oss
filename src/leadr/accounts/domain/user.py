"""User domain model."""

from pydantic import EmailStr, Field, field_validator

from leadr.common.domain.ids import AccountID, UserID
from leadr.common.domain.models import Entity


class User(Entity):
    """User domain entity.

    Represents a user within an account (organization/team).
    Users are scoped to a specific account and have an email
    address and display name.

    Each user belongs to exactly one account, and users cannot be
    transferred between accounts. The email must be unique within
    an account.

    Superadmin users have elevated privileges and can access resources
    across all accounts in the system.
    """

    id: UserID = Field(
        frozen=True,
        default_factory=UserID,
        description="Unique user identifier",
    )
    account_id: AccountID = Field(
        frozen=True, description="ID of the account this user belongs to (immutable)"
    )
    email: EmailStr = Field(description="User's email address (validated format)")
    display_name: str = Field(description="User's display name (2-100 characters)")
    super_admin: bool = Field(
        default=False, description="Whether this user has superadmin privileges"
    )

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        """Validate display name length and format.

        Args:
            value: The display name to validate.

        Returns:
            The validated and trimmed display name.

        Raises:
            ValueError: If display name is empty, too short, or too long.
        """
        if not value or not value.strip():
            raise ValueError("Display name cannot be empty")
        if len(value) < 2:
            raise ValueError("Display name must be at least 2 characters")
        if len(value) > 100:
            raise ValueError("Display name must not exceed 100 characters")
        return value.strip()
