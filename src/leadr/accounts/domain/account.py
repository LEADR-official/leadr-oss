"""Account domain model."""

import re
from enum import Enum

from pydantic import Field, field_validator

from leadr.common.domain.ids import AccountID
from leadr.common.domain.models import Entity


class AccountStatus(Enum):
    """Account status enumeration."""

    ACTIVE = "active"
    SUSPENDED = "suspended"


class Account(Entity):
    """Account domain entity.

    Represents an organization or team that owns games and manages users.
    Accounts have a unique name and URL-friendly slug, and can be
    active or suspended.
    """

    id: AccountID = Field(
        frozen=True,
        default_factory=AccountID,
        description="Unique account identifier",
    )
    name: str
    slug: str
    status: AccountStatus = AccountStatus.ACTIVE

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate account name length and format."""
        if not value or not value.strip():
            raise ValueError("Account name cannot be empty")
        if len(value) < 2:
            raise ValueError("Account name must be at least 2 characters")
        if len(value) > 100:
            raise ValueError("Account name must not exceed 100 characters")
        return value.strip()

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        """Validate slug format (lowercase alphanumeric with hyphens)."""
        if not value:
            raise ValueError("Account slug cannot be empty")
        if len(value) < 2:
            raise ValueError("Account slug must be at least 2 characters")
        if len(value) > 50:
            raise ValueError("Account slug must not exceed 50 characters")
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", value):
            raise ValueError(
                "Account slug must be lowercase alphanumeric with hyphens, "
                "and cannot start or end with a hyphen"
            )
        return value

    def suspend(self) -> None:
        """Suspend the account, preventing access."""
        self.status = AccountStatus.SUSPENDED

    def activate(self) -> None:
        """Activate the account, allowing access."""
        self.status = AccountStatus.ACTIVE
