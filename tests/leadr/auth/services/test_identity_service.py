"""Tests for IdentityService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.adapters.orm import AccountORM
from leadr.auth.adapters.orm import IdentityKindEnum, IdentityORM, IdentitySessionORM
from leadr.auth.domain.identity import IdentityKind
from leadr.auth.services.identity_service import IdentityService
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, GameID, IdentityID, IdentitySessionID
from leadr.games.adapters.orm import GameORM


@pytest.mark.asyncio
class TestIdentityServiceGetOrCreate:
    """Test suite for get_or_create_identity method."""

    async def test_creates_new_identity(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test creating a new identity when one doesn't exist."""
        service = IdentityService(db_session)

        identity, created = await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.DEVICE,
            external_key="dev_12345678-1234-1234-1234-123456789012",
            display_name="Test Player",
        )

        assert created is True
        assert identity is not None
        assert identity.account_id == account_orm.id
        assert identity.game_id == game_orm.id
        assert identity.kind == IdentityKind.DEVICE
        assert identity.external_key == "dev_12345678-1234-1234-1234-123456789012"
        assert identity.display_name == "Test Player"

    async def test_returns_existing_identity(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test that existing identity is returned instead of creating new one."""
        service = IdentityService(db_session)

        # Create first identity
        identity1, created1 = await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.DEVICE,
            external_key="dev_existing_identity",
            display_name="Original Name",
        )
        assert created1 is True

        # Try to create same identity again
        identity2, created2 = await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.DEVICE,
            external_key="dev_existing_identity",
        )

        assert created2 is False
        assert identity2.id == identity1.id

    async def test_updates_display_name_on_existing_identity(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test that display name is updated when identity exists."""
        service = IdentityService(db_session)

        # Create first identity
        identity1, _ = await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.DEVICE,
            external_key="dev_update_display_name",
            display_name="Original Name",
        )
        assert identity1.display_name == "Original Name"

        # Get same identity with different display name
        identity2, created = await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.DEVICE,
            external_key="dev_update_display_name",
            display_name="New Name",
        )

        assert created is False
        assert identity2.id == identity1.id
        assert identity2.display_name == "New Name"

    async def test_creates_different_identities_for_different_kinds(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test that different kinds create different identities."""
        service = IdentityService(db_session)

        identity_device, created1 = await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.DEVICE,
            external_key="user_123",
        )

        identity_steam, created2 = await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.STEAM,
            external_key="user_123",
        )

        assert created1 is True
        assert created2 is True
        assert identity_device.id != identity_steam.id


@pytest.mark.asyncio
class TestIdentityServiceGetIdentity:
    """Test suite for get_identity and get_identity_or_raise methods."""

    async def test_get_identity_returns_identity(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test getting an identity by ID."""
        service = IdentityService(db_session)

        identity, _ = await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.DEVICE,
            external_key="dev_get_identity_test",
        )

        result = await service.get_identity(identity.id)

        assert result is not None
        assert result.id == identity.id

    async def test_get_identity_returns_none_for_nonexistent(self, db_session: AsyncSession):
        """Test getting a non-existent identity returns None."""
        service = IdentityService(db_session)

        result = await service.get_identity(IdentityID(uuid4()))

        assert result is None

    async def test_get_identity_or_raise_returns_identity(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test getting an identity by ID or raising."""
        service = IdentityService(db_session)

        identity, _ = await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.DEVICE,
            external_key="dev_get_or_raise_test",
        )

        result = await service.get_identity_or_raise(identity.id)

        assert result is not None
        assert result.id == identity.id

    async def test_get_identity_or_raise_raises_for_nonexistent(self, db_session: AsyncSession):
        """Test getting a non-existent identity raises EntityNotFoundError."""
        service = IdentityService(db_session)

        with pytest.raises(EntityNotFoundError):
            await service.get_identity_or_raise(IdentityID(uuid4()))


@pytest.mark.asyncio
class TestIdentityServiceUpdateIdentity:
    """Test suite for update_identity method."""

    async def test_update_identity_display_name(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test updating an identity's display name."""
        service = IdentityService(db_session)

        identity, _ = await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.DEVICE,
            external_key="dev_update_identity_test",
            display_name="Original",
        )

        updated = await service.update_identity(
            identity_id=identity.id,
            display_name="Updated Name",
        )

        assert updated.display_name == "Updated Name"

    async def test_update_identity_raises_for_nonexistent(self, db_session: AsyncSession):
        """Test updating a non-existent identity raises EntityNotFoundError."""
        service = IdentityService(db_session)

        with pytest.raises(EntityNotFoundError):
            await service.update_identity(
                identity_id=IdentityID(uuid4()),
                display_name="Test",
            )


