"""Tests for IdentityService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from leadr.auth.domain.identity import Identity, IdentityKind, IdentitySession
from leadr.auth.services.identity_service import IdentityService
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, GameID, IdentityID, IdentitySessionID
from leadr.common.domain.pagination_result import PaginatedResult


@pytest.fixture
def mock_session():
    """Create a mock SQLAlchemy session."""
    return MagicMock()


@pytest.fixture
def service(mock_session):
    """Create IdentityService with mocked dependencies."""
    mock_device_service = AsyncMock()
    svc = IdentityService(mock_session, device_service=mock_device_service)
    svc.repository = AsyncMock()
    svc.session_repo = AsyncMock()
    return svc


@pytest.mark.asyncio
class TestIdentityServiceGetOrCreate:
    """Test suite for get_or_create_identity method."""

    async def test_creates_new_identity(self, service):
        """Test creating a new identity when one doesn't exist."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Mock repository to return None (no existing identity)
        service.repository.get_by_external_key.return_value = None

        # Create expected identity
        expected_identity = Identity(
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_12345678-1234-1234-1234-123456789012",
            display_name="Test Player",
        )
        service.repository.create.return_value = expected_identity

        identity, created = await service.get_or_create_identity(
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_12345678-1234-1234-1234-123456789012",
            display_name="Test Player",
        )

        assert created is True
        assert identity is not None
        assert identity.account_id == account_id
        assert identity.game_id == game_id
        assert identity.kind == IdentityKind.DEVICE
        assert identity.external_key == "dev_12345678-1234-1234-1234-123456789012"
        assert identity.display_name == "Test Player"

        # Verify repository.create was called
        service.repository.create.assert_called_once()

    async def test_returns_existing_identity(self, service):
        """Test that existing identity is returned instead of creating new one."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Create existing identity
        existing_identity = Identity(
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_existing_identity",
            display_name="Original Name",
        )

        # Mock repository to return existing identity
        service.repository.get_by_external_key.return_value = existing_identity

        identity, created = await service.get_or_create_identity(
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_existing_identity",
        )

        assert created is False
        assert identity.id == existing_identity.id

        # Verify create was NOT called
        service.repository.create.assert_not_called()

    async def test_updates_display_name_on_existing_identity(self, service):
        """Test that display name is updated when identity exists."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Create existing identity with original name
        existing_identity = Identity(
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_update_display_name",
            display_name="Original Name",
        )

        # Mock repository to return existing identity
        service.repository.get_by_external_key.return_value = existing_identity

        # Create updated identity for return value
        updated_identity = Identity(
            id=existing_identity.id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_update_display_name",
            display_name="New Name",
        )
        service.repository.update.return_value = updated_identity

        identity, created = await service.get_or_create_identity(
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_update_display_name",
            display_name="New Name",
        )

        assert created is False
        assert identity.id == existing_identity.id
        assert identity.display_name == "New Name"

        # Verify update was called
        service.repository.update.assert_called_once()

    async def test_creates_different_identities_for_different_kinds(self, service):
        """Test that different kinds create different identities."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Mock repository to return None for both (new identities)
        service.repository.get_by_external_key.return_value = None

        # Create expected identities
        identity_device = Identity(
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="user_123",
        )
        identity_steam = Identity(
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.STEAM,
            external_key="user_123",
        )

        # Configure create to return different identities
        service.repository.create.side_effect = [identity_device, identity_steam]

        result_device, created1 = await service.get_or_create_identity(
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="user_123",
        )

        result_steam, created2 = await service.get_or_create_identity(
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.STEAM,
            external_key="user_123",
        )

        assert created1 is True
        assert created2 is True
        assert result_device.id != result_steam.id


@pytest.mark.asyncio
class TestIdentityServiceGetIdentity:
    """Test suite for get_identity and get_identity_or_raise methods."""

    async def test_get_identity_returns_identity(self, service):
        """Test getting an identity by ID."""
        identity_id = IdentityID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        expected_identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_get_identity_test",
        )

        # Mock repository
        service.repository.get_by_id.return_value = expected_identity

        result = await service.get_identity(identity_id)

        assert result is not None
        assert result.id == identity_id

    async def test_get_identity_returns_none_for_nonexistent(self, service):
        """Test getting a non-existent identity returns None."""
        identity_id = IdentityID(uuid4())

        # Mock repository to return None
        service.repository.get_by_id.return_value = None

        result = await service.get_identity(identity_id)

        assert result is None

    async def test_get_identity_or_raise_returns_identity(self, service):
        """Test getting an identity by ID or raising."""
        identity_id = IdentityID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        expected_identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_get_or_raise_test",
        )

        # Mock repository
        service.repository.get_by_id.return_value = expected_identity

        result = await service.get_identity_or_raise(identity_id)

        assert result is not None
        assert result.id == identity_id

    async def test_get_identity_or_raise_raises_for_nonexistent(self, service):
        """Test getting a non-existent identity raises EntityNotFoundError."""
        identity_id = IdentityID(uuid4())

        # Mock repository to return None
        service.repository.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError):
            await service.get_identity_or_raise(identity_id)


@pytest.mark.asyncio
class TestIdentityServiceUpdateIdentity:
    """Test suite for update_identity method."""

    async def test_update_identity_display_name(self, service):
        """Test updating an identity's display name."""
        identity_id = IdentityID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Create original identity
        original_identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_update_identity_test",
            display_name="Original",
        )

        # Create updated identity
        updated_identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_update_identity_test",
            display_name="Updated Name",
        )

        # Mock repository
        service.repository.get_by_id.return_value = original_identity
        service.repository.update.return_value = updated_identity

        result = await service.update_identity(
            identity_id=identity_id,
            display_name="Updated Name",
        )

        assert result.display_name == "Updated Name"
        service.repository.update.assert_called_once()

    async def test_update_identity_raises_for_nonexistent(self, service):
        """Test updating a non-existent identity raises EntityNotFoundError."""
        identity_id = IdentityID(uuid4())

        # Mock repository to return None
        service.repository.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError):
            await service.update_identity(
                identity_id=identity_id,
                display_name="Test",
            )


