"""Account and User repository services - STUB for RED commit."""

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account
from leadr.accounts.domain.user import User
from leadr.common.domain.models import EntityID


class AccountRepository:
    """Account repository - STUB."""

    def __init__(self, session: AsyncSession):
        """Initialize repository."""
        self.session = session

    async def create(self, account: Account) -> Account:
        """Create account - STUB."""
        raise NotImplementedError

    async def get_by_id(self, account_id: EntityID) -> Account | None:
        """Get account by ID - STUB."""
        raise NotImplementedError

    async def get_by_slug(self, slug: str) -> Account | None:
        """Get account by slug - STUB."""
        raise NotImplementedError

    async def update(self, account: Account) -> Account:
        """Update account - STUB."""
        raise NotImplementedError

    async def delete(self, account_id: EntityID) -> None:
        """Delete account - STUB."""
        raise NotImplementedError

    async def list_all(self) -> list[Account]:
        """List all accounts - STUB."""
        raise NotImplementedError


class UserRepository:
    """User repository - STUB."""

    def __init__(self, session: AsyncSession):
        """Initialize repository."""
        self.session = session

    async def create(self, user: User) -> User:
        """Create user - STUB."""
        raise NotImplementedError

    async def get_by_id(self, user_id: EntityID) -> User | None:
        """Get user by ID - STUB."""
        raise NotImplementedError

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email - STUB."""
        raise NotImplementedError

    async def list_by_account(self, account_id: EntityID) -> list[User]:
        """List users by account - STUB."""
        raise NotImplementedError

    async def update(self, user: User) -> User:
        """Update user - STUB."""
        raise NotImplementedError

    async def delete(self, user_id: EntityID) -> None:
        """Delete user - STUB."""
        raise NotImplementedError
