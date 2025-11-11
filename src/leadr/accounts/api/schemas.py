"""API request and response models for accounts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.domain.user import User


# Account models
class AccountCreateRequest(BaseModel):
    """Request model for creating an account."""

    name: str = Field(description="Account name (2-100 characters)")
    slug: str = Field(
        description="URL-friendly identifier for the account (lowercase, alphanumeric, hyphens)"
    )


class AccountUpdateRequest(BaseModel):
    """Request model for updating an account."""

    name: str | None = Field(default=None, description="Updated account name")
    slug: str | None = Field(default=None, description="Updated URL-friendly identifier")
    status: AccountStatus | None = Field(
        default=None, description="Account status (active, suspended, deleted)"
    )
    deleted: bool | None = Field(default=None, description="Set to true to soft delete the account")


class AccountResponse(BaseModel):
    """Response model for an account."""

    id: UUID = Field(description="Unique identifier for the account")
    name: str = Field(description="Account name")
    slug: str = Field(description="URL-friendly identifier")
    status: AccountStatus = Field(description="Current account status")
    created_at: datetime = Field(description="Timestamp when the account was created (UTC)")
    updated_at: datetime = Field(description="Timestamp of last update (UTC)")

    @classmethod
    def from_domain(cls, account: Account) -> "AccountResponse":
        """Convert domain entity to response model.

        Args:
            account: The domain Account entity to convert.

        Returns:
            AccountResponse with all fields populated from the domain entity.
        """
        return cls(
            id=account.id,
            name=account.name,
            slug=account.slug,
            status=account.status,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )


# User models
class UserCreateRequest(BaseModel):
    """Request model for creating a user."""

    account_id: UUID = Field(description="ID of the account this user belongs to")
    email: EmailStr = Field(description="User's email address (must be valid email format)")
    display_name: str = Field(description="User's display name (2-100 characters)")


class UserUpdateRequest(BaseModel):
    """Request model for updating a user."""

    email: EmailStr | None = Field(default=None, description="Updated email address")
    display_name: str | None = Field(default=None, description="Updated display name")
    deleted: bool | None = Field(default=None, description="Set to true to soft delete the user")


class UserResponse(BaseModel):
    """Response model for a user."""

    id: UUID = Field(description="Unique identifier for the user")
    account_id: UUID = Field(description="ID of the account this user belongs to")
    email: str = Field(description="User's email address")
    display_name: str = Field(description="User's display name")
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
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
