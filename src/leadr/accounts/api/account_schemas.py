"""API request and response models for accounts."""

from datetime import datetime

from pydantic import BaseModel, Field

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.common.domain.ids import AccountID


class AccountCreateRequest(BaseModel):
    """Request model for creating an account."""

    name: str = Field(description="Account name (2-100 characters)")
    slug: str | None = Field(
        default=None,
        description=(
            "Optional URL-friendly slug (globally unique). "
            "If not provided, will be auto-generated from name"
        ),
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

    id: AccountID = Field(description="Unique identifier for the account")
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
