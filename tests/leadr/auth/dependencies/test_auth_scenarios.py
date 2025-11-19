"""Tests for additional authentication scenarios and edge cases."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.accounts.services.user_service import UserService
from leadr.auth.dependencies import require_admin_auth
from leadr.auth.services.api_key_service import APIKeyService
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.nonce_service import NonceService
from leadr.common.domain.ids import AccountID


@pytest.mark.asyncio
class TestAdminAPIDisabled:
    """Test suite for admin API disabled scenarios."""

    @patch("leadr.auth.dependencies.settings.ENABLE_ADMIN_API", False)
    async def test_admin_auth_when_admin_api_disabled_raises_500(self, db_session: AsyncSession):
        """Test that admin auth raises 500 when ENABLE_ADMIN_API is False."""
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        device_service = DeviceService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await require_admin_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                device_service=device_service,
                nonce_service=nonce_service,
                api_key="ldr_test123",
                authorization=None,
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 500
        assert "Admin API is not enabled" in exc_info.value.detail


@pytest.mark.asyncio
class TestUserNotFoundEdgeCase:
    """Test suite for user not found edge case."""

    async def test_api_key_with_missing_user_raises_401(self, db_session: AsyncSession):
        """Test that an API key whose user was deleted raises 401."""
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

        # Create user
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

        # Soft delete the user
        await user_service.soft_delete(user.id)

        # Try to use the API key with deleted user
        device_service = DeviceService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await require_admin_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                device_service=device_service,
                nonce_service=nonce_service,
                api_key=plain_key,
                authorization=None,
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 401
        assert "User" in exc_info.value.detail or "not found" in exc_info.value.detail.lower()
