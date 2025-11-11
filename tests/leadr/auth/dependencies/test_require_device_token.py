"""Tests for require_device_token dependency."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.adapters.orm import AccountORM
from leadr.auth.adapters.orm import DeviceORM, DeviceSessionORM, DeviceStatusEnum
from leadr.auth.dependencies import require_device_token
from leadr.auth.services.dependencies import get_device_service
from leadr.games.adapters.orm import GameORM


@pytest.mark.asyncio
class TestRequireDeviceToken:
    """Test suite for require_device_token dependency."""

    async def test_missing_authorization_header_raises_401(self, db_session: AsyncSession):
        """Test that missing Authorization header raises 401 Unauthorized."""
        service = await get_device_service(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await require_device_token(service=service, authorization=None)

        assert exc_info.value.status_code == 401
        assert "required" in exc_info.value.detail.lower()

    async def test_invalid_bearer_format_raises_401(self, db_session: AsyncSession):
        """Test that invalid Bearer format raises 401 Unauthorized."""
        service = await get_device_service(db_session)
        with pytest.raises(HTTPException) as exc_info:
            await require_device_token(service=service, authorization="NotBearer token123")

        assert exc_info.value.status_code == 401
        assert (
            "format" in exc_info.value.detail.lower() or "invalid" in exc_info.value.detail.lower()
        )

    async def test_invalid_token_raises_401(self, db_session: AsyncSession):
        """Test that an invalid/unknown token raises 401 Unauthorized."""
        # Create account, game, and device to ensure DB works
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

        service = await get_device_service(db_session)

        # Start a valid session to ensure setup works
        with patch("leadr.auth.services.device_service.generate_access_token") as mock_gen:
            mock_gen.return_value = ("valid_token", "valid_hash")
            await service.start_session(
                game_id=game.id,
                device_id=str(uuid4()),
                platform="ios",
            )

        # Try with a completely invalid token
        with pytest.raises(HTTPException) as exc_info:
            await require_device_token(service=service, authorization="Bearer invalid.jwt.token")

        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()

    async def test_valid_token_returns_device_entity(self, db_session: AsyncSession):
        """Test that a valid device token returns the Device entity."""
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
        service = await get_device_service(db_session)
        device_id = str(uuid4())

        with patch("leadr.auth.services.device_service.generate_access_token") as mock_gen:
            mock_gen.return_value = ("test_token", "test_hash")
            device, plain_token, _ = await service.start_session(
                game_id=game.id,
                device_id=device_id,
                platform="android",
            )

        # Mock token validation for the require_device_token call
        with patch("leadr.auth.services.device_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": device_id,
                "game_id": str(game.id),
                "account_id": str(account.id),
            }
            with patch("leadr.auth.services.device_service.hash_token") as mock_hash:
                mock_hash.return_value = "test_hash"

                # Use the dependency with Bearer token
                result = await require_device_token(
                    service=service, authorization=f"Bearer {plain_token}"
                )

        # Should return the Device entity
        assert result.id == device.id
        assert result.device_id == device_id
        assert result.game_id == game.id
        assert result.account_id == account.id

    async def test_expired_session_raises_401(self, db_session: AsyncSession):
        """Test that a token with expired session raises 401 Unauthorized."""
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

        # Create device with expired session
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
            access_token_hash="test_hash",
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired
        )
        db_session.add(expired_session)
        await db_session.commit()

        # Mock token validation to return valid claims but session is expired
        service = await get_device_service(db_session)

        with patch("leadr.auth.services.device_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": device_orm.device_id,
                "game_id": str(game.id),
                "account_id": str(account.id),
            }
            with patch("leadr.auth.services.device_service.hash_token") as mock_hash:
                mock_hash.return_value = "test_hash"

                # Try to use token with expired session
                with pytest.raises(HTTPException) as exc_info:
                    await require_device_token(service=service, authorization="Bearer test_token")

        assert exc_info.value.status_code == 401
        assert (
            "invalid" in exc_info.value.detail.lower() or "expired" in exc_info.value.detail.lower()
        )

    async def test_revoked_session_raises_401(self, db_session: AsyncSession):
        """Test that a token with revoked session raises 401 Unauthorized."""
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

        # Create device with revoked session
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
            access_token_hash="test_hash",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            revoked_at=datetime.now(UTC),  # Revoked
        )
        db_session.add(revoked_session)
        await db_session.commit()

        service = await get_device_service(db_session)

        with patch("leadr.auth.services.device_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": device_orm.device_id,
                "game_id": str(game.id),
                "account_id": str(account.id),
            }
            with patch("leadr.auth.services.device_service.hash_token") as mock_hash:
                mock_hash.return_value = "test_hash"

                # Try to use token with revoked session
                with pytest.raises(HTTPException) as exc_info:
                    await require_device_token(service=service, authorization="Bearer test_token")

        assert exc_info.value.status_code == 401
        assert (
            "invalid" in exc_info.value.detail.lower() or "revoked" in exc_info.value.detail.lower()
        )

    async def test_banned_device_raises_401(self, db_session: AsyncSession):
        """Test that a token for banned device raises 401 Unauthorized."""
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

        # Create valid session for banned device
        valid_session = DeviceSessionORM(
            id=uuid4(),
            device_id=device_orm.id,
            access_token_hash="test_hash",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        db_session.add(valid_session)
        await db_session.commit()

        service = await get_device_service(db_session)

        with patch("leadr.auth.services.device_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": device_orm.device_id,
                "game_id": str(game.id),
                "account_id": str(account.id),
            }
            with patch("leadr.auth.services.device_service.hash_token") as mock_hash:
                mock_hash.return_value = "test_hash"

                # Try to use token for banned device
                with pytest.raises(HTTPException) as exc_info:
                    await require_device_token(service=service, authorization="Bearer test_token")

        assert exc_info.value.status_code == 401
        assert (
            "invalid" in exc_info.value.detail.lower() or "banned" in exc_info.value.detail.lower()
        )

    async def test_soft_deleted_device_raises_401(self, db_session: AsyncSession):
        """Test that a token for soft-deleted device raises 401 Unauthorized."""
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

        # Create soft-deleted device
        device_orm = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id=str(uuid4()),
            account_id=account.id,
            platform="android",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            deleted_at=datetime.now(UTC),  # Soft deleted
        )
        db_session.add(device_orm)
        await db_session.commit()

        service = await get_device_service(db_session)

        with patch("leadr.auth.services.device_service.validate_access_token") as mock_val:
            mock_val.return_value = {
                "sub": device_orm.device_id,
                "game_id": str(game.id),
                "account_id": str(account.id),
            }

            # Try to use token for deleted device
            with pytest.raises(HTTPException) as exc_info:
                await require_device_token(service=service, authorization="Bearer test_token")

        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()
