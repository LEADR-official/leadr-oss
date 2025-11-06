"""Account domain model - STUB for RED commit."""

from enum import Enum

from leadr.common.domain.models import Entity


class AccountStatus(Enum):
    """Account status enumeration."""

    ACTIVE = "active"
    SUSPENDED = "suspended"


class Account(Entity):
    """Account domain entity - STUB implementation that will fail tests."""

    name: str
    slug: str
    status: AccountStatus = AccountStatus.ACTIVE

    def suspend(self) -> None:
        """Suspend the account - STUB."""

    def activate(self) -> None:
        """Activate the account - STUB."""
