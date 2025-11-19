"""Tests for client authentication and OR logic (admin+client) paths."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.accounts.services.user_service import UserService
from leadr.auth.dependencies import AuthContextDependency, require_admin_or_client_auth
from leadr.auth.domain.device import Device, DeviceStatus
from leadr.auth.services.api_key_service import APIKeyService
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.nonce_service import NonceService
from leadr.common.domain.ids import AccountID, DeviceID, GameID


@pytest.mark.asyncio
class TestClientOnlyAuth:
    """Test suite for client-only authentication path."""

    @patch("leadr.auth.dependencies.settings.ENABLE_CLIENT_API", False)
    async def test_client_auth_when_client_api_disabled_raises_500(self, db_session: AsyncSession):
        """Test that client auth raises 500 when ENABLE_CLIENT_API is False."""
        device_service = DeviceService(db_session)
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        # Create dependency requiring client auth
        require_client_auth = AuthContextDependency(require_admin=False, require_client=True)

        with pytest.raises(HTTPException) as exc_info:
            await require_client_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                device_service=device_service,
                nonce_service=nonce_service,
                api_key=None,
                authorization="Bearer test_token",
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 500
        assert "Client API is not enabled" in exc_info.value.detail

    async def test_client_auth_missing_bearer_token_raises_401(self, db_session: AsyncSession):
        """Test that missing bearer token raises 401."""
        device_service = DeviceService(db_session)
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_auth = AuthContextDependency(require_admin=False, require_client=True)

        with pytest.raises(HTTPException) as exc_info:
            await require_client_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                device_service=device_service,
                nonce_service=nonce_service,
                api_key=None,
                authorization=None,
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 401
        assert "require" in exc_info.value.detail.lower()

    async def test_client_auth_invalid_bearer_format_raises_401(self, db_session: AsyncSession):
        """Test that invalid bearer token format raises 401."""
        device_service = DeviceService(db_session)
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_auth = AuthContextDependency(require_admin=False, require_client=True)

        with pytest.raises(HTTPException) as exc_info:
            await require_client_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                device_service=device_service,
                nonce_service=nonce_service,
                api_key=None,
                authorization="InvalidFormat",
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 401
        assert "Invalid authorization format" in exc_info.value.detail

    async def test_client_auth_invalid_token_raises_401(self, db_session: AsyncSession):
        """Test that invalid device token raises 401."""
        device_service = DeviceService(db_session)
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_auth = AuthContextDependency(require_admin=False, require_client=True)

        # Mock validate_device_token to return None (invalid token)
        device_service.validate_device_token = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await require_client_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                device_service=device_service,
                nonce_service=nonce_service,
                api_key=None,
                authorization="Bearer invalid_token",
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 401
        assert "Invalid or expired device token" in exc_info.value.detail

    async def test_client_auth_with_nonce_requirement_missing_nonce_raises_412(
        self, db_session: AsyncSession
    ):
        """Test that missing nonce raises 412 when nonce is required."""
        device_service = DeviceService(db_session)
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_with_nonce = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=True
        )

        # Mock valid device
        now = datetime.now(UTC)
        mock_device = Device(
            id=DeviceID(),
            account_id=AccountID(),
            game_id=GameID(),
            client_fingerprint="a" * 64,  # Valid SHA256 hash
            platform="test",
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        device_service.validate_device_token = AsyncMock(return_value=mock_device)

        with pytest.raises(HTTPException) as exc_info:
            await require_client_with_nonce(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                device_service=device_service,
                nonce_service=nonce_service,
                api_key=None,
                authorization="Bearer valid_token",
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 412
        assert "Nonce required" in exc_info.value.detail

    async def test_client_auth_with_invalid_nonce_raises_412(self, db_session: AsyncSession):
        """Test that invalid nonce raises 412."""
        device_service = DeviceService(db_session)
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_with_nonce = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=True
        )

        # Mock valid device
        now = datetime.now(UTC)
        mock_device = Device(
            id=DeviceID(),
            account_id=AccountID(),
            game_id=GameID(),
            client_fingerprint="a" * 64,  # Valid SHA256 hash
            platform="test",
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        device_service.validate_device_token = AsyncMock(return_value=mock_device)

        # Mock nonce validation to raise ValueError with "not found"
        nonce_service.validate_and_consume_nonce = AsyncMock(
            side_effect=ValueError("Nonce not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_client_with_nonce(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                device_service=device_service,
                nonce_service=nonce_service,
                api_key=None,
                authorization="Bearer valid_token",
                leadr_client_nonce="invalid_nonce",
            )

        assert exc_info.value.status_code == 412
        assert "Invalid nonce" in exc_info.value.detail

    async def test_client_auth_with_wrong_device_nonce_raises_412(self, db_session: AsyncSession):
        """Test that nonce from wrong device raises 412."""
        device_service = DeviceService(db_session)
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_with_nonce = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=True
        )

        # Mock valid device
        now = datetime.now(UTC)
        mock_device = Device(
            id=DeviceID(),
            account_id=AccountID(),
            game_id=GameID(),
            client_fingerprint="a" * 64,  # Valid SHA256 hash
            platform="test",
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        device_service.validate_device_token = AsyncMock(return_value=mock_device)

        # Mock nonce validation to raise ValueError with "does not belong"
        nonce_service.validate_and_consume_nonce = AsyncMock(
            side_effect=ValueError("Nonce does not belong to device")
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_client_with_nonce(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                device_service=device_service,
                nonce_service=nonce_service,
                api_key=None,
                authorization="Bearer valid_token",
                leadr_client_nonce="wrong_device_nonce",
            )

        assert exc_info.value.status_code == 412
        assert "does not belong to this device" in exc_info.value.detail

    async def test_client_auth_with_used_nonce_raises_412(self, db_session: AsyncSession):
        """Test that already used nonce raises 412."""
        device_service = DeviceService(db_session)
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_with_nonce = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=True
        )

        # Mock valid device
        now = datetime.now(UTC)
        mock_device = Device(
            id=DeviceID(),
            account_id=AccountID(),
            game_id=GameID(),
            client_fingerprint="a" * 64,  # Valid SHA256 hash
            platform="test",
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        device_service.validate_device_token = AsyncMock(return_value=mock_device)

        # Mock nonce validation to raise ValueError with "already used"
        nonce_service.validate_and_consume_nonce = AsyncMock(
            side_effect=ValueError("Nonce already used")
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_client_with_nonce(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                device_service=device_service,
                nonce_service=nonce_service,
                api_key=None,
                authorization="Bearer valid_token",
                leadr_client_nonce="used_nonce",
            )

        assert exc_info.value.status_code == 412
        assert "already used" in exc_info.value.detail

    async def test_client_auth_with_expired_nonce_raises_412(self, db_session: AsyncSession):
        """Test that expired nonce raises 412."""
        device_service = DeviceService(db_session)
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_with_nonce = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=True
        )

        # Mock valid device
        now = datetime.now(UTC)
        mock_device = Device(
            id=DeviceID(),
            account_id=AccountID(),
            game_id=GameID(),
            client_fingerprint="a" * 64,  # Valid SHA256 hash
            platform="test",
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        device_service.validate_device_token = AsyncMock(return_value=mock_device)

        # Mock nonce validation to raise ValueError with "expired"
        nonce_service.validate_and_consume_nonce = AsyncMock(
            side_effect=ValueError("Nonce expired")
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_client_with_nonce(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                device_service=device_service,
                nonce_service=nonce_service,
                api_key=None,
                authorization="Bearer valid_token",
                leadr_client_nonce="expired_nonce",
            )

        assert exc_info.value.status_code == 412
        assert "expired" in exc_info.value.detail.lower()

    async def test_client_auth_valid_token_and_nonce_succeeds(self, db_session: AsyncSession):
        """Test that valid token and nonce returns ClientAuthContext."""
        device_service = DeviceService(db_session)
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_with_nonce = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=True
        )

        # Mock valid device
        now = datetime.now(UTC)
        account_id = AccountID()
        mock_device = Device(
            id=DeviceID(),
            account_id=account_id,
            game_id=GameID(),
            client_fingerprint="d" * 64,  # Valid SHA256 hash
            platform="test",
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        device_service.validate_device_token = AsyncMock(return_value=mock_device)

        # Mock valid nonce
        nonce_service.validate_and_consume_nonce = AsyncMock(return_value=None)

        result = await require_client_with_nonce(
            request=mock_request,
            api_key_service=api_key_service,
            user_service=user_service,
            device_service=device_service,
            nonce_service=nonce_service,
            api_key=None,
            authorization="Bearer valid_token",
            leadr_client_nonce="valid_nonce",
        )

        # Verify we got a ClientAuthContext
        assert result.device is not None
        assert result.account_id == account_id
        assert result.user is None
        assert result.api_key is None

    @patch("leadr.auth.dependencies.settings.DEBUG", True)
    async def test_client_auth_with_debug_logging(self, db_session: AsyncSession):
        """Test that debug logging occurs when DEBUG=True."""
        device_service = DeviceService(db_session)
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=False
        )

        # Mock valid device
        now = datetime.now(UTC)
        account_id = AccountID()
        mock_device = Device(
            id=DeviceID(),
            account_id=account_id,
            game_id=GameID(),
            client_fingerprint="e" * 64,  # Valid SHA256 hash
            platform="test",
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        device_service.validate_device_token = AsyncMock(return_value=mock_device)

        # Call with debug enabled
        result = await require_client(
            request=mock_request,
            api_key_service=api_key_service,
            user_service=user_service,
            device_service=device_service,
            nonce_service=nonce_service,
            api_key=None,
            authorization="Bearer valid_token",
            leadr_client_nonce=None,
        )

        # Verify we got a ClientAuthContext (debug logging happened internally)
        assert result.device is not None
        assert result.account_id == account_id

    async def test_client_auth_with_generic_nonce_error_raises_412(self, db_session: AsyncSession):
        """Test that generic ValueError from nonce validation raises 412 with 'Invalid nonce'."""
        device_service = DeviceService(db_session)
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        require_client_with_nonce = AuthContextDependency(
            require_admin=False, require_client=True, require_nonce=True
        )

        # Mock valid device
        now = datetime.now(UTC)
        mock_device = Device(
            id=DeviceID(),
            account_id=AccountID(),
            game_id=GameID(),
            client_fingerprint="a" * 64,  # Valid SHA256 hash
            platform="test",
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        device_service.validate_device_token = AsyncMock(return_value=mock_device)

        # Mock nonce validation to raise ValueError with message that doesn't match any pattern
        nonce_service.validate_and_consume_nonce = AsyncMock(
            side_effect=ValueError("Some unexpected error")
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_client_with_nonce(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                device_service=device_service,
                nonce_service=nonce_service,
                api_key=None,
                authorization="Bearer valid_token",
                leadr_client_nonce="some_nonce",
            )

        assert exc_info.value.status_code == 412
        assert exc_info.value.detail == "Invalid nonce"


@pytest.mark.asyncio
class TestORLogicAuth:
    """Test suite for OR logic (admin OR client) authentication."""

    @patch("leadr.auth.dependencies.settings.ENABLE_ADMIN_API", False)
    @patch("leadr.auth.dependencies.settings.ENABLE_CLIENT_API", False)
    async def test_or_logic_when_both_apis_disabled_raises_500(self, db_session: AsyncSession):
        """Test that OR logic raises 500 when both APIs are disabled."""
        device_service = DeviceService(db_session)
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await require_admin_or_client_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                device_service=device_service,
                nonce_service=nonce_service,
                api_key="ldr_test",
                authorization="Bearer test_token",
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 500
        assert "Neither Admin nor Client API is enabled" in exc_info.value.detail

    async def test_or_logic_prefers_client_auth_when_bearer_provided(
        self, db_session: AsyncSession
    ):
        """Test that OR logic tries client auth first when bearer token is provided."""
        device_service = DeviceService(db_session)
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        # Mock valid device (client auth succeeds)
        now = datetime.now(UTC)
        account_id = AccountID()
        mock_device = Device(
            id=DeviceID(),
            account_id=account_id,
            game_id=GameID(),
            client_fingerprint="f" * 64,  # Valid SHA256 hash
            platform="test",
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        device_service.validate_device_token = AsyncMock(return_value=mock_device)

        result = await require_admin_or_client_auth(
            request=mock_request,
            api_key_service=api_key_service,
            user_service=user_service,
            device_service=device_service,
            nonce_service=nonce_service,
            api_key="ldr_test",  # API key also provided
            authorization="Bearer valid_token",  # But bearer takes precedence
            leadr_client_nonce=None,
        )

        # Should return ClientAuthContext (client auth was tried first)
        assert result.device is not None
        assert result.account_id == account_id

    async def test_or_logic_falls_back_to_admin_when_client_fails(self, db_session: AsyncSession):
        """Test that OR logic falls back to admin auth when client auth fails."""
        # Create account and user for admin auth
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

        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account_id,
            email=f"test-{str(account_id)[:8]}@example.com",
            display_name="Test User",
        )

        api_key_service = APIKeyService(db_session)
        api_key, plain_key = await api_key_service.create_api_key(
            account_id=account_id,
            user_id=user.id,
            name="Test Key",
            expires_at=None,
        )

        device_service = DeviceService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        # Mock invalid device (client auth fails)
        device_service.validate_device_token = AsyncMock(return_value=None)

        result = await require_admin_or_client_auth(
            request=mock_request,
            api_key_service=api_key_service,
            user_service=user_service,
            device_service=device_service,
            nonce_service=nonce_service,
            api_key=plain_key,  # Valid admin API key
            authorization="Bearer invalid_token",  # Invalid client token
            leadr_client_nonce=None,
        )

        # Should return AdminAuthContext (fallback to admin auth)
        assert result.api_key is not None
        assert result.user is not None
        assert result.account_id == account_id

    async def test_or_logic_with_only_api_key_uses_admin_auth(self, db_session: AsyncSession):
        """Test that OR logic uses admin auth when only API key is provided."""
        # Create account and user for admin auth
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

        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account_id,
            email=f"test-{str(account_id)[:8]}@example.com",
            display_name="Test User",
        )

        api_key_service = APIKeyService(db_session)
        api_key, plain_key = await api_key_service.create_api_key(
            account_id=account_id,
            user_id=user.id,
            name="Test Key",
            expires_at=None,
        )

        device_service = DeviceService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        result = await require_admin_or_client_auth(
            request=mock_request,
            api_key_service=api_key_service,
            user_service=user_service,
            device_service=device_service,
            nonce_service=nonce_service,
            api_key=plain_key,
            authorization=None,  # No bearer token
            leadr_client_nonce=None,
        )

        # Should return AdminAuthContext
        assert result.api_key is not None
        assert result.user is not None
        assert result.account_id == account_id

    async def test_or_logic_when_neither_auth_succeeds_raises_401(self, db_session: AsyncSession):
        """Test that OR logic raises 401 when neither auth method succeeds."""
        device_service = DeviceService(db_session)
        api_key_service = APIKeyService(db_session)
        user_service = UserService(db_session)
        nonce_service = NonceService(db_session)
        mock_request = Mock()

        # Mock invalid device
        device_service.validate_device_token = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await require_admin_or_client_auth(
                request=mock_request,
                api_key_service=api_key_service,
                user_service=user_service,
                device_service=device_service,
                nonce_service=nonce_service,
                api_key="ldr_invalid",  # Invalid API key
                authorization="Bearer invalid_token",  # Invalid token
                leadr_client_nonce=None,
            )

        assert exc_info.value.status_code == 401
        assert "Valid authentication required" in exc_info.value.detail
