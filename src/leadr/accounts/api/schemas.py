"""API request and response models for accounts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.domain.user import User


# Account models
class AccountCreateRequest(BaseModel):
    """Request model for creating an account."""

    name: str
    slug: str


class AccountUpdateRequest(BaseModel):
    """Request model for updating an account."""

    name: str | None = None
    slug: str | None = None
    status: AccountStatus | None = None
    deleted: bool | None = None


class AccountResponse(BaseModel):
    """Response model for an account."""

    id: UUID
    name: str
    slug: str
    status: AccountStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, account: Account) -> "AccountResponse":
        """Convert domain entity to response model."""
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

    account_id: UUID
    email: EmailStr
    display_name: str


class UserUpdateRequest(BaseModel):
    """Request model for updating a user."""

    email: EmailStr | None = None
    display_name: str | None = None
    deleted: bool | None = None


class UserResponse(BaseModel):
    """Response model for a user."""

    id: UUID
    account_id: UUID
    email: str
    display_name: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        """Convert domain entity to response model."""
        return cls(
            id=user.id,
            account_id=user.account_id,
            email=user.email,
            display_name=user.display_name,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
