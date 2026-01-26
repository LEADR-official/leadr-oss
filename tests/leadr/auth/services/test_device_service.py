"""Tests for DeviceService."""

import hashlib
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.adapters.orm import AccountORM
from leadr.auth.adapters.orm import DeviceORM, DeviceStatusEnum
from leadr.auth.domain.device import DeviceStatus
from leadr.auth.services.device_service import DeviceService
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, DeviceID, GameID
from leadr.games.adapters.orm import GameORM


@pytest.mark.asyncio
class TestDeviceService:
    """Test suite for DeviceService."""

    async def test_get_or_create_device_creates_new_device(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test get_or_create_device creates a new device if it doesn't exist."""
        service = DeviceService(db_session)
        fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()

        device = await service.get_or_create_device(
            game_id=GameID(game_orm.id),
            client_fingerprint=fingerprint,
            platform="ios",
            metadata={"app_version": "1.0.0"},
        )

        assert device is not None
        assert device.client_fingerprint == fingerprint
        assert device.game_id == game_orm.id
        assert device.account_id == account_orm.id
        assert device.platform == "ios"
        assert device.status == DeviceStatus.ACTIVE
        assert device.metadata == {"app_version": "1.0.0"}

    async def test_get_or_create_device_returns_existing_device(
        self, db_session: AsyncSession, game_orm: GameORM
    ):
        """Test get_or_create_device returns existing device and updates last_seen_at."""
        service = DeviceService(db_session)
        fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()

        # Create first device
        device1 = await service.get_or_create_device(
            game_id=GameID(game_orm.id),
            client_fingerprint=fingerprint,
            platform="ios",
        )
        first_seen = device1.last_seen_at

        # Get same device again
        device2 = await service.get_or_create_device(
            game_id=GameID(game_orm.id),
            client_fingerprint=fingerprint,
            platform="ios",
        )

        assert device2.id == device1.id
        assert device2.last_seen_at >= first_seen

    async def test_get_or_create_device_raises_for_nonexistent_game(
        self, db_session: AsyncSession
    ):
        """Test that get_or_create_device for nonexistent game raises error."""
        service = DeviceService(db_session)

        with pytest.raises(EntityNotFoundError):
            await service.get_or_create_device(
                game_id=GameID(uuid4()),
                client_fingerprint=hashlib.sha256(str(uuid4()).encode()).hexdigest(),
                platform="ios",
            )

    async def test_list_devices_by_account(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test listing devices filtered by account."""
        service = DeviceService(db_session)

        # Create a couple of devices
        for i in range(3):
            fingerprint = hashlib.sha256(f"device_{i}".encode()).hexdigest()
            await service.get_or_create_device(
                game_id=GameID(game_orm.id),
                client_fingerprint=fingerprint,
                platform="android",
            )

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.list_devices(
            account_id=AccountID(account_orm.id),
            pagination=pagination,
        )

        assert len(result.items) == 3

    async def test_get_device_by_id(
        self, db_session: AsyncSession, device_orm: DeviceORM
    ):
        """Test getting a device by ID."""
        service = DeviceService(db_session)
        device = await service.get_device(device_orm.id)

        assert device is not None
        assert device.id == device_orm.id

    async def test_get_device_not_found(self, db_session: AsyncSession):
        """Test getting a non-existent device returns None."""
        service = DeviceService(db_session)
        device = await service.get_device(uuid4())

        assert device is None

    async def test_ban_device(
        self, db_session: AsyncSession, device_orm: DeviceORM
    ):
        """Test banning a device."""
        service = DeviceService(db_session)

        device = await service.ban_device(DeviceID(device_orm.id))

        assert device.status == DeviceStatus.BANNED

    async def test_suspend_device(
        self, db_session: AsyncSession, device_orm: DeviceORM
    ):
        """Test suspending a device."""
        service = DeviceService(db_session)

        device = await service.suspend_device(DeviceID(device_orm.id))

        assert device.status == DeviceStatus.SUSPENDED

    async def test_activate_device(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test activating a banned device."""
        service = DeviceService(db_session)

        # Create a banned device
        fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        device = await service.get_or_create_device(
            game_id=GameID(game_orm.id),
            client_fingerprint=fingerprint,
        )
        await service.ban_device(DeviceID(device.id))

        # Activate it
        device = await service.activate_device(DeviceID(device.id))

        assert device.status == DeviceStatus.ACTIVE

    async def test_ban_device_not_found(self, db_session: AsyncSession):
        """Test banning a non-existent device raises error."""
        service = DeviceService(db_session)

        with pytest.raises(EntityNotFoundError):
            await service.ban_device(DeviceID(uuid4()))