@pytest.mark.asyncio
class TestIdentityServiceStartSession:
    """Test suite for start_session method."""

    async def test_start_session_creates_session(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test that starting a session creates an IdentitySession record."""
        service = IdentityService(db_session)

        identity, _ = await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.DEVICE,
            external_key="dev_start_session_test",
        )

        with patch("leadr.auth.services.identity_service.generate_access_token") as mock_access:
            mock_access.return_value = ("test_access_token", "test_access_hash")
            with patch(
                "leadr.auth.services.identity_service.generate_refresh_token"
            ) as mock_refresh:
                mock_refresh.return_value = ("test_refresh_token", "test_refresh_hash")

                access_token, refresh_token, expires_in = await service.start_session(
                    identity=identity,
                    ip_address="192.168.1.1",
                    user_agent="TestApp/1.0",
                )

        assert access_token == "test_access_token"
        assert refresh_token == "test_refresh_token"
        assert expires_in > 0

        # Verify session was created
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.list_sessions(
            account_id=AccountID(account_orm.id),
            identity_id=identity.id,
            pagination=pagination,
        )
        assert len(result.items) == 1
        assert result.items[0].identity_id == identity.id
        assert result.items[0].access_token_hash == "test_access_hash"
        assert result.items[0].refresh_token_hash == "test_refresh_hash"
        assert result.items[0].ip_address == "192.168.1.1"
        assert result.items[0].user_agent == "TestApp/1.0"

    async def test_start_session_uses_correct_expiration(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test that session token has correct expiration time."""
        service = IdentityService(db_session)

        identity, _ = await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.DEVICE,
            external_key="dev_expiration_test",
        )

        with patch("leadr.auth.services.identity_service.generate_access_token") as mock_access:
            mock_access.return_value = ("token", "hash")
            with patch(
                "leadr.auth.services.identity_service.generate_refresh_token"
            ) as mock_refresh:
                mock_refresh.return_value = ("refresh", "refresh_hash")

                await service.start_session(identity=identity)

                # Verify generate_access_token was called with correct expiration
                assert mock_access.called
                call_kwargs = mock_access.call_args[1]
                assert "expires_delta" in call_kwargs
                # Default should be 24 hours
                assert call_kwargs["expires_delta"] == timedelta(hours=24)


