"""Tests for Device and DeviceSession repository services."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.adapters.orm import AccountORM
from leadr.auth.adapters.orm import DeviceORM
from leadr.auth.domain.device import Device, DeviceSession, DeviceStatus
from leadr.auth.services.repositories import DeviceRepository
from leadr.common.domain.ids import AccountID, DeviceID, GameID
from leadr.games.adapters.orm import GameORM


@pytest.mark.asyncio
class TestDeviceRepository:
    """Test suite for DeviceRepository."""

    async def test_create_device(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test creating a device via repository."""
        # Create domain entity
        now = datetime.now(UTC)
        device = Device(
            game_id=GameID(game_orm.id),
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            account_id=AccountID(account_orm.id),
            platform="ios",
            first_seen_at=now,
            last_seen_at=now,
        )

        # Create via repository
        repository = DeviceRepository(db_session)
        created_device = await repository.create(device)

        assert created_device.id is not None
        assert created_device.game_id == game_orm.id
        assert (
            created_device.client_fingerprint
            == "cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0"
        )
        assert created_device.account_id == account_orm.id
        assert created_device.platform == "ios"
        assert created_device.status == DeviceStatus.ACTIVE

    async def test_get_device_by_id(self, db_session: AsyncSession, device_orm: DeviceORM):
        """Test retrieving a device by ID."""
        # Retrieve via repository
        repository = DeviceRepository(db_session)
        device = await repository.get_by_id(device_orm.id)

        assert device is not None
        assert device.id == device_orm.id
        assert device.client_fingerprint == device_orm.client_fingerprint
        assert device.platform == device_orm.platform

    async def test_get_device_by_id_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent device returns None."""
        repository = DeviceRepository(db_session)
        device = await repository.get_by_id(uuid4())
        assert device is None

    async def test_get_device_by_game_and_device_id(
        self, db_session: AsyncSession, device_orm: DeviceORM
    ):
        """Test retrieving a device by game_id and device_id."""
        # Retrieve via repository
        repository = DeviceRepository(db_session)
        device = await repository.get_by_game_and_fingerprint(
            GameID(device_orm.game_id), device_orm.client_fingerprint
        )

        assert device is not None
        assert device.game_id == device_orm.game_id
        assert device.client_fingerprint == device_orm.client_fingerprint

    async def test_get_device_by_game_and_device_id_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent device by game and device_id returns None."""
        repository = DeviceRepository(db_session)
        device = await repository.get_by_game_and_fingerprint(GameID(uuid4()), "nonexistent")
        assert device is None

    async def test_update_device(
        self, db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
    ):
        """Test updating a device via repository."""
        # Create device
        now = datetime.now(UTC)
        device = Device(
            game_id=GameID(game_orm.id),
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            account_id=AccountID(account_orm.id),
            first_seen_at=now,
            last_seen_at=now,
        )

        repository = DeviceRepository(db_session)
        created_device = await repository.create(device)

        # Update the device
        created_device.ban()
        updated_device = await repository.update(created_device)

        assert updated_device.status == DeviceStatus.BANNED
        assert updated_device.id == created_device.id

    async def test_filter_devices_by_account(self, db_session: AsyncSession):
        """Test filtering devices by account_id."""
        # Create two accounts
        account1 = AccountORM(
            id=uuid4(),
            name="Account 1",
            slug="account-1",
        )
        account2 = AccountORM(
            id=uuid4(),
            name="Account 2",
            slug="account-2",
        )
        db_session.add(account1)
        db_session.add(account2)
        await db_session.commit()

        # Create games
        game1 = GameORM(
            id=uuid4(),
            account_id=account1.id,
            name="Game 1",
            slug="game-1",
        )
        game2 = GameORM(
            id=uuid4(),
            account_id=account2.id,
            name="Game 2",
            slug="game-2",
        )
        db_session.add(game1)
        db_session.add(game2)
        await db_session.commit()

        # Create devices for both accounts
        now = datetime.now(UTC)
        device1 = DeviceORM(
            id=uuid4(),
            game_id=game1.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            account_id=account1.id,
            first_seen_at=now,
            last_seen_at=now,
        )
        device2 = DeviceORM(
            id=uuid4(),
            game_id=game2.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            account_id=account2.id,
            first_seen_at=now,
            last_seen_at=now,
        )
        db_session.add(device1)
        db_session.add(device2)
        await db_session.commit()

        # Filter by account1
        repository = DeviceRepository(db_session)
        devices = await repository.filter(account_id=AccountID(account1.id))

        assert len(devices) == 1
        assert devices[0].account_id == account1.id
        assert (
            devices[0].client_fingerprint
            == "cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0"
        )


