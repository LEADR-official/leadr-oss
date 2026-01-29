"""Tests for admin auth dependency (require_admin_auth)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.accounts.services.user_service import UserService
from leadr.auth.dependencies import require_admin_auth
from leadr.auth.domain.api_key import APIKeyStatus
from leadr.auth.services.api_key_service import APIKeyService
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.identity_service import IdentityService
from leadr.auth.services.nonce_service import NonceService
from leadr.common.domain.ids import AccountID


@pytest.mark.asyncio
class TestRequireAdminAuth:
    """Test suite for require_admin_auth dependency."""

    async def test_missing_api_key_header_raises_401(self, db_session: AsyncSession):
        """Test that missing API key header raises 401 Unauthorized."""
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await require_admin_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                identity_service=identity_service,
                nonce_service=nonce_service,
                api_key=None,
                authorization=None,
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 401
        assert "require" in exc_info.value.detail.lower()

    async def test_invalid_api_key_raises_401(self, db_session: AsyncSession):
        """Test that an invalid/unknown API key raises 401 Unauthorized."""
        # Create account and valid key first (to ensure DB works)
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
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

        # Create user for API key
        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account_id,
            email=f"test-{str(account_id)[:8]}@example.com",
            display_name="Test User",
        )

        api_key_service = APIKeyService(db_session)
        await api_key_service.create_api_key(
            account_id=account_id,
            user_id=user.id,
            name="Valid Key",
            expires_at=None,
        )

        # Try with a completely invalid key
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await require_admin_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                identity_service=identity_service,
                nonce_service=nonce_service,
                api_key="ldr_invalidkey123456",
                authorization=None,
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()

    async def test_valid_api_key_returns_api_key_entity(self, db_session: AsyncSession):
        """Test that a valid API key returns the APIKey entity."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
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

        # Create user for API key
        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account_id,
            email=f"test-{str(account_id)[:8]}@example.com",
            display_name="Test User",
        )

        # Create API key
        api_key_service = APIKeyService(db_session)
        api_key, plain_key = await api_key_service.create_api_key(
            account_id=account_id,
            user_id=user.id,
            name="Test Key",
            expires_at=None,
        )

        # Use the dependency
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        result = await require_admin_auth(
            request=mock_request,
            api_key_service=api_key_service,
            user_service=user_service,
            identity_service=identity_service,
            nonce_service=nonce_service,
            api_key=plain_key,
            authorization=None,
            leadr_client_nonce=None,
        )

        # Should return AuthContext with APIKey and User
        assert result.api_key is not None
        assert result.api_key.id == api_key.id
        assert result.account_id == account_id
        assert result.api_key.name == "Test Key"
        assert result.api_key.status == APIKeyStatus.ACTIVE
        assert result.user is not None
        assert result.user.id == user.id

    async def test_expired_api_key_raises_401(self, db_session: AsyncSession):
        """Test that an expired API key raises 401 Unauthorized."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
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

        # Create user for API key
        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account_id,
            email=f"test-{str(account_id)[:8]}@example.com",
            display_name="Test User",
        )

        # Create expired API key
        api_key_service = APIKeyService(db_session)
        expired_time = now - timedelta(days=1)
        api_key, plain_key = await api_key_service.create_api_key(
            account_id=account_id,
            user_id=user.id,
            name="Expired Key",
            expires_at=expired_time,
        )

        # Try to use expired key
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await require_admin_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                identity_service=identity_service,
                nonce_service=nonce_service,
                api_key=plain_key,
                authorization=None,
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 401
        assert (
            "invalid" in exc_info.value.detail.lower() or "expired" in exc_info.value.detail.lower()
        )

    async def test_revoked_api_key_raises_401(self, db_session: AsyncSession):
        """Test that a revoked API key raises 401 Unauthorized."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
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

        # Create user for API key
        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account_id,
            email=f"test-{str(account_id)[:8]}@example.com",
            display_name="Test User",
        )

        # Create and revoke API key
        api_key_service = APIKeyService(db_session)
        api_key, plain_key = await api_key_service.create_api_key(
            account_id=account_id,
            user_id=user.id,
            name="To Be Revoked",
            expires_at=None,
        )

        # Revoke it
        await api_key_service.revoke_api_key(api_key.id)

        # Try to use revoked key
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await require_admin_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                identity_service=identity_service,
                nonce_service=nonce_service,
                api_key=plain_key,
                authorization=None,
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 401
        assert (
            "invalid" in exc_info.value.detail.lower() or "revoked" in exc_info.value.detail.lower()
        )

    async def test_soft_deleted_api_key_raises_401(self, db_session: AsyncSession):
        """Test that a soft-deleted API key raises 401 Unauthorized."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
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

        # Create user for API key
        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account_id,
            email=f"test-{str(account_id)[:8]}@example.com",
            display_name="Test User",
        )

        # Create and soft-delete API key
        api_key_service = APIKeyService(db_session)
        api_key, plain_key = await api_key_service.create_api_key(
            account_id=account_id,
            user_id=user.id,
            name="To Be Deleted",
            expires_at=None,
        )

        # Soft delete it
        await api_key_service.soft_delete(api_key.id)

        # Try to use deleted key
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await require_admin_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                identity_service=identity_service,
                nonce_service=nonce_service,
                api_key=plain_key,
                authorization=None,
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()

    async def test_valid_key_updates_last_used_at(self, db_session: AsyncSession):
        """Test that using a valid API key updates the last_used_at timestamp."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
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

        # Create user for API key
        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account_id,
            email=f"test-{str(account_id)[:8]}@example.com",
            display_name="Test User",
        )

        # Create API key
        api_key_service = APIKeyService(db_session)
        api_key, plain_key = await api_key_service.create_api_key(
            account_id=account_id,
            user_id=user.id,
            name="Test Key",
            expires_at=None,
        )

        # Verify last_used_at is None initially
        assert api_key.last_used_at is None

        # Use the dependency
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        await require_admin_auth(
            request=mock_request,
            api_key_service=api_key_service,
            user_service=user_service,
            identity_service=identity_service,
            nonce_service=nonce_service,
            api_key=plain_key,
            authorization=None,
            leadr_client_nonce=None,
        )

        # Refresh the key from DB to get updated timestamp
        updated_key = await api_key_service.get_by_id_or_raise(api_key.id)

        # Verify last_used_at was updated
        assert updated_key.last_used_at is not None
        assert updated_key.last_used_at > now