@pytest.mark.asyncio
class TestIdentityServiceStartSession:
    """Test suite for start_session method."""

    async def test_start_session_creates_session(self, service):
        """Test that starting a session creates an IdentitySession record."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        identity_id = IdentityID(uuid4())

        # Mock device service
        mock_device = MagicMock()
        mock_device.account_id = account_id
        mock_device.game_id = game_id
        mock_device.client_fingerprint = "a" * 64
        service._device_service.get_or_create_device.return_value = mock_device

        # Mock identity creation
        expected_identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="a" * 64,
        )
        service.repository.get_by_external_key.return_value = None
        service.repository.create.return_value = expected_identity

        # Mock session creation
        created_session = IdentitySession(
            identity_id=identity_id,
            access_token_hash="test_access_hash",
            refresh_token_hash="test_refresh_hash",
            token_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            refresh_expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        service.session_repo.create.return_value = created_session

        with patch("leadr.auth.services.identity_service.generate_access_token") as mock_access:
            mock_access.return_value = ("test_access_token", "test_access_hash")
            with patch(
                "leadr.auth.services.identity_service.generate_refresh_token"
            ) as mock_refresh:
                mock_refresh.return_value = ("test_refresh_token", "test_refresh_hash")

                identity, access_token, refresh_token, expires_in = await service.start_session(
                    game_id=game_id,
                    client_fingerprint="a" * 64,
                    platform="ios",
                )

        assert access_token == "test_access_token"
        assert refresh_token == "test_refresh_token"
        assert expires_in > 0

        # Verify session was created
        service.session_repo.create.assert_called_once()
        created_session_arg = service.session_repo.create.call_args[0][0]
        assert created_session_arg.identity_id == identity_id
        assert created_session_arg.access_token_hash == "test_access_hash"
        assert created_session_arg.refresh_token_hash == "test_refresh_hash"

    async def test_start_session_uses_correct_expiration(self, service):
        """Test that session token has correct expiration time."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Mock device service
        mock_device = MagicMock()
        mock_device.account_id = account_id
        mock_device.game_id = game_id
        mock_device.client_fingerprint = "b" * 64
        service._device_service.get_or_create_device.return_value = mock_device

        # Mock identity creation
        expected_identity = Identity(
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="b" * 64,
        )
        service.repository.get_by_external_key.return_value = None
        service.repository.create.return_value = expected_identity

        # Mock session creation
        service.session_repo.create.return_value = MagicMock()

        with patch("leadr.auth.services.identity_service.generate_access_token") as mock_access:
            mock_access.return_value = ("token", "hash")
            with patch(
                "leadr.auth.services.identity_service.generate_refresh_token"
            ) as mock_refresh:
                mock_refresh.return_value = ("refresh", "refresh_hash")

                await service.start_session(
                    game_id=game_id,
                    client_fingerprint="b" * 64,
                )

                # Verify generate_access_token was called with correct expiration
                assert mock_access.called
                call_kwargs = mock_access.call_args[1]
                assert "expires_delta" in call_kwargs
                # Default should be 24 hours
                assert call_kwargs["expires_delta"] == timedelta(hours=24)


