"""Tests for AuthContext classes and helper functions."""

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from leadr.accounts.domain.user import User
from leadr.auth.dependencies import (
    AdminAuthContext,
    AuthContext,
    ClientAuthContext,
    resolve_query_account_id,
    validate_body_account_id,
)
from leadr.auth.domain.api_key import APIKey, APIKeyStatus
from leadr.auth.domain.device import Device, DeviceStatus
from leadr.common.domain.ids import AccountID, APIKeyID, DeviceID, GameID, UserID


@pytest.mark.asyncio
class TestAuthContext:
    """Test suite for base AuthContext class."""

    async def test_auth_type_returns_admin_when_api_key_present(self):
        """Test that auth_type returns 'admin' when API key is present."""
        now = datetime.now(UTC)
        account_id = AccountID()
        user_id = UserID()
        api_key_id = APIKeyID()

        user = User(
            id=user_id,
            account_id=account_id,
            email="test@example.com",
            display_name="Test User",
            super_admin=False,
            created_at=now,
            updated_at=now,
        )

        api_key = APIKey(
            id=api_key_id,
            account_id=account_id,
            user_id=user_id,
            name="Test Key",
            key_hash="test_hash",
            key_prefix="ldr_test",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        context = AuthContext(
            account_id=account_id,
            user=user,
            api_key=api_key,
            device=None,
        )

        assert context.auth_type == "admin"

    async def test_auth_type_returns_client_when_device_present(self):
        """Test that auth_type returns 'client' when device is present."""
        now = datetime.now(UTC)
        account_id = AccountID()
        device_id = DeviceID()

        device = Device(
            id=device_id,
            account_id=account_id,
            game_id=GameID(),
            client_fingerprint="test_device_123",
            platform="test",
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        context = AuthContext(
            account_id=account_id,
            user=None,
            api_key=None,
            device=device,
        )

        assert context.auth_type == "client"

    async def test_auth_type_raises_when_neither_set(self):
        """Test that auth_type raises ValueError when neither api_key nor device is set."""
        account_id = AccountID()

        context = AuthContext(
            account_id=account_id,
            user=None,
            api_key=None,
            device=None,
        )

        with pytest.raises(ValueError, match="Neither api_key nor device set"):
            _ = context.auth_type

    async def test_is_superadmin_returns_true_for_superadmin_user(self):
        """Test that is_superadmin returns True when user has super_admin flag."""
        now = datetime.now(UTC)
        account_id = AccountID()
        user_id = UserID()

        user = User(
            id=user_id,
            account_id=account_id,
            email="admin@example.com",
            display_name="Super Admin",
            super_admin=True,
            created_at=now,
            updated_at=now,
        )

        context = AuthContext(
            account_id=account_id,
            user=user,
            api_key=None,
            device=None,
        )

        assert context.is_superadmin is True

    async def test_is_superadmin_returns_false_for_regular_user(self):
        """Test that is_superadmin returns False for regular users."""
        now = datetime.now(UTC)
        account_id = AccountID()
        user_id = UserID()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="Regular User",
            super_admin=False,
            created_at=now,
            updated_at=now,
        )

        context = AuthContext(
            account_id=account_id,
            user=user,
            api_key=None,
            device=None,
        )

        assert context.is_superadmin is False

    async def test_is_superadmin_returns_false_when_user_is_none(self):
        """Test that is_superadmin returns False when user is None (client auth)."""
        account_id = AccountID()

        context = AuthContext(
            account_id=account_id,
            user=None,
            api_key=None,
            device=None,
        )

        assert context.is_superadmin is False

    async def test_has_access_to_account_returns_true_for_superadmin(self):
        """Test that superadmin has access to any account."""
        now = datetime.now(UTC)
        account_id = AccountID()
        other_account_id = AccountID()
        user_id = UserID()
        api_key_id = APIKeyID()

        user = User(
            id=user_id,
            account_id=account_id,
            email="admin@example.com",
            display_name="Super Admin",
            super_admin=True,
            created_at=now,
            updated_at=now,
        )

        api_key = APIKey(
            id=api_key_id,
            account_id=account_id,
            user_id=user_id,
            name="Admin Key",
            key_hash="test_hash",
            key_prefix="ldr_test",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        context = AuthContext(
            account_id=account_id,
            user=user,
            api_key=api_key,
            device=None,
        )

        # Superadmin should have access to any account
        assert context.has_access_to_account(other_account_id) is True
        assert context.has_access_to_account(account_id) is True

    async def test_has_access_to_account_returns_true_for_own_account(self):
        """Test that regular user has access to their own account."""
        now = datetime.now(UTC)
        account_id = AccountID()
        user_id = UserID()
        api_key_id = APIKeyID()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="Regular User",
            super_admin=False,
            created_at=now,
            updated_at=now,
        )

        api_key = APIKey(
            id=api_key_id,
            account_id=account_id,
            user_id=user_id,
            name="User Key",
            key_hash="test_hash",
            key_prefix="ldr_test",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        context = AuthContext(
            account_id=account_id,
            user=user,
            api_key=api_key,
            device=None,
        )

        assert context.has_access_to_account(account_id) is True

    async def test_has_access_to_account_returns_false_for_other_account(self):
        """Test that regular user does not have access to other accounts."""
        now = datetime.now(UTC)
        account_id = AccountID()
        other_account_id = AccountID()
        user_id = UserID()
        api_key_id = APIKeyID()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="Regular User",
            super_admin=False,
            created_at=now,
            updated_at=now,
        )

        api_key = APIKey(
            id=api_key_id,
            account_id=account_id,
            user_id=user_id,
            name="User Key",
            key_hash="test_hash",
            key_prefix="ldr_test",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        context = AuthContext(
            account_id=account_id,
            user=user,
            api_key=api_key,
            device=None,
        )

        assert context.has_access_to_account(other_account_id) is False

    async def test_has_access_to_account_for_client_auth(self):
        """Test that client auth only has access to its own account."""
        now = datetime.now(UTC)
        account_id = AccountID()
        other_account_id = AccountID()
        device_id = DeviceID()

        device = Device(
            id=device_id,
            account_id=account_id,
            game_id=GameID(),
            client_fingerprint="test_device_123",
            platform="test",
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        context = AuthContext(
            account_id=account_id,
            user=None,
            api_key=None,
            device=device,
        )

        # Client auth should have access to own account
        assert context.has_access_to_account(account_id) is True
        # But not to other accounts
        assert context.has_access_to_account(other_account_id) is False


@pytest.mark.asyncio
class TestAdminAuthContext:
    """Test suite for AdminAuthContext class."""

    async def test_properties_return_correct_types(self):
        """Test that AdminAuthContext properties return non-None values."""
        now = datetime.now(UTC)
        account_id = AccountID()
        user_id = UserID()
        api_key_id = APIKeyID()

        user = User(
            id=user_id,
            account_id=account_id,
            email="test@example.com",
            display_name="Test User",
            super_admin=False,
            created_at=now,
            updated_at=now,
        )

        api_key = APIKey(
            id=api_key_id,
            account_id=account_id,
            user_id=user_id,
            name="Test Key",
            key_hash="test_hash",
            key_prefix="ldr_test",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        context = AdminAuthContext(
            account_id=account_id,
            user=user,
            api_key=api_key,
            device=None,
        )

        # All properties should be accessible
        assert context.account_id == account_id
        assert context.user == user
        assert context.api_key == api_key
        assert context.device is None


@pytest.mark.asyncio
class TestClientAuthContext:
    """Test suite for ClientAuthContext class."""

    async def test_properties_return_correct_types(self):
        """Test that ClientAuthContext properties return correct types."""
        now = datetime.now(UTC)
        account_id = AccountID()
        device_id = DeviceID()

        device = Device(
            id=device_id,
            account_id=account_id,
            game_id=GameID(),
            client_fingerprint="test_device_123",
            platform="test",
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        context = ClientAuthContext(
            account_id=account_id,
            user=None,
            api_key=None,
            device=device,
        )

        # All properties should be accessible
        assert context.account_id == account_id
        assert context.user is None
        assert context.api_key is None
        assert context.device == device


@pytest.mark.asyncio
class TestResolveQueryAccountID:
    """Test suite for resolve_query_account_id helper function."""

    async def test_superadmin_without_account_id_raises_400(self):
        """Test that superadmin without account_id query param raises 400."""
        now = datetime.now(UTC)
        account_id = AccountID()
        user_id = UserID()
        api_key_id = APIKeyID()

        user = User(
            id=user_id,
            account_id=account_id,
            email="admin@example.com",
            display_name="Super Admin",
            super_admin=True,
            created_at=now,
            updated_at=now,
        )

        api_key = APIKey(
            id=api_key_id,
            account_id=account_id,
            user_id=user_id,
            name="Admin Key",
            key_hash="test_hash",
            key_prefix="ldr_test",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        auth = AdminAuthContext(
            account_id=account_id,
            user=user,
            api_key=api_key,
            device=None,
        )

        with pytest.raises(HTTPException) as exc_info:
            resolve_query_account_id(auth, None)

        assert exc_info.value.status_code == 400
        assert "must explicitly specify account_id" in exc_info.value.detail

    async def test_superadmin_with_account_id_returns_it(self):
        """Test that superadmin with account_id query param returns it."""
        now = datetime.now(UTC)
        account_id = AccountID()
        target_account_id = AccountID()
        user_id = UserID()
        api_key_id = APIKeyID()

        user = User(
            id=user_id,
            account_id=account_id,
            email="admin@example.com",
            display_name="Super Admin",
            super_admin=True,
            created_at=now,
            updated_at=now,
        )

        api_key = APIKey(
            id=api_key_id,
            account_id=account_id,
            user_id=user_id,
            name="Admin Key",
            key_hash="test_hash",
            key_prefix="ldr_test",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        auth = AdminAuthContext(
            account_id=account_id,
            user=user,
            api_key=api_key,
            device=None,
        )

        result = resolve_query_account_id(auth, target_account_id)
        assert result == target_account_id

    async def test_regular_user_without_account_id_returns_own_account(self):
        """Test that regular user without account_id returns their own account."""
        now = datetime.now(UTC)
        account_id = AccountID()
        user_id = UserID()
        api_key_id = APIKeyID()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="Regular User",
            super_admin=False,
            created_at=now,
            updated_at=now,
        )

        api_key = APIKey(
            id=api_key_id,
            account_id=account_id,
            user_id=user_id,
            name="User Key",
            key_hash="test_hash",
            key_prefix="ldr_test",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        auth = AdminAuthContext(
            account_id=account_id,
            user=user,
            api_key=api_key,
            device=None,
        )

        result = resolve_query_account_id(auth, None)
        assert result == account_id

    async def test_regular_user_with_matching_account_id_returns_it(self):
        """Test that regular user with matching account_id returns it."""
        now = datetime.now(UTC)
        account_id = AccountID()
        user_id = UserID()
        api_key_id = APIKeyID()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="Regular User",
            super_admin=False,
            created_at=now,
            updated_at=now,
        )

        api_key = APIKey(
            id=api_key_id,
            account_id=account_id,
            user_id=user_id,
            name="User Key",
            key_hash="test_hash",
            key_prefix="ldr_test",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        auth = AdminAuthContext(
            account_id=account_id,
            user=user,
            api_key=api_key,
            device=None,
        )

        result = resolve_query_account_id(auth, account_id)
        assert result == account_id

    async def test_regular_user_with_different_account_id_raises_403(self):
        """Test that regular user with different account_id raises 403."""
        now = datetime.now(UTC)
        account_id = AccountID()
        other_account_id = AccountID()
        user_id = UserID()
        api_key_id = APIKeyID()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="Regular User",
            super_admin=False,
            created_at=now,
            updated_at=now,
        )

        api_key = APIKey(
            id=api_key_id,
            account_id=account_id,
            user_id=user_id,
            name="User Key",
            key_hash="test_hash",
            key_prefix="ldr_test",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        auth = AdminAuthContext(
            account_id=account_id,
            user=user,
            api_key=api_key,
            device=None,
        )

        with pytest.raises(HTTPException) as exc_info:
            resolve_query_account_id(auth, other_account_id)

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail


@pytest.mark.asyncio
class TestValidateBodyAccountID:
    """Test suite for validate_body_account_id helper function."""

    async def test_superadmin_can_access_any_account(self):
        """Test that superadmin can access any account in request body."""
        now = datetime.now(UTC)
        account_id = AccountID()
        target_account_id = AccountID()
        user_id = UserID()
        api_key_id = APIKeyID()

        user = User(
            id=user_id,
            account_id=account_id,
            email="admin@example.com",
            display_name="Super Admin",
            super_admin=True,
            created_at=now,
            updated_at=now,
        )

        api_key = APIKey(
            id=api_key_id,
            account_id=account_id,
            user_id=user_id,
            name="Admin Key",
            key_hash="test_hash",
            key_prefix="ldr_test",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        auth = AdminAuthContext(
            account_id=account_id,
            user=user,
            api_key=api_key,
            device=None,
        )

        # Should not raise
        validate_body_account_id(auth, target_account_id)

    async def test_regular_user_can_access_own_account(self):
        """Test that regular user can access their own account in request body."""
        now = datetime.now(UTC)
        account_id = AccountID()
        user_id = UserID()
        api_key_id = APIKeyID()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="Regular User",
            super_admin=False,
            created_at=now,
            updated_at=now,
        )

        api_key = APIKey(
            id=api_key_id,
            account_id=account_id,
            user_id=user_id,
            name="User Key",
            key_hash="test_hash",
            key_prefix="ldr_test",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        auth = AdminAuthContext(
            account_id=account_id,
            user=user,
            api_key=api_key,
            device=None,
        )

        # Should not raise
        validate_body_account_id(auth, account_id)

    async def test_regular_user_cannot_access_other_account(self):
        """Test that regular user cannot access another account in request body."""
        now = datetime.now(UTC)
        account_id = AccountID()
        other_account_id = AccountID()
        user_id = UserID()
        api_key_id = APIKeyID()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="Regular User",
            super_admin=False,
            created_at=now,
            updated_at=now,
        )

        api_key = APIKey(
            id=api_key_id,
            account_id=account_id,
            user_id=user_id,
            name="User Key",
            key_hash="test_hash",
            key_prefix="ldr_test",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        auth = AdminAuthContext(
            account_id=account_id,
            user=user,
            api_key=api_key,
            device=None,
        )

        with pytest.raises(HTTPException) as exc_info:
            validate_body_account_id(auth, other_account_id)

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail
