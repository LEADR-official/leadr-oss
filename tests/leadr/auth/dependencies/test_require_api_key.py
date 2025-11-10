"""Tests for require_api_key dependency."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.auth.dependencies import require_api_key
from leadr.auth.domain.api_key import APIKeyStatus
from leadr.auth.services.api_key_service import APIKeyService


@pytest.mark.asyncio
class TestRequireAPIKey:
    """Test suite for require_api_key dependency."""

    async def test_missing_api_key_header_raises_401(self, db_session: AsyncSession):
        """Test that missing API key header raises 401 Unauthorized."""
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(api_key=None, db=db_session)

        assert exc_info.value.status_code == 401
        assert "required" in exc_info.value.detail.lower()

    async def test_invalid_api_key_raises_401(self, db_session: AsyncSession):
        """Test that an invalid/unknown API key raises 401 Unauthorized."""
        # Create account and valid key first (to ensure DB works)
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        service = APIKeyService(db_session)
        await service.create_api_key(
            account_id=account_id,
            name="Valid Key",
            expires_at=None,
        )

        # Try with a completely invalid key
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(api_key="ldr_invalidkey123456", db=db_session)

        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()

    async def test_valid_api_key_returns_api_key_entity(self, db_session: AsyncSession):
        """Test that a valid API key returns the APIKey entity."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create API key
        service = APIKeyService(db_session)
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            name="Test Key",
            expires_at=None,
        )

        # Use the dependency
        result = await require_api_key(api_key=plain_key, db=db_session)

        # Should return the APIKey entity
        assert result.id == api_key.id
        assert result.account_id == account_id
        assert result.name == "Test Key"
        assert result.status == APIKeyStatus.ACTIVE

    async def test_expired_api_key_raises_401(self, db_session: AsyncSession):
        """Test that an expired API key raises 401 Unauthorized."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create expired API key
        service = APIKeyService(db_session)
        expired_time = now - timedelta(days=1)
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            name="Expired Key",
            expires_at=expired_time,
        )

        # Try to use expired key
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(api_key=plain_key, db=db_session)

        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower() or "expired" in exc_info.value.detail.lower()

    async def test_revoked_api_key_raises_401(self, db_session: AsyncSession):
        """Test that a revoked API key raises 401 Unauthorized."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create and revoke API key
        service = APIKeyService(db_session)
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            name="To Be Revoked",
            expires_at=None,
        )

        # Revoke it
        await service.revoke_api_key(api_key.id, account_id=account_id)

        # Try to use revoked key
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(api_key=plain_key, db=db_session)

        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower() or "revoked" in exc_info.value.detail.lower()

    async def test_soft_deleted_api_key_raises_401(self, db_session: AsyncSession):
        """Test that a soft-deleted API key raises 401 Unauthorized."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create and soft-delete API key
        service = APIKeyService(db_session)
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            name="To Be Deleted",
            expires_at=None,
        )

        # Soft delete it
        from leadr.common.domain.models import EntityID

        await service.soft_delete(EntityID(value=api_key.id))

        # Try to use deleted key
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(api_key=plain_key, db=db_session)

        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()

    async def test_valid_key_updates_last_used_at(self, db_session: AsyncSession):
        """Test that using a valid API key updates the last_used_at timestamp."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create API key
        service = APIKeyService(db_session)
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            name="Test Key",
            expires_at=None,
        )

        # Verify last_used_at is None initially
        assert api_key.last_used_at is None

        # Use the dependency
        await require_api_key(api_key=plain_key, db=db_session)

        # Refresh the key from DB to get updated timestamp
        from leadr.common.domain.models import EntityID

        updated_key = await service.get_by_id_or_raise(EntityID(value=api_key.id))

        # Verify last_used_at was updated
        assert updated_key.last_used_at is not None
        assert updated_key.last_used_at > now
