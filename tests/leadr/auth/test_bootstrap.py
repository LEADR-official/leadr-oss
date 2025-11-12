"""Tests for superadmin bootstrap logic."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.services.repositories import AccountRepository, UserRepository
from leadr.accounts.services.user_service import UserService
from leadr.auth.bootstrap import ensure_superadmin_exists
from leadr.auth.services.repositories import APIKeyRepository
from leadr.config import settings


@pytest.mark.asyncio
class TestSuperadminBootstrap:
    """Test suite for superadmin bootstrap functionality."""

    async def test_ensure_superadmin_exists_creates_account_user_and_key(
        self, db_session: AsyncSession
    ):
        """Test that ensure_superadmin_exists creates account, user, and API key when none exist."""
        # Verify no superadmin exists
        user_service = UserService(db_session)
        assert await user_service.superadmin_exists() is False

        # Run bootstrap
        await ensure_superadmin_exists(db_session)

        # Verify superadmin was created
        assert await user_service.superadmin_exists() is True

        # Verify account was created
        account_repo = AccountRepository(db_session)
        account = await account_repo.get_by_slug(settings.SUPERADMIN_ACCOUNT_SLUG)
        assert account is not None
        assert account.name == settings.SUPERADMIN_ACCOUNT_NAME
        assert account.slug == settings.SUPERADMIN_ACCOUNT_SLUG

        # Verify user was created
        user_repo = UserRepository(db_session)
        user = await user_repo.get_by_email(settings.SUPERADMIN_EMAIL)
        assert user is not None
        assert user.email == settings.SUPERADMIN_EMAIL
        assert user.display_name == settings.SUPERADMIN_DISPLAY_NAME
        assert user.super_admin is True
        assert user.account_id == account.id

        # Verify API key was created
        api_key_repo = APIKeyRepository(db_session)
        keys = await api_key_repo.filter(account_id=account.id)
        assert len(keys) == 1
        assert keys[0].name == settings.SUPERADMIN_API_KEY_NAME

    async def test_ensure_superadmin_exists_is_idempotent(self, db_session: AsyncSession):
        """Test that ensure_superadmin_exists can be called multiple times safely."""
        # Run bootstrap twice
        await ensure_superadmin_exists(db_session)
        await ensure_superadmin_exists(db_session)

        # Verify only one superadmin exists
        user_service = UserService(db_session)
        superadmins = await user_service.find_superadmins()
        assert len(superadmins) == 1

        # Verify only one account with that slug
        account_repo = AccountRepository(db_session)
        accounts = await account_repo.filter(slug=settings.SUPERADMIN_ACCOUNT_SLUG)
        assert len(accounts) == 1

        # Verify only one API key for that account
        api_key_repo = APIKeyRepository(db_session)
        keys = await api_key_repo.filter(account_id=accounts[0].id)
        assert len(keys) == 1

    async def test_ensure_superadmin_exists_skips_if_superadmin_exists(
        self, db_session: AsyncSession
    ):
        """Test that ensure_superadmin_exists skips creation if any superadmin exists."""
        # Create a different superadmin manually
        from uuid import uuid4

        from leadr.accounts.domain.account import Account, AccountStatus
        from leadr.accounts.services.repositories import AccountRepository

        account_repo = AccountRepository(db_session)
        account_id = uuid4()

        account = Account(
            id=account_id,
            name="Existing Account",
            slug="existing-account",
            status=AccountStatus.ACTIVE,
        )
        await account_repo.create(account)

        user_service = UserService(db_session)
        await user_service.create_user(
            account_id=account_id,
            email="existing@example.com",
            display_name="Existing Admin",
            super_admin=True,
        )

        # Verify superadmin exists
        assert await user_service.superadmin_exists() is True

        # Run bootstrap
        await ensure_superadmin_exists(db_session)

        # Verify no new account was created with the configured slug
        accounts = await account_repo.filter(slug=settings.SUPERADMIN_ACCOUNT_SLUG)
        assert len(accounts) == 0

        # Verify still only one superadmin
        superadmins = await user_service.find_superadmins()
        assert len(superadmins) == 1
        assert superadmins[0].email == "existing@example.com"