@pytest.mark.asyncio
class TestIdentityServiceValidateToken:
    """Test suite for validate_identity_token method."""

    async def test_validate_token_returns_identity_for_valid_token(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test that valid token returns associated identity."""
        service = IdentityService(db_session)

        identity, _ = await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.DEVICE,
            external_key="dev_validate_token_test",
        )

        with patch("leadr.auth.services.identity_service.generate_access_token") as mock_access:
            mock_access.return_value = ("test_token", "test_hash")
            with patch(
                "leadr.auth.services.identity_service.generate_refresh_token"
            ) as mock_refresh:
                mock_refresh.return_value = ("test_refresh", "test_refresh_hash")
                await service.start_session(identity=identity)

        # Validate token
        with patch("leadr.auth.services.identity_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": identity.external_key,
                "game_id": str(game_orm.id),
                "account_id": str(account_orm.id),
                "identity_id": str(identity.id.uuid),
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "test_hash"

                result = await service.validate_identity_token("test_token")

        assert result is not None
        assert result.id == identity.id

    async def test_validate_token_returns_none_for_invalid_jwt(self, db_session: AsyncSession):
        """Test that invalid JWT returns None."""
        service = IdentityService(db_session)

        with patch("leadr.auth.services.identity_service.validate_access_token") as mock_val:
            mock_val.return_value = None

            result = await service.validate_identity_token("invalid_token")

        assert result is None

    async def test_validate_token_returns_none_when_identity_id_missing(
        self, db_session: AsyncSession
    ):
        """Test that token without identity_id returns None."""
        service = IdentityService(db_session)

        with patch("leadr.auth.services.identity_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": "some_key",
                "game_id": str(uuid4()),
                "account_id": str(uuid4()),
                # No identity_id
            }

            result = await service.validate_identity_token("token_without_identity")

        assert result is None

    async def test_validate_token_returns_none_for_nonexistent_identity(
        self, db_session: AsyncSession
    ):
        """Test that token with non-existent identity returns None."""
        service = IdentityService(db_session)

        nonexistent_id = uuid4()

        with patch("leadr.auth.services.identity_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": "some_key",
                "game_id": str(uuid4()),
                "account_id": str(uuid4()),
                "identity_id": str(nonexistent_id),
            }

            result = await service.validate_identity_token("token_nonexistent")

        assert result is None

    async def test_validate_token_returns_none_for_expired_session(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test that token with expired session returns None."""
        # Create identity directly in ORM
        identity_orm = IdentityORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            kind=IdentityKindEnum.DEVICE,
            external_key="dev_expired_session",
        )
        db_session.add(identity_orm)
        await db_session.commit()

        # Create expired session
        expired_session = IdentitySessionORM(
            id=uuid4(),
            identity_id=identity_orm.id,
            access_token_hash="expired_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired
            refresh_expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        db_session.add(expired_session)
        await db_session.commit()

        service = IdentityService(db_session)

        with patch("leadr.auth.services.identity_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_expired_session",
                "game_id": str(game_orm.id),
                "account_id": str(account_orm.id),
                "identity_id": str(identity_orm.id),
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "expired_hash"

                result = await service.validate_identity_token("expired_token")

        assert result is None

    async def test_validate_token_returns_none_for_revoked_session(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test that token with revoked session returns None."""
        # Create identity directly in ORM
        identity_orm = IdentityORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            kind=IdentityKindEnum.DEVICE,
            external_key="dev_revoked_session",
        )
        db_session.add(identity_orm)
        await db_session.commit()

        # Create revoked session
        revoked_session = IdentitySessionORM(
            id=uuid4(),
            identity_id=identity_orm.id,
            access_token_hash="revoked_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_expires_at=datetime.now(UTC) + timedelta(days=30),
            revoked_at=datetime.now(UTC),  # Revoked
        )
        db_session.add(revoked_session)
        await db_session.commit()

        service = IdentityService(db_session)

        with patch("leadr.auth.services.identity_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_revoked_session",
                "game_id": str(game_orm.id),
                "account_id": str(account_orm.id),
                "identity_id": str(identity_orm.id),
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "revoked_hash"

                result = await service.validate_identity_token("revoked_token")

        assert result is None

    async def test_validate_token_returns_none_when_session_not_found(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test that token without matching session returns None."""
        # Create identity directly in ORM
        identity_orm = IdentityORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            kind=IdentityKindEnum.DEVICE,
            external_key="dev_no_session",
        )
        db_session.add(identity_orm)
        await db_session.commit()

        service = IdentityService(db_session)

        with patch("leadr.auth.services.identity_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_no_session",
                "game_id": str(game_orm.id),
                "account_id": str(account_orm.id),
                "identity_id": str(identity_orm.id),
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "nonexistent_hash"

                result = await service.validate_identity_token("token_no_session")

        assert result is None


@pytest.mark.asyncio
class TestIdentityServiceRefreshToken:
    """Test suite for refresh_access_token method."""

    async def test_refresh_token_success(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test successfully refreshing an access token."""
        # Create identity and session
        identity_orm = IdentityORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            kind=IdentityKindEnum.DEVICE,
            external_key="dev_refresh_success",
        )
        db_session.add(identity_orm)
        await db_session.commit()

        now = datetime.now(UTC)
        session_orm = IdentitySessionORM(
            id=uuid4(),
            identity_id=identity_orm.id,
            access_token_hash="old_access_hash",
            refresh_token_hash="old_refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )
        db_session.add(session_orm)
        await db_session.commit()

        service = IdentityService(db_session)

        with patch("leadr.auth.services.identity_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_refresh_success",
                "game_id": str(game_orm.id),
                "account_id": str(account_orm.id),
                "identity_id": str(identity_orm.id),
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
        await db_session.refresh(session_orm)
        assert session_orm.access_token_hash == "new_access_hash"
        assert session_orm.refresh_token_hash == "new_refresh_hash"
        assert session_orm.token_version == 2

    async def test_refresh_token_rejects_invalid_jwt(self, db_session: AsyncSession):
        """Test that invalid refresh JWT is rejected."""
        service = IdentityService(db_session)

        with patch("leadr.auth.services.identity_service.validate_refresh_token") as mock_val:
            mock_val.return_value = None

            result = await service.refresh_access_token("invalid_token")

        assert result is None

    async def test_refresh_token_rejects_when_session_not_found(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test that refresh is rejected when session not found."""
        service = IdentityService(db_session)

        with patch("leadr.auth.services.identity_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": "some_key",
                "game_id": str(game_orm.id),
                "account_id": str(account_orm.id),
                "token_version": 1,
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "nonexistent_hash"

                result = await service.refresh_access_token("orphan_token")

        assert result is None

    async def test_refresh_token_rejects_mismatched_version(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test that refresh token with mismatched version is rejected."""
        # Create identity and session with version 2
        identity_orm = IdentityORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            kind=IdentityKindEnum.DEVICE,
            external_key="dev_version_mismatch",
        )
        db_session.add(identity_orm)
        await db_session.commit()

        now = datetime.now(UTC)
        session_orm = IdentitySessionORM(
            id=uuid4(),
            identity_id=identity_orm.id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=2,  # Version 2 in DB
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )
        db_session.add(session_orm)
        await db_session.commit()

        service = IdentityService(db_session)

        with patch("leadr.auth.services.identity_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_version_mismatch",
                "game_id": str(game_orm.id),
                "account_id": str(account_orm.id),
                "token_version": 1,  # Old version in token
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "refresh_hash"

                result = await service.refresh_access_token("old_version_token")

        assert result is None

    async def test_refresh_token_rejects_expired_refresh(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test that expired refresh token is rejected."""
        # Create identity and session with expired refresh
        identity_orm = IdentityORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            kind=IdentityKindEnum.DEVICE,
            external_key="dev_expired_refresh",
        )
        db_session.add(identity_orm)
        await db_session.commit()

        now = datetime.now(UTC)
        session_orm = IdentitySessionORM(
            id=uuid4(),
            identity_id=identity_orm.id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now - timedelta(days=1),  # Expired
        )
        db_session.add(session_orm)
        await db_session.commit()

        service = IdentityService(db_session)

        with patch("leadr.auth.services.identity_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_expired_refresh",
                "game_id": str(game_orm.id),
                "account_id": str(account_orm.id),
                "token_version": 1,
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "refresh_hash"

                result = await service.refresh_access_token("expired_refresh_token")

        assert result is None

    async def test_refresh_token_rejects_revoked_session(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test that refresh token with revoked session is rejected."""
        # Create identity and revoked session
        identity_orm = IdentityORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            kind=IdentityKindEnum.DEVICE,
            external_key="dev_revoked_refresh",
        )
        db_session.add(identity_orm)
        await db_session.commit()

        now = datetime.now(UTC)
        session_orm = IdentitySessionORM(
            id=uuid4(),
            identity_id=identity_orm.id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
            revoked_at=now - timedelta(minutes=5),  # Revoked
        )
        db_session.add(session_orm)
        await db_session.commit()

        service = IdentityService(db_session)

        with patch("leadr.auth.services.identity_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_revoked_refresh",
                "game_id": str(game_orm.id),
                "account_id": str(account_orm.id),
                "token_version": 1,
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "refresh_hash"

                result = await service.refresh_access_token("revoked_token")

        assert result is None

    async def test_refresh_token_rejects_when_identity_deleted(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test that refresh is rejected when identity is soft-deleted."""
        now = datetime.now(UTC)

        # Create identity first, then soft-delete it
        identity_orm = IdentityORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            kind=IdentityKindEnum.DEVICE,
            external_key="dev_deleted_identity_test",
            deleted_at=now,  # Soft-deleted
        )
        db_session.add(identity_orm)
        await db_session.flush()

        # Create session for the deleted identity
        session_orm = IdentitySessionORM(
            id=uuid4(),
            identity_id=identity_orm.id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )
        db_session.add(session_orm)
        await db_session.commit()

        service = IdentityService(db_session)

        with patch("leadr.auth.services.identity_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": "dev_deleted_identity_test",
                "game_id": str(game_orm.id),
                "account_id": str(account_orm.id),
                "token_version": 1,
            }
            with patch("leadr.auth.services.identity_service.hash_token") as mock_hash:
                mock_hash.return_value = "refresh_hash"

                result = await service.refresh_access_token("deleted_identity_token")

        assert result is None


@pytest.mark.asyncio
class TestIdentityServiceSessionManagement:
    """Test suite for session management methods."""

    async def test_get_session_returns_session(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test getting a session by ID."""
        # Create identity and session
        identity_orm = IdentityORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            kind=IdentityKindEnum.DEVICE,
            external_key="dev_get_session",
        )
        db_session.add(identity_orm)
        await db_session.commit()

        now = datetime.now(UTC)
        session_id = uuid4()
        session_orm = IdentitySessionORM(
            id=session_id,
            identity_id=identity_orm.id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )
        db_session.add(session_orm)
        await db_session.commit()

        service = IdentityService(db_session)
        result = await service.get_session(IdentitySessionID(session_id))

        assert result is not None
        assert result.id.uuid == session_id

    async def test_get_session_returns_none_for_nonexistent(self, db_session: AsyncSession):
        """Test getting a non-existent session returns None."""
        service = IdentityService(db_session)
        result = await service.get_session(IdentitySessionID(uuid4()))

        assert result is None

    async def test_get_session_or_raise_returns_session(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test getting a session by ID or raising."""
        # Create identity and session
        identity_orm = IdentityORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            kind=IdentityKindEnum.DEVICE,
            external_key="dev_get_session_or_raise",
        )
        db_session.add(identity_orm)
        await db_session.commit()

        now = datetime.now(UTC)
        session_id = uuid4()
        session_orm = IdentitySessionORM(
            id=session_id,
            identity_id=identity_orm.id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )
        db_session.add(session_orm)
        await db_session.commit()

        service = IdentityService(db_session)
        result = await service.get_session_or_raise(IdentitySessionID(session_id))

        assert result is not None
        assert result.id.uuid == session_id

    async def test_get_session_or_raise_raises_for_nonexistent(self, db_session: AsyncSession):
        """Test getting a non-existent session raises EntityNotFoundError."""
        service = IdentityService(db_session)

        with pytest.raises(EntityNotFoundError):
            await service.get_session_or_raise(IdentitySessionID(uuid4()))

    async def test_revoke_session_sets_revoked_at(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test revoking a session sets revoked_at."""
        # Create identity and session
        identity_orm = IdentityORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            kind=IdentityKindEnum.DEVICE,
            external_key="dev_revoke_session",
        )
        db_session.add(identity_orm)
        await db_session.commit()

        now = datetime.now(UTC)
        session_id = uuid4()
        session_orm = IdentitySessionORM(
            id=session_id,
            identity_id=identity_orm.id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )
        db_session.add(session_orm)
        await db_session.commit()

        service = IdentityService(db_session)
        result = await service.revoke_session(IdentitySessionID(session_id))

        assert result.revoked_at is not None
        assert result.is_revoked() is True

    async def test_revoke_session_raises_for_nonexistent(self, db_session: AsyncSession):
        """Test revoking a non-existent session raises EntityNotFoundError."""
        service = IdentityService(db_session)

        with pytest.raises(EntityNotFoundError):
            await service.revoke_session(IdentitySessionID(uuid4()))


@pytest.mark.asyncio
class TestIdentityServiceListMethods:
    """Test suite for list methods."""

    async def test_list_identities_returns_all_for_account(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test listing identities for an account."""
        service = IdentityService(db_session)

        # Create multiple identities
        await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.DEVICE,
            external_key="dev_list_1",
        )
        await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.STEAM,
            external_key="steam_list_1",
        )

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.list_identities(
            account_id=AccountID(account_orm.id),
            pagination=pagination,
        )

        assert len(result.items) == 2

    async def test_list_identities_filters_by_kind(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test filtering identities by kind."""
        service = IdentityService(db_session)

        # Create identities with different kinds
        await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.DEVICE,
            external_key="dev_filter_kind_1",
        )
        await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.STEAM,
            external_key="steam_filter_kind_1",
        )

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.list_identities(
            account_id=AccountID(account_orm.id),
            kind=IdentityKind.DEVICE,
            pagination=pagination,
        )

        assert len(result.items) == 1
        assert result.items[0].kind == IdentityKind.DEVICE

    async def test_list_sessions_returns_all_for_identity(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test listing sessions for an identity."""
        service = IdentityService(db_session)

        identity, _ = await service.get_or_create_identity(
            account_id=AccountID(account_orm.id),
            game_id=GameID(game_orm.id),
            kind=IdentityKind.DEVICE,
            external_key="dev_list_sessions",
        )

        # Create multiple sessions
        with patch("leadr.auth.services.identity_service.generate_access_token") as mock_access:
            mock_access.return_value = ("token1", "hash1")
            with patch(
                "leadr.auth.services.identity_service.generate_refresh_token"
            ) as mock_refresh:
                mock_refresh.return_value = ("refresh1", "refresh_hash1")
                await service.start_session(identity=identity)

        with patch("leadr.auth.services.identity_service.generate_access_token") as mock_access:
            mock_access.return_value = ("token2", "hash2")
            with patch(
                "leadr.auth.services.identity_service.generate_refresh_token"
            ) as mock_refresh:
                mock_refresh.return_value = ("refresh2", "refresh_hash2")
                await service.start_session(identity=identity)

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.list_sessions(
            account_id=AccountID(account_orm.id),
            identity_id=identity.id,
            pagination=pagination,
        )

        assert len(result.items) == 2
