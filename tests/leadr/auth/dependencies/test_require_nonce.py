"""Tests for require_nonce dependency."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.adapters.orm import AccountORM
from leadr.auth.adapters.orm import DeviceORM, NonceORM
from leadr.auth.dependencies import require_nonce
from leadr.auth.domain.device import Device
from leadr.auth.services.dependencies import get_nonce_service
from leadr.games.adapters.orm import GameORM


@pytest.mark.asyncio
class TestRequireNonce:
    """Test suite for require_nonce dependency."""

    async def test_valid_nonce_succeeds(self, db_session: AsyncSession):
        """Test that valid nonce is accepted and consumed."""
        # Create account, game, and device
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

        device_orm = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device_orm)
        await db_session.commit()

        # Create valid nonce
        nonce_value = str(uuid4())
        nonce_orm = NonceORM(
            id=uuid4(),
            device_id=device_orm.id,
            nonce_value=nonce_value,
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status="pending",
        )
        db_session.add(nonce_orm)
        await db_session.commit()

        # Create device entity
        device = Device(
            id=device_orm.id,
            game_id=device_orm.game_id,
            device_id=device_orm.device_id,
            account_id=device_orm.account_id,
            first_seen_at=device_orm.first_seen_at,
            last_seen_at=device_orm.last_seen_at,
        )

        # Validate nonce
        service = await get_nonce_service(db_session)
        result = await require_nonce(
            device=device,
            service=service,
            leadr_client_nonce=nonce_value,
        )

        assert result is True

        # Verify nonce was marked as used
        await db_session.refresh(nonce_orm)
        assert nonce_orm.status == "used"
        assert nonce_orm.used_at is not None

    async def test_missing_nonce_header_raises_412(self, db_session: AsyncSession):
        """Test that missing nonce header raises 412 Precondition Failed."""
        # Create minimal device
        device = Device(
            id=uuid4(),
            game_id=uuid4(),
            device_id="test-device",
            account_id=uuid4(),
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )

        service = await get_nonce_service(db_session)

        with pytest.raises(HTTPException) as exc_info:
            await require_nonce(device=device, service=service, leadr_client_nonce=None)

        assert exc_info.value.status_code == 412
        assert "nonce required" in exc_info.value.detail.lower()

    async def test_invalid_nonce_raises_412(self, db_session: AsyncSession):
        """Test that invalid/unknown nonce raises 412."""
        # Create account, game, and device
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

        device_orm = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device_orm)
        await db_session.commit()

        device = Device(
            id=device_orm.id,
            game_id=device_orm.game_id,
            device_id=device_orm.device_id,
            account_id=device_orm.account_id,
            first_seen_at=device_orm.first_seen_at,
            last_seen_at=device_orm.last_seen_at,
        )

        service = await get_nonce_service(db_session)

        with pytest.raises(HTTPException) as exc_info:
            await require_nonce(device=device, service=service, leadr_client_nonce="invalid-nonce")

        assert exc_info.value.status_code == 412
        assert "invalid" in exc_info.value.detail.lower()

    async def test_expired_nonce_raises_412(self, db_session: AsyncSession):
        """Test that expired nonce raises 412."""
        # Create account, game, and device
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

        device_orm = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device_orm)
        await db_session.commit()

        # Create expired nonce
        nonce_value = str(uuid4())
        nonce_orm = NonceORM(
            id=uuid4(),
            device_id=device_orm.id,
            nonce_value=nonce_value,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),  # Expired
            status="pending",
        )
        db_session.add(nonce_orm)
        await db_session.commit()

        device = Device(
            id=device_orm.id,
            game_id=device_orm.game_id,
            device_id=device_orm.device_id,
            account_id=device_orm.account_id,
            first_seen_at=device_orm.first_seen_at,
            last_seen_at=device_orm.last_seen_at,
        )

        service = await get_nonce_service(db_session)

        with pytest.raises(HTTPException) as exc_info:
            await require_nonce(device=device, service=service, leadr_client_nonce=nonce_value)

        assert exc_info.value.status_code == 412
        assert "expired" in exc_info.value.detail.lower()

    async def test_already_used_nonce_raises_412(self, db_session: AsyncSession):
        """Test that already-used nonce raises 412."""
        # Create account, game, and device
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

        device_orm = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device_orm)
        await db_session.commit()

        # Create used nonce
        nonce_value = str(uuid4())
        nonce_orm = NonceORM(
            id=uuid4(),
            device_id=device_orm.id,
            nonce_value=nonce_value,
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status="used",
            used_at=datetime.now(UTC),
        )
        db_session.add(nonce_orm)
        await db_session.commit()

        device = Device(
            id=device_orm.id,
            game_id=device_orm.game_id,
            device_id=device_orm.device_id,
            account_id=device_orm.account_id,
            first_seen_at=device_orm.first_seen_at,
            last_seen_at=device_orm.last_seen_at,
        )

        service = await get_nonce_service(db_session)

        with pytest.raises(HTTPException) as exc_info:
            await require_nonce(device=device, service=service, leadr_client_nonce=nonce_value)

        assert exc_info.value.status_code == 412
        assert "already used" in exc_info.value.detail.lower()

    async def test_nonce_from_different_device_raises_412(self, db_session: AsyncSession):
        """Test that nonce from different device raises 412."""
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

        # Create two devices
        device1_orm = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="device-1",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device1_orm)

        device2_orm = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="device-2",
            account_id=game.account_id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device2_orm)
        await db_session.commit()

        # Create nonce for device1
        nonce_value = str(uuid4())
        nonce_orm = NonceORM(
            id=uuid4(),
            device_id=device1_orm.id,
            nonce_value=nonce_value,
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status="pending",
        )
        db_session.add(nonce_orm)
        await db_session.commit()

        # Try to use nonce with device2
        device2 = Device(
            id=device2_orm.id,
            game_id=device2_orm.game_id,
            device_id=device2_orm.device_id,
            account_id=device2_orm.account_id,
            first_seen_at=device2_orm.first_seen_at,
            last_seen_at=device2_orm.last_seen_at,
        )

        service = await get_nonce_service(db_session)

        with pytest.raises(HTTPException) as exc_info:
            await require_nonce(device=device2, service=service, leadr_client_nonce=nonce_value)

        assert exc_info.value.status_code == 412
        assert "does not belong" in exc_info.value.detail.lower()