@pytest.mark.asyncio
class TestIdentityServiceValidateToken:
    """Test suite for validate_identity_token method."""

    async def test_validate_token_returns_identity_for_valid_token(self, service):
        """Test that valid token returns associated identity."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        identity_id = IdentityID(uuid4())

        # Create expected identity
        expected_identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_valid_token",
        )

        # Create valid session
        valid_session = IdentitySession(
            identity_id=identity_id,
            access_token_hash="test_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_expires_at=datetime.now(UTC) + timedelta(days=30),
        )

        # Mock repository
        service.repository.get_by_id.return_value = expected_identity
        service.session_repo.get_by_token_hash.return_value = valid_session

        # Validate token
        with patch("leadr.auth.services.identity_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_valid_token",
                "game_id": str(game_id.uuid),
                "account_id": str(account_id.uuid),
                "identity_id": str(identity_id.uuid),
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "test_hash"

                result = await service.validate_identity_token("test_token")

        assert result is not None
        assert result.id == identity_id

    async def test_validate_token_returns_none_for_invalid_jwt(self, service):
        """Test that invalid JWT returns None."""
        with patch("leadr.auth.services.identity_service.validate_access_token") as mock_val:
            mock_val.return_value = None

            result = await service.validate_identity_token("invalid_token")

        assert result is None

    async def test_validate_token_returns_none_when_identity_id_missing(self, service):
        """Test that token without identity_id returns None."""
        with patch("leadr.auth.services.identity_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": "some_key",
                "game_id": str(uuid4()),
                "account_id": str(uuid4()),
                # No identity_id
            }

            result = await service.validate_identity_token("token_without_identity")

        assert result is None

    async def test_validate_token_returns_none_for_nonexistent_identity(self, service):
        """Test that token with non-existent identity returns None."""
        nonexistent_id = IdentityID(uuid4())

        # Mock repository to return None
        service.repository.get_by_id.return_value = None

        with patch("leadr.auth.services.identity_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": "some_key",
                "game_id": str(uuid4()),
                "account_id": str(uuid4()),
                "identity_id": str(nonexistent_id.uuid),
            }

            result = await service.validate_identity_token("token_nonexistent")

        assert result is None

    async def test_validate_token_returns_none_for_expired_session(self, service):
        """Test that token with expired session returns None."""
        identity_id = IdentityID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Create identity
        expected_identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_expired_session",
        )

        # Create expired session
        expired_session = IdentitySession(
            identity_id=identity_id,
            access_token_hash="expired_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired
            refresh_expires_at=datetime.now(UTC) + timedelta(days=30),
        )

        # Mock repository
        service.repository.get_by_id.return_value = expected_identity
        service.session_repo.get_by_token_hash.return_value = expired_session

        with patch("leadr.auth.services.identity_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_expired_session",
                "game_id": str(game_id.uuid),
                "account_id": str(account_id.uuid),
                "identity_id": str(identity_id.uuid),
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "expired_hash"

                result = await service.validate_identity_token("expired_token")

        assert result is None

    async def test_validate_token_returns_none_for_revoked_session(self, service):
        """Test that token with revoked session returns None."""
        identity_id = IdentityID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Create identity
        expected_identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_revoked_session",
        )

        # Create revoked session
        revoked_session = IdentitySession(
            identity_id=identity_id,
            access_token_hash="revoked_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_expires_at=datetime.now(UTC) + timedelta(days=30),
            revoked_at=datetime.now(UTC),  # Revoked
        )

        # Mock repository
        service.repository.get_by_id.return_value = expected_identity
        service.session_repo.get_by_token_hash.return_value = revoked_session

        with patch("leadr.auth.services.identity_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_revoked_session",
                "game_id": str(game_id.uuid),
                "account_id": str(account_id.uuid),
                "identity_id": str(identity_id.uuid),
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "revoked_hash"

                result = await service.validate_identity_token("revoked_token")

        assert result is None

    async def test_validate_token_returns_none_when_session_not_found(self, service):
        """Test that token without matching session returns None."""
        identity_id = IdentityID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Create identity
        expected_identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_no_session",
        )

        # Mock repository
        service.repository.get_by_id.return_value = expected_identity
        service.session_repo.get_by_token_hash.return_value = None  # No session

        with patch("leadr.auth.services.identity_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_no_session",
                "game_id": str(game_id.uuid),
                "account_id": str(account_id.uuid),
                "identity_id": str(identity_id.uuid),
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "nonexistent_hash"

                result = await service.validate_identity_token("token_no_session")

        assert result is None


@pytest.mark.asyncio
class TestIdentityServiceRefreshToken:
    """Test suite for refresh_access_token method."""

    async def test_refresh_token_success(self, service):
        """Test successfully refreshing an access token."""
        identity_id = IdentityID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Create identity
        expected_identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_refresh_success",
        )

        # Create session
        now = datetime.now(UTC)
        session = IdentitySession(
            identity_id=identity_id,
            access_token_hash="old_access_hash",
            refresh_token_hash="old_refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )

        # Mock repository
        service.repository.get_by_id.return_value = expected_identity
        service.session_repo.get_by_refresh_token_hash.return_value = session
        service.session_repo.update.return_value = session

        with patch("leadr.auth.services.identity_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_refresh_success",
                "game_id": str(game_id.uuid),
                "account_id": str(account_id.uuid),
                "identity_id": str(identity_id.uuid),
                "token_version": 1,
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "old_refresh_hash"
                with patch(
                    "leadr.auth.services.identity_service.generate_access_token"
                ) as mock_gen_access:
                    mock_gen_access.return_value = ("new_access_token", "new_access_hash")
                    with patch(
                        "leadr.auth.services.identity_service.generate_refresh_token"
                    ) as mock_gen_refresh:
                        mock_gen_refresh.return_value = ("new_refresh_token", "new_refresh_hash")

                        result = await service.refresh_access_token("old_refresh_token")

        assert result is not None
        access_token, refresh_token, expires_in = result
        assert access_token == "new_access_token"
        assert refresh_token == "new_refresh_token"
        assert expires_in > 0

        # Verify session was updated
        service.session_repo.update.assert_called_once()

    async def test_refresh_token_rejects_invalid_jwt(self, service):
        """Test that invalid refresh JWT is rejected."""
        with patch("leadr.auth.services.identity_service.validate_refresh_token") as mock_val:
            mock_val.return_value = None

            result = await service.refresh_access_token("invalid_token")

        assert result is None

    async def test_refresh_token_rejects_when_session_not_found(self, service):
        """Test that refresh is rejected when session not found."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())

        # Mock session_repo to return None
        service.session_repo.get_by_refresh_token_hash.return_value = None

        with patch("leadr.auth.services.identity_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": "some_key",
                "game_id": str(game_id.uuid),
                "account_id": str(account_id.uuid),
                "token_version": 1,
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "nonexistent_hash"

                result = await service.refresh_access_token("orphan_token")

        assert result is None

    async def test_refresh_token_rejects_mismatched_version(self, service):
        """Test that refresh token with mismatched version is rejected."""
        identity_id = IdentityID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Create session with version 2
        now = datetime.now(UTC)
        session = IdentitySession(
            identity_id=identity_id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=2,  # Version 2 in session
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )

        # Mock repository
        service.session_repo.get_by_refresh_token_hash.return_value = session

        with patch("leadr.auth.services.identity_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_version_mismatch",
                "game_id": str(game_id.uuid),
                "account_id": str(account_id.uuid),
                "token_version": 1,  # Old version in token
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "refresh_hash"

                result = await service.refresh_access_token("old_version_token")

        assert result is None

    async def test_refresh_token_rejects_expired_refresh(self, service):
        """Test that expired refresh token is rejected."""
        identity_id = IdentityID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Create session with expired refresh
        now = datetime.now(UTC)
        session = IdentitySession(
            identity_id=identity_id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now - timedelta(days=1),  # Expired
        )

        # Mock repository
        service.session_repo.get_by_refresh_token_hash.return_value = session

        with patch("leadr.auth.services.identity_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_expired_refresh",
                "game_id": str(game_id.uuid),
                "account_id": str(account_id.uuid),
                "token_version": 1,
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "refresh_hash"

                result = await service.refresh_access_token("expired_refresh_token")

        assert result is None

    async def test_refresh_token_rejects_revoked_session(self, service):
        """Test that refresh token with revoked session is rejected."""
        identity_id = IdentityID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Create revoked session
        now = datetime.now(UTC)
        session = IdentitySession(
            identity_id=identity_id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
            revoked_at=now - timedelta(minutes=5),  # Revoked
        )

        # Mock repository
        service.session_repo.get_by_refresh_token_hash.return_value = session

        with patch("leadr.auth.services.identity_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_revoked_refresh",
                "game_id": str(game_id.uuid),
                "account_id": str(account_id.uuid),
                "token_version": 1,
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "refresh_hash"

                result = await service.refresh_access_token("revoked_token")

        assert result is None

    async def test_refresh_token_rejects_when_identity_deleted(self, service):
        """Test that refresh is rejected when identity is soft-deleted."""
        identity_id = IdentityID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Create session
        now = datetime.now(UTC)
        session = IdentitySession(
            identity_id=identity_id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )

        # Mock repository - identity not found (soft-deleted)
        service.session_repo.get_by_refresh_token_hash.return_value = session
        service.repository.get_by_id.return_value = None  # Identity deleted

        with patch("leadr.auth.services.identity_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_deleted_identity_test",
                "game_id": str(game_id.uuid),
                "account_id": str(account_id.uuid),
                "token_version": 1,
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "refresh_hash"

                result = await service.refresh_access_token("deleted_identity_token")

        assert result is None


@pytest.mark.asyncio
class TestIdentityServiceSessionManagement:
    """Test suite for session management methods."""

    async def test_get_session_returns_session(self, service):
        """Test getting a session by ID."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())

        # Create expected session
        now = datetime.now(UTC)
        expected_session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )

        # Mock repository
        service.session_repo.get_by_id.return_value = expected_session

        result = await service.get_session(session_id)

        assert result is not None
        assert result.id == session_id

    async def test_get_session_returns_none_for_nonexistent(self, service):
        """Test getting a non-existent session returns None."""
        session_id = IdentitySessionID(uuid4())

        # Mock repository to return None
        service.session_repo.get_by_id.return_value = None

        result = await service.get_session(session_id)

        assert result is None

    async def test_get_session_or_raise_returns_session(self, service):
        """Test getting a session by ID or raising."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())

        # Create expected session
        now = datetime.now(UTC)
        expected_session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )

        # Mock repository
        service.session_repo.get_by_id.return_value = expected_session

        result = await service.get_session_or_raise(session_id)

        assert result is not None
        assert result.id == session_id

    async def test_get_session_or_raise_raises_for_nonexistent(self, service):
        """Test getting a non-existent session raises EntityNotFoundError."""
        session_id = IdentitySessionID(uuid4())

        # Mock repository to return None
        service.session_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError):
            await service.get_session_or_raise(session_id)

    async def test_revoke_session_sets_revoked_at(self, service):
        """Test revoking a session sets revoked_at."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())

        # Create session
        now = datetime.now(UTC)
        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )

        # Create revoked session (return value)
        revoked_session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
            revoked_at=now,
        )

        # Mock repository
        service.session_repo.get_by_id.return_value = session
        service.session_repo.update.return_value = revoked_session

        result = await service.revoke_session(session_id)

        assert result.revoked_at is not None
        assert result.is_revoked() is True
        service.session_repo.update.assert_called_once()

    async def test_revoke_session_raises_for_nonexistent(self, service):
        """Test revoking a non-existent session raises EntityNotFoundError."""
        session_id = IdentitySessionID(uuid4())

        # Mock repository to return None
        service.session_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError):
            await service.revoke_session(session_id)


@pytest.mark.asyncio
class TestIdentityServiceListMethods:
    """Test suite for list methods."""

    async def test_list_identities_returns_all_for_account(self, service):
        """Test listing identities for an account."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Create expected identities
        identity1 = Identity(
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_list_1",
        )
        identity2 = Identity(
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.STEAM,
            external_key="steam_list_1",
        )

        # Mock repository
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        expected_result = PaginatedResult(
            items=[identity1, identity2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter.return_value = expected_result

        result = await service.list_identities(
            account_id=account_id,
            pagination=pagination,
        )

        assert len(result.items) == 2

    async def test_list_identities_filters_by_kind(self, service):
        """Test filtering identities by kind."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Create expected identity
        identity1 = Identity(
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_filter_kind_1",
        )

        # Mock repository
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        expected_result = PaginatedResult(
            items=[identity1],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter.return_value = expected_result

        result = await service.list_identities(
            account_id=account_id,
            kind=IdentityKind.DEVICE,
            pagination=pagination,
        )

        assert len(result.items) == 1
        assert result.items[0].kind == IdentityKind.DEVICE

    async def test_list_sessions_returns_all_for_identity(self, service):
        """Test listing sessions for an identity."""
        account_id = AccountID(uuid4())
        identity_id = IdentityID(uuid4())

        # Create expected sessions
        now = datetime.now(UTC)
        session1 = IdentitySession(
            identity_id=identity_id,
            access_token_hash="hash1",
            refresh_token_hash="refresh_hash1",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )
        session2 = IdentitySession(
            identity_id=identity_id,
            access_token_hash="hash2",
            refresh_token_hash="refresh_hash2",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )

        # Mock repository
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        expected_result = PaginatedResult(
            items=[session1, session2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.session_repo.filter.return_value = expected_result

        result = await service.list_sessions(
            account_id=account_id,
            identity_id=identity_id,
            pagination=pagination,
        )

        assert len(result.items) == 2
