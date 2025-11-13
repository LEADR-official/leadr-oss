"""Superadmin bootstrap functionality.

This module provides functionality to automatically create a superadmin user
and associated account on application startup if none exists.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account
from leadr.accounts.services.repositories import AccountRepository
from leadr.accounts.services.user_service import UserService
from leadr.auth.services.api_key_service import APIKeyService
from leadr.config import settings

logger = logging.getLogger(__name__)


async def ensure_superadmin_exists(session: AsyncSession) -> None:
    """Ensure a superadmin user exists, creating one if necessary.

    This function is idempotent and safe to call multiple times. It will:
    1. Check if any superadmin user already exists
    2. If not, create:
       - A system account (configured via SUPERADMIN_ACCOUNT_NAME/SLUG)
       - A superadmin user (configured via SUPERADMIN_EMAIL/DISPLAY_NAME)
       - An API key for the superadmin (using SUPERADMIN_API_KEY)

    The function commits the transaction if it creates entities.

    Args:
        session: Database session to use for queries and inserts.

    Example:
        >>> async with get_session() as session:
        ...     await ensure_superadmin_exists(session)
    """
    # Check if any superadmin already exists
    user_service = UserService(session)
    if await user_service.superadmin_exists():
        logger.info("Superadmin already exists, skipping bootstrap")
        return

    logger.info("No superadmin found, creating superadmin user and account")

    # Create system account
    account_repo = AccountRepository(session)

    # Check if account with this slug already exists
    existing_account = await account_repo.get_by_slug(settings.SUPERADMIN_ACCOUNT_SLUG)
    if existing_account:
        account = existing_account
        logger.info(
            "Using existing account: %s (id=%s)",
            account.name,
            account.id,
        )
    else:
        account = Account(
            name=settings.SUPERADMIN_ACCOUNT_NAME,
            slug=settings.SUPERADMIN_ACCOUNT_SLUG,
        )
        account = await account_repo.create(account)
        logger.info(
            "Created superadmin account: %s (id=%s)",
            account.name,
            account.id,
        )

    # Create superadmin user
    user = await user_service.create_user(
        account_id=account.id,
        email=settings.SUPERADMIN_EMAIL,
        display_name=settings.SUPERADMIN_DISPLAY_NAME,
        super_admin=True,
    )
    logger.info(
        "Created superadmin user: %s (id=%s)",
        user.email,
        user.id,
    )

    # Create API key for superadmin
    api_key_service = APIKeyService(session)
    api_key = await api_key_service.create_api_key_with_value(
        account_id=account.id,
        user_id=user.id,
        name=settings.SUPERADMIN_API_KEY_NAME,
        key_value=settings.SUPERADMIN_API_KEY,
    )
    logger.info(
        "Created superadmin API key: %s (prefix=%s)",
        api_key.name,
        api_key.key_prefix,
    )

    # Commit the transaction
    await session.commit()

    logger.info("Superadmin bootstrap completed successfully")