@pytest.mark.asyncio
class TestDeviceSessionRepository:
    """Test suite for DeviceSessionRepository."""

    async def test_get_by_token_hash(self, db_session: AsyncSession, device_orm: DeviceORM):
        """Test retrieving a session by access token hash."""
        # Create session
        now = datetime.now(UTC)
        from leadr.auth.services.repositories import DeviceSessionRepository

        repository = DeviceSessionRepository(db_session)
        session = DeviceSession(
            device_id=DeviceID(device_orm.id),
            access_token_hash="test_access_hash",
            refresh_token_hash="test_refresh_hash",
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )
        created_session = await repository.create(session)

        # Retrieve by access token hash
        retrieved = await repository.get_by_token_hash("test_access_hash")

        assert retrieved is not None
        assert retrieved.id == created_session.id
        assert retrieved.access_token_hash == "test_access_hash"

    async def test_get_by_token_hash_not_found(self, db_session: AsyncSession):
        """Test that get_by_token_hash returns None for non-existent hash."""
        from leadr.auth.services.repositories import DeviceSessionRepository

        repository = DeviceSessionRepository(db_session)
        session = await repository.get_by_token_hash("nonexistent_hash")

        assert session is None

    async def test_get_by_refresh_token_hash(self, db_session: AsyncSession, device_orm: DeviceORM):
        """Test retrieving a session by refresh token hash."""
        # Create session with refresh token
        now = datetime.now(UTC)
        from leadr.auth.services.repositories import DeviceSessionRepository

        repository = DeviceSessionRepository(db_session)
        session = DeviceSession(
            device_id=DeviceID(device_orm.id),
            access_token_hash="test_access_hash",
            refresh_token_hash="unique_refresh_hash",
            token_version=1,
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )
        created_session = await repository.create(session)

        # Retrieve by refresh token hash
        retrieved = await repository.get_by_refresh_token_hash("unique_refresh_hash")

        assert retrieved is not None
        assert retrieved.id == created_session.id
        assert retrieved.refresh_token_hash == "unique_refresh_hash"
        assert retrieved.token_version == 1

    async def test_get_by_refresh_token_hash_not_found(self, db_session: AsyncSession):
        """Test that get_by_refresh_token_hash returns None for non-existent hash."""
        from leadr.auth.services.repositories import DeviceSessionRepository

        repository = DeviceSessionRepository(db_session)
        session = await repository.get_by_refresh_token_hash("nonexistent_refresh_hash")

        assert session is None

    async def test_get_by_refresh_token_hash_excludes_soft_deleted(
        self, db_session: AsyncSession, device_orm: DeviceORM
    ):
        """Test that get_by_refresh_token_hash excludes soft-deleted sessions."""
        # Create and then soft-delete session
        now = datetime.now(UTC)
        from leadr.auth.services.repositories import DeviceSessionRepository

        repository = DeviceSessionRepository(db_session)
        session = DeviceSession(
            device_id=DeviceID(device_orm.id),
            access_token_hash="test_access_hash",
            refresh_token_hash="deleted_refresh_hash",
            expires_at=now + timedelta(hours=1),
            refresh_expires_at=now + timedelta(days=30),
        )
        created_session = await repository.create(session)

        # Soft delete
        created_session.deleted_at = datetime.now(UTC)
        await repository.update(created_session)

        # Try to retrieve - should return None
        retrieved = await repository.get_by_refresh_token_hash("deleted_refresh_hash")

        assert retrieved is None
