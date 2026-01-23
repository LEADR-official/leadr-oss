"""Tests for AuthContext classes and helper functions."""

from datetime import UTC, datetime

import pytest

from leadr.accounts.domain.user import User
from leadr.auth.dependencies import (
    AdminAuthContext,
    AuthContext,
    ClientAuthContext,
)
from leadr.auth.domain.api_key import APIKey, APIKeyStatus
from leadr.auth.domain.identity import Identity, IdentityKind
from leadr.common.domain.ids import AccountID, APIKeyID, GameID, IdentityID, UserID


def _create_mock_identity(account_id: AccountID, game_id: GameID) -> Identity:
    """Create a mock identity for testing."""
    now = datetime.now(UTC)
    return Identity(
        id=IdentityID(),
        account_id=account_id,
        game_id=game_id,
        kind=IdentityKind.DEVICE,
        external_key="test-fingerprint",
        display_name=None,
        created_at=now,
        updated_at=now,
    )


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
            identity=None,
        )

        assert context.auth_type == "admin"

    async def test_auth_type_returns_client_when_identity_present(self):
        """Test that auth_type returns 'client' when identity is present."""
        account_id = AccountID()
        game_id = GameID()
        identity = _create_mock_identity(account_id, game_id)

        context = AuthContext(
            account_id=account_id,
            user=None,
            api_key=None,
            identity=identity,
        )

        assert context.auth_type == "client"

    async def test_auth_type_raises_when_neither_set(self):
        """Test that auth_type raises ValueError when neither api_key nor identity is set."""
        account_id = AccountID()

        context = AuthContext(
            account_id=account_id,
            user=None,
            api_key=None,
            identity=None,
        )

        with pytest.raises(ValueError, match="Neither api_key nor identity set"):
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
            identity=None,
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
            identity=None,
        )

        assert context.is_superadmin is False

    async def test_is_superadmin_returns_false_when_user_is_none(self):
        """Test that is_superadmin returns False when user is None (client auth)."""
        account_id = AccountID()

        context = AuthContext(
            account_id=account_id,
            user=None,
            api_key=None,
            identity=None,
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
            identity=None,
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
            identity=None,
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
            identity=None,
        )

        assert context.has_access_to_account(other_account_id) is False

    async def test_has_access_to_account_for_client_auth(self):
        """Test that client auth only has access to its own account."""
        account_id = AccountID()
        other_account_id = AccountID()
        game_id = GameID()
        identity = _create_mock_identity(account_id, game_id)

        context = AuthContext(
            account_id=account_id,
            user=None,
            api_key=None,
            identity=identity,
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
            identity=None,
        )

        # All properties should be accessible
        assert context.account_id == account_id
        assert context.user == user
        assert context.api_key == api_key
        assert context.identity is None


@pytest.mark.asyncio
class TestClientAuthContext:
    """Test suite for ClientAuthContext class."""

    async def test_properties_return_correct_types(self):
        """Test that ClientAuthContext properties return correct types."""
        account_id = AccountID()
        game_id = GameID()
        identity = _create_mock_identity(account_id, game_id)

        context = ClientAuthContext(
            account_id=account_id,
            identity=identity,
        )

        # All properties should be accessible
        assert context.account_id == account_id
        assert context.user is None
        assert context.api_key is None
        assert context.identity == identity
        assert context.game_id == game_id
