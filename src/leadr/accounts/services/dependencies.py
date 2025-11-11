"""Account and User service dependency injection factories."""

from typing import Annotated

from fastapi import Depends

from leadr.accounts.services.account_service import AccountService
from leadr.accounts.services.user_service import UserService
from leadr.common.dependencies import DatabaseSession


async def get_account_service(db: DatabaseSession) -> AccountService:
    """Get AccountService dependency.

    Args:
        db: Database session injected via dependency injection

    Returns:
        AccountService instance configured with the database session
    """
    return AccountService(db)


async def get_user_service(db: DatabaseSession) -> UserService:
    """Get UserService dependency.

    Args:
        db: Database session injected via dependency injection

    Returns:
        UserService instance configured with the database session
    """
    return UserService(db)


# Type aliases for dependency injection in routes
AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
