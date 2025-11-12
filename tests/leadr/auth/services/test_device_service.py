"""Tests for DeviceService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.adapters.orm import AccountORM
from leadr.auth.domain.device import DeviceStatus
from leadr.auth.services.device_service import DeviceService
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.games.adapters.orm import GameORM


@pytest.mark.asyncio
class TestDeviceService:
    """Test suite for DeviceService."""

    async def test_start_session_creates_new_device(self, db_session: AsyncSession):
        """Test starting a session creates a new device if it doesn't exist."""
        # Create account and game
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Start session for new device
        service = DeviceService(db_session)
        device_id = str(uuid4())

        with patch("leadr.auth.services.device_service.generate_access_token") as mock_gen_access:
            mock_gen_access.return_value = ("mock_token", "mock_hash")
            with patch(
                "leadr.auth.services.device_service.generate_refresh_token"
            ) as mock_gen_refresh:
                mock_gen_refresh.return_value = ("mock_refresh_token", "mock_refresh_hash")

                device, access_token, refresh_token, expires_in = await service.start_session(
                    game_id=game.id,
                    device_id=device_id,
                    platform="ios",
                    ip_address="192.168.1.1",
                    user_agent="TestApp/1.0",
                )

        assert device is not None
        assert device.device_id == device_id
        assert device.game_id == game.id
        assert device.account_id == account.id
        assert device.platform == "ios"
        assert device.status == DeviceStatus.ACTIVE
        assert access_token == "mock_token"
        assert refresh_token == "mock_refresh_token"
        assert expires_in > 0

    async def test_start_session_updates_existing_device(self, db_session: AsyncSession):
        """Test starting a session updates last_seen_at for existing device."""
        # Create account and game
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create initial device and session
        service = DeviceService(db_session)
        device_id = str(uuid4())

        with patch("leadr.auth.services.device_service.generate_access_token") as mock_gen_access:
            mock_gen_access.return_value = ("token1", "hash1")
            with patch(
                "leadr.auth.services.device_service.generate_refresh_token"
            ) as mock_gen_refresh:
                mock_gen_refresh.return_value = ("refresh1", "refresh_hash1")
                device1, _, _, _ = await service.start_session(
                    game_id=game.id,
                    device_id=device_id,
                    platform="ios",
                )
                first_seen = device1.last_seen_at

        # Start another session for same device
        with patch("leadr.auth.services.device_service.generate_access_token") as mock_gen_access:
            mock_gen_access.return_value = ("token2", "hash2")
            with patch(
                "leadr.auth.services.device_service.generate_refresh_token"
            ) as mock_gen_refresh:
                mock_gen_refresh.return_value = ("refresh2", "refresh_hash2")
                device2, _, _, _ = await service.start_session(
                    game_id=game.id,
                    device_id=device_id,
                    platform="ios",
                )

        assert device2.id == device1.id
        assert device2.last_seen_at > first_seen

    async def test_start_session_creates_device_session(self, db_session: AsyncSession):
        """Test that starting a session creates a DeviceSession record."""
        # Create account and game
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        service = DeviceService(db_session)
        device_id = str(uuid4())

        with patch("leadr.auth.services.device_service.generate_access_token") as mock_gen_access:
            mock_gen_access.return_value = ("test_token", "test_hash")
            with patch(
                "leadr.auth.services.device_service.generate_refresh_token"
            ) as mock_gen_refresh:
                mock_gen_refresh.return_value = ("test_refresh", "test_refresh_hash")

                device, access_token, refresh_token, expires_in = await service.start_session(
                    game_id=game.id,
                    device_id=device_id,
                    platform="android",
                    ip_address="10.0.0.1",
                    user_agent="TestApp/2.0",
                )

        # Verify session was created
        from leadr.auth.services.repositories import DeviceSessionRepository

        session_repo = DeviceSessionRepository(db_session)
        sessions = await session_repo.filter(account_id=account.id)
        assert len(sessions) == 1
        assert sessions[0].device_id == device.id
        assert sessions[0].access_token_hash == "test_hash"
        assert sessions[0].ip_address == "10.0.0.1"
        assert sessions[0].user_agent == "TestApp/2.0"

    async def test_start_session_raises_for_nonexistent_game(self, db_session: AsyncSession):
        """Test that starting a session for nonexistent game raises error."""
        service = DeviceService(db_session)

        with pytest.raises(EntityNotFoundError):
            await service.start_session(
                game_id=uuid4(),
                device_id=str(uuid4()),
                platform="ios",
            )

    async def test_start_session_uses_correct_token_expiration(self, db_session: AsyncSession):
        """Test that session token has correct expiration time."""
        # Create account and game
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        service = DeviceService(db_session)

        with patch("leadr.auth.services.device_service.generate_access_token") as mock_gen_access:
            mock_gen_access.return_value = ("token", "hash")
            with patch(
                "leadr.auth.services.device_service.generate_refresh_token"
            ) as mock_gen_refresh:
                mock_gen_refresh.return_value = ("refresh", "refresh_hash")

                _, _, _, expires_in = await service.start_session(
                    game_id=game.id,
                    device_id=str(uuid4()),
                    platform="ios",
                )

                # Verify generate_access_token was called with correct expiration
                assert mock_gen_access.called
                call_args = mock_gen_access.call_args[1]
                assert "expires_delta" in call_args
                # Default should be 24 hours
                assert call_args["expires_delta"] == timedelta(hours=24)

    async def test_validate_device_token_returns_device_for_valid_token(
        self, db_session: AsyncSession
    ):
        """Test that valid token returns associated device."""
        # Create account and game
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create device and session
        service = DeviceService(db_session)
        device_id = str(uuid4())

        with patch("leadr.auth.services.device_service.generate_access_token") as mock_gen_access:
            mock_gen_access.return_value = ("test_token", "test_hash")
            with patch(
                "leadr.auth.services.device_service.generate_refresh_token"
            ) as mock_gen_refresh:
                mock_gen_refresh.return_value = ("test_refresh", "test_refresh_hash")
                created_device, access_token, refresh_token, _ = await service.start_session(
                    game_id=game.id,
                    device_id=device_id,
                    platform="ios",
                )

        # Validate token
        with patch("leadr.auth.services.device_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": device_id,
                "game_id": str(game.id),
                "account_id": str(account.id),
            }
            with patch("leadr.auth.services.device_service.hash_token") as mock_hash:
                mock_hash.return_value = "test_hash"

                device = await service.validate_device_token("test_token")

        assert device is not None
        assert device.id == created_device.id
        assert device.device_id == device_id

    async def test_validate_device_token_returns_none_for_invalid_token(
        self, db_session: AsyncSession
    ):
        """Test that invalid token returns None."""
        service = DeviceService(db_session)

        with patch("leadr.auth.services.device_service.validate_access_token") as mock_val:
            mock_val.return_value = None

            device = await service.validate_device_token("invalid_token")

        assert device is None

    async def test_validate_device_token_returns_none_for_expired_session(
        self, db_session: AsyncSession
    ):
        """Test that token with expired session returns None."""
        # Create account and game
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create device and expired session
        from leadr.auth.adapters.orm import DeviceORM, DeviceSessionORM

        device_orm = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id=str(uuid4()),
            account_id=account.id,
            platform="ios",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device_orm)
        await db_session.commit()

        # Create expired session
        expired_session = DeviceSessionORM(
            id=uuid4(),
            device_id=device_orm.id,
            access_token_hash="hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired
            refresh_expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        db_session.add(expired_session)
        await db_session.commit()

        service = DeviceService(db_session)

        with patch("leadr.auth.services.device_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": device_orm.device_id,
                "game_id": str(game.id),
                "account_id": str(account.id),
            }
            with patch("leadr.auth.services.device_service.hash_token") as mock_hash:
                mock_hash.return_value = "hash"

                device = await service.validate_device_token("token")

        assert device is None

    async def test_validate_device_token_returns_none_for_revoked_session(
        self, db_session: AsyncSession
    ):
        """Test that token with revoked session returns None."""
        # Create account and game
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create device and revoked session
        from leadr.auth.adapters.orm import DeviceORM, DeviceSessionORM

        device_orm = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id=str(uuid4()),
            account_id=account.id,
            platform="android",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device_orm)
        await db_session.commit()

        # Create revoked session
        revoked_session = DeviceSessionORM(
            id=uuid4(),
            device_id=device_orm.id,
            access_token_hash="hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_expires_at=datetime.now(UTC) + timedelta(days=30),
            revoked_at=datetime.now(UTC),  # Revoked
        )
        db_session.add(revoked_session)
        await db_session.commit()

        service = DeviceService(db_session)

        with patch("leadr.auth.services.device_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": device_orm.device_id,
                "game_id": str(game.id),
                "account_id": str(account.id),
            }
            with patch("leadr.auth.services.device_service.hash_token") as mock_hash:
                mock_hash.return_value = "hash"

                device = await service.validate_device_token("token")

        assert device is None

    async def test_validate_device_token_returns_none_for_banned_device(
        self, db_session: AsyncSession
    ):
        """Test that token for banned device returns None."""
        # Create account and game
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create banned device
        from leadr.auth.adapters.orm import DeviceORM, DeviceSessionORM, DeviceStatusEnum

        device_orm = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id=str(uuid4()),
            account_id=account.id,
            platform="ios",
            status=DeviceStatusEnum.BANNED,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device_orm)
        await db_session.commit()

        # Create valid session
        valid_session = DeviceSessionORM(
            id=uuid4(),
            device_id=device_orm.id,
            access_token_hash="hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        db_session.add(valid_session)
        await db_session.commit()

        service = DeviceService(db_session)

        with patch("leadr.auth.services.device_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": device_orm.device_id,
                "game_id": str(game.id),
                "account_id": str(account.id),
            }
            with patch("leadr.auth.services.device_service.hash_token") as mock_hash:
                mock_hash.return_value = "hash"

                device = await service.validate_device_token("token")

        assert device is None

    async def test_refresh_access_token_success(self, db_session: AsyncSession):
        """Test successfully refreshing an access token with valid refresh token."""
        # Create account and game
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create device
        from leadr.auth.adapters.orm import DeviceORM, DeviceSessionORM

        device_orm = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id=str(uuid4()),
            account_id=account.id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device_orm)
        await db_session.commit()

        # Create session with refresh token
        now = datetime.now(UTC)
        session = DeviceSessionORM(
            id=uuid4(),
            device_id=device_orm.id,
            access_token_hash="old_access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )
        db_session.add(session)
        await db_session.commit()

        service = DeviceService(db_session)

        # Mock crypto functions
        with patch("leadr.auth.services.device_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": device_orm.device_id,
                "game_id": str(game.id),
                "account_id": str(account.id),
                "token_version": 1,
            }
            with patch("leadr.auth.services.device_service.hash_token") as mock_hash:
                mock_hash.return_value = "refresh_hash"
                with patch(
                    "leadr.auth.services.device_service.generate_access_token"
                ) as mock_gen_access:
                    mock_gen_access.return_value = ("new_access_token", "new_access_hash")
                    with patch(
                        "leadr.auth.services.device_service.generate_refresh_token"
                    ) as mock_gen_refresh:
                        mock_gen_refresh.return_value = ("new_refresh_token", "new_refresh_hash")

                        result = await service.refresh_access_token("old_refresh_token")
                        assert result is not None
                        access_token, refresh_token, expires_in = result

        # Verify tokens returned
        assert access_token == "new_access_token"
        assert refresh_token == "new_refresh_token"
        assert expires_in > 0

        # Verify session was updated with new hashes and incremented version
        await db_session.refresh(session)
        assert session.access_token_hash == "new_access_hash"
        assert session.refresh_token_hash == "new_refresh_hash"
        assert session.token_version == 2

    async def test_refresh_access_token_rejects_invalid_jwt(self, db_session: AsyncSession):
        """Test that invalid refresh JWT is rejected."""
        service = DeviceService(db_session)

        with patch("leadr.auth.services.device_service.validate_refresh_token") as mock_val:
            mock_val.return_value = None  # Invalid JWT

            result = await service.refresh_access_token("invalid_token")

        assert result is None

    async def test_refresh_access_token_rejects_mismatched_version(self, db_session: AsyncSession):
        """Test that refresh token with mismatched version is rejected (replay attack)."""
        # Create account and game
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create device
        from leadr.auth.adapters.orm import DeviceORM, DeviceSessionORM

        device_orm = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id=str(uuid4()),
            account_id=account.id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device_orm)
        await db_session.commit()

        # Create session with token_version=2
        now = datetime.now(UTC)
        session = DeviceSessionORM(
            id=uuid4(),
            device_id=device_orm.id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=2,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )
        db_session.add(session)
        await db_session.commit()

        service = DeviceService(db_session)

        # JWT claims have token_version=1 (old token)
        with patch("leadr.auth.services.device_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": device_orm.device_id,
                "game_id": str(game.id),
                "account_id": str(account.id),
                "token_version": 1,  # Mismatched version
            }
            with patch("leadr.auth.services.device_service.hash_token") as mock_hash:
                mock_hash.return_value = "refresh_hash"

                result = await service.refresh_access_token("old_refresh_token")

        assert result is None

    async def test_refresh_access_token_rejects_expired_refresh_token(
        self, db_session: AsyncSession
    ):
        """Test that expired refresh token is rejected."""
        # Create account and game
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create device
        from leadr.auth.adapters.orm import DeviceORM, DeviceSessionORM

        device_orm = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id=str(uuid4()),
            account_id=account.id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device_orm)
        await db_session.commit()

        # Create session with expired refresh token
        now = datetime.now(UTC)
        session = DeviceSessionORM(
            id=uuid4(),
            device_id=device_orm.id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now - timedelta(days=1),  # Expired
        )
        db_session.add(session)
        await db_session.commit()

        service = DeviceService(db_session)

        with patch("leadr.auth.services.device_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": device_orm.device_id,
                "game_id": str(game.id),
                "account_id": str(account.id),
                "token_version": 1,
            }
            with patch("leadr.auth.services.device_service.hash_token") as mock_hash:
                mock_hash.return_value = "refresh_hash"

                result = await service.refresh_access_token("expired_refresh_token")

        assert result is None

    async def test_refresh_access_token_rejects_revoked_session(self, db_session: AsyncSession):
        """Test that refresh token with revoked session is rejected."""
        # Create account and game
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create device
        from leadr.auth.adapters.orm import DeviceORM, DeviceSessionORM

        device_orm = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id=str(uuid4()),
            account_id=account.id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device_orm)
        await db_session.commit()

        # Create revoked session
        now = datetime.now(UTC)
        session = DeviceSessionORM(
            id=uuid4(),
            device_id=device_orm.id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
            revoked_at=now - timedelta(minutes=5),  # Revoked
        )
        db_session.add(session)
        await db_session.commit()

        service = DeviceService(db_session)

        with patch("leadr.auth.services.device_service.validate_refresh_token") as mock_val:
            mock_val.return_value = {
                "sub": device_orm.device_id,
                "game_id": str(game.id),
                "account_id": str(account.id),
                "token_version": 1,
            }
            with patch("leadr.auth.services.device_service.hash_token") as mock_hash:
                mock_hash.return_value = "refresh_hash"

                result = await service.refresh_access_token("revoked_token")

        assert result is None
