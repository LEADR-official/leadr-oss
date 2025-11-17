"""API request and response models for users."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from leadr.accounts.domain.user import User
from leadr.common.domain.ids import AccountID, UserID


class UserCreateRequest(BaseModel):
    """Request model for creating a user."""

    account_id: AccountID = Field(description="ID of the account this user belongs to")
    email: EmailStr = Field(description="User's email address (must be valid email format)")
    display_name: str = Field(description="User's display name (2-100 characters)")


class UserUpdateRequest(BaseModel):
    """Request model for updating a user."""

    email: EmailStr | None = Field(default=None, description="Updated email address")
    display_name: str | None = Field(default=None, description="Updated display name")
    super_admin: bool | None = Field(
        default=None, description="Set superadmin privileges (true/false)"
    )
    deleted: bool | None = Field(default=None, description="Set to true to soft delete the user")


class UserResponse(BaseModel):
    """Response model for a user."""

    id: UserID = Field(description="Unique identifier for the user")
    account_id: AccountID = Field(description="ID of the account this user belongs to")
    email: str = Field(description="User's email address")
    display_name: str = Field(description="User's display name")
    super_admin: bool = Field(description="Whether this user has superadmin privileges")
    created_at: datetime = Field(description="Timestamp when the user was created (UTC)")
    updated_at: datetime = Field(description="Timestamp of last update (UTC)")

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        """Convert domain entity to response model.

        Args:
            user: The domain User entity to convert.

        Returns:
            UserResponse with all fields populated from the domain entity.
        """
        return cls(
            id=user.id,
            account_id=user.account_id,
            email=user.email,
            display_name=user.display_name,
            super_admin=user.super_admin,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
