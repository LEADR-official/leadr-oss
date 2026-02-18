"""Tests for client authentication and OR logic (admin+client) paths."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.services.user_service import UserService
from leadr.auth.dependencies import AuthContextDependency
from leadr.auth.domain.identity import Identity, IdentityKind
from leadr.auth.services.api_key_service import APIKeyService
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.identity_service import IdentityService
from leadr.auth.services.nonce_service import NonceService
from leadr.common.domain.ids import AccountID, GameID, IdentityID


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
class TestClientOnlyAuth:
    """Test suite for client-only authentication path."""

    @patch("leadr.auth.dependencies.settings.ENABLE_CLIENT_API", False)
    async def test_client_auth_when_client_api_disabled_raises_500(self, db_session: AsyncSession):
        """Test that client auth raises 500 when ENABLE_CLIENT_API is False."""
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        # Create dependency requiring client auth
        require_client_auth = AuthContextDependency(require_admin=False, require_client=True)
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await require_client_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                identity_service=identity_service,
                nonce_service=nonce_service,
                background_tasks=background_tasks,
                api_key=None,
                authorization="Bearer test_token",
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 500
        assert "Client API is not enabled" in exc_info.value.detail

    async def test_client_auth_missing_bearer_token_raises_401(self, db_session: AsyncSession):
        """Test that missing bearer token raises 401."""
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_auth = AuthContextDependency(require_admin=False, require_client=True)
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await require_client_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                identity_service=identity_service,
                nonce_service=nonce_service,
                background_tasks=background_tasks,
                api_key=None,
                authorization=None,
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 401
        assert "require" in exc_info.value.detail.lower()

    async def test_client_auth_invalid_bearer_format_raises_401(self, db_session: AsyncSession):
        """Test that invalid bearer token format raises 401."""
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_auth = AuthContextDependency(require_admin=False, require_client=True)
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await require_client_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                identity_service=identity_service,
                nonce_service=nonce_service,
                background_tasks=background_tasks,
                api_key=None,
                authorization="InvalidFormat",
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 401
        assert "Invalid authorization format" in exc_info.value.detail

    async def test_client_auth_invalid_token_raises_401(self, db_session: AsyncSession):
        """Test that invalid identity token raises 401."""
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_auth = AuthContextDependency(require_admin=False, require_client=True)

        # Mock validate_identity_token to return None (invalid token)
        identity_service.validate_identity_token = AsyncMock(return_value=None)
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await require_client_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                identity_service=identity_service,
                nonce_service=nonce_service,
                background_tasks=background_tasks,
                api_key=None,
                authorization="Bearer invalid_token",
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail

    async def test_client_auth_with_nonce_requirement_missing_nonce_raises_412(
        self, db_session: AsyncSession
    ):
        """Test that missing nonce raises 412 when nonce is required."""
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_with_nonce = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=True
        )

        # Mock valid identity
        account_id = AccountID()
        game_id = GameID()
        mock_identity = _create_mock_identity(account_id, game_id)
        identity_service.validate_identity_token = AsyncMock(return_value=mock_identity)
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await require_client_with_nonce(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                identity_service=identity_service,
                nonce_service=nonce_service,
                background_tasks=background_tasks,
                api_key=None,
                authorization="Bearer valid_token",
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 412
        assert "Nonce required" in exc_info.value.detail

    async def test_client_auth_with_invalid_nonce_raises_412(self, db_session: AsyncSession):
        """Test that invalid nonce raises 412."""
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_with_nonce = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=True
        )

        # Mock valid identity
        account_id = AccountID()
        game_id = GameID()
        mock_identity = _create_mock_identity(account_id, game_id)
        identity_service.validate_identity_token = AsyncMock(return_value=mock_identity)

        # Mock nonce validation to raise ValueError with "not found"
        nonce_service.validate_and_consume_nonce = AsyncMock(
            side_effect=ValueError("Nonce not found")
        )
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await require_client_with_nonce(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                identity_service=identity_service,
                nonce_service=nonce_service,
                background_tasks=background_tasks,
                api_key=None,
                authorization="Bearer valid_token",
                leadr_client_nonce="invalid_nonce",
            )

        assert exc_info.value.status_code == 412
        assert "Invalid nonce" in exc_info.value.detail

    async def test_client_auth_with_wrong_identity_nonce_raises_412(self, db_session: AsyncSession):
        """Test that nonce from wrong identity raises 412."""
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_with_nonce = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=True
        )

        # Mock valid identity
        account_id = AccountID()
        game_id = GameID()
        mock_identity = _create_mock_identity(account_id, game_id)
        identity_service.validate_identity_token = AsyncMock(return_value=mock_identity)

        # Mock nonce validation to raise ValueError with "does not belong"
        nonce_service.validate_and_consume_nonce = AsyncMock(
            side_effect=ValueError("Nonce does not belong to this identity")
        )
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await require_client_with_nonce(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                identity_service=identity_service,
                nonce_service=nonce_service,
                background_tasks=background_tasks,
                api_key=None,
                authorization="Bearer valid_token",
                leadr_client_nonce="wrong_identity_nonce",
            )

        assert exc_info.value.status_code == 412
        assert "does not belong to this identity" in exc_info.value.detail

    async def test_client_auth_with_used_nonce_raises_412(self, db_session: AsyncSession):
        """Test that already used nonce raises 412."""
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_with_nonce = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=True
        )

        # Mock valid identity
        account_id = AccountID()
        game_id = GameID()
        mock_identity = _create_mock_identity(account_id, game_id)
        identity_service.validate_identity_token = AsyncMock(return_value=mock_identity)

        # Mock nonce validation to raise ValueError with "already used"
        nonce_service.validate_and_consume_nonce = AsyncMock(
            side_effect=ValueError("Nonce already used")
        )
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await require_client_with_nonce(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                identity_service=identity_service,
                nonce_service=nonce_service,
                background_tasks=background_tasks,
                api_key=None,
                authorization="Bearer valid_token",
                leadr_client_nonce="used_nonce",
            )

        assert exc_info.value.status_code == 412
        assert "already used" in exc_info.value.detail

    async def test_client_auth_with_expired_nonce_raises_412(self, db_session: AsyncSession):
        """Test that expired nonce raises 412."""
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_with_nonce = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=True
        )

        # Mock valid identity
        account_id = AccountID()
        game_id = GameID()
        mock_identity = _create_mock_identity(account_id, game_id)
        identity_service.validate_identity_token = AsyncMock(return_value=mock_identity)

        # Mock nonce validation to raise ValueError with "expired"
        nonce_service.validate_and_consume_nonce = AsyncMock(
            side_effect=ValueError("Nonce expired")
        )
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await require_client_with_nonce(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                identity_service=identity_service,
                nonce_service=nonce_service,
                background_tasks=background_tasks,
                api_key=None,
                authorization="Bearer valid_token",
                leadr_client_nonce="expired_nonce",
            )

        assert exc_info.value.status_code == 412
        assert "expired" in exc_info.value.detail.lower()

    async def test_client_auth_valid_token_and_nonce_succeeds(self, db_session: AsyncSession):
        """Test that valid token and nonce returns ClientAuthContext."""
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_with_nonce = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=True
        )

        # Mock valid identity
        account_id = AccountID()
        game_id = GameID()
        mock_identity = _create_mock_identity(account_id, game_id)
        identity_service.validate_identity_token = AsyncMock(return_value=mock_identity)

        # Mock valid nonce
        nonce_service.validate_and_consume_nonce = AsyncMock(return_value=None)
        background_tasks = BackgroundTasks()

        result = await require_client_with_nonce(
            request=mock_request,
            api_key_service=api_key_service,
            user_service=user_service,
            identity_service=identity_service,
            nonce_service=nonce_service,
            background_tasks=background_tasks,
            api_key=None,
            authorization="Bearer valid_token",
            leadr_client_nonce="valid_nonce",
        )

        # Verify we got a ClientAuthContext
        assert result.identity is not None
        assert result.identity is not None
        assert result.account_id == account_id
        assert result.user is None
        assert result.api_key is None

    @patch("leadr.auth.dependencies.settings.DEBUG", True)
    async def test_client_auth_with_debug_logging(self, db_session: AsyncSession):
        """Test that debug logging occurs when DEBUG=True."""
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=False
        )

        # Mock valid identity
        account_id = AccountID()
        game_id = GameID()
        mock_identity = _create_mock_identity(account_id, game_id)
        identity_service.validate_identity_token = AsyncMock(return_value=mock_identity)

        # Call with debug enabled
        background_tasks = BackgroundTasks()
        result = await require_client(
            request=mock_request,
            api_key_service=api_key_service,
            user_service=user_service,
            identity_service=identity_service,
            nonce_service=nonce_service,
            background_tasks=background_tasks,
            api_key=None,
            authorization="Bearer valid_token",
            leadr_client_nonce=None,
        )

        # Verify we got a ClientAuthContext (debug logging happened internally)
        assert result.identity is not None
        assert result.identity is not None
        assert result.account_id == account_id

    async def test_client_auth_with_generic_nonce_error_raises_412(self, db_session: AsyncSession):
        """Test that generic ValueError from nonce validation raises 412 with 'Invalid nonce'."""
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_with_nonce = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=True
        )

        # Mock valid identity
        account_id = AccountID()
        game_id = GameID()
        mock_identity = _create_mock_identity(account_id, game_id)
        identity_service.validate_identity_token = AsyncMock(return_value=mock_identity)

        # Mock nonce validation to raise ValueError with message that doesn't match any pattern
        nonce_service.validate_and_consume_nonce = AsyncMock(
            side_effect=ValueError("Some unexpected error")
        )
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await require_client_with_nonce(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                identity_service=identity_service,
                nonce_service=nonce_service,
                background_tasks=background_tasks,
                api_key=None,
                authorization="Bearer valid_token",
                leadr_client_nonce="some_nonce",
            )

        assert exc_info.value.status_code == 412
        assert exc_info.value.detail == "Invalid nonce"
