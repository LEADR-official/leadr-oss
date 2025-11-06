"""Account domain model."""

from enum import Enum

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

    name: str
    slug: str
    status: AccountStatus = AccountStatus.ACTIVE

    def suspend(self) -> None:
        """Suspend the account, preventing access."""
        self.status = AccountStatus.SUSPENDED

    def activate(self) -> None:
        """Activate the account, allowing access."""
        self.status = AccountStatus.ACTIVE
