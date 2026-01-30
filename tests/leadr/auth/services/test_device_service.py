"""Tests for DeviceService."""

import hashlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from leadr.auth.domain.device import Device, DeviceStatus
from leadr.auth.services.device_service import DeviceService
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, DeviceID, GameID
from leadr.common.domain.pagination_result import PaginatedResult


@pytest.mark.asyncio
class TestDeviceService:
    """Test suite for DeviceService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create a DeviceService with mocked repository."""
        svc = DeviceService(mock_session)
        svc.repository = MagicMock()
        return svc

    async def test_get_or_create_device_creates_new_device(self, service, mock_session):
        """Test get_or_create_device creates a new device if it doesn't exist."""
        # Setup
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()

        # Mock game lookup
        game_mock = MagicMock()
        game_mock.account_id = account_id.uuid
        mock_session.get = AsyncMock(return_value=game_mock)

        # Mock repository - no existing device
        service.repository.get_by_game_and_fingerprint = AsyncMock(return_value=None)

        # Mock create to return the device with proper attributes
        async def mock_create(device: Device) -> Device:
            return device

        service.repository.create = AsyncMock(side_effect=mock_create)

        # Execute
        device = await service.get_or_create_device(
            game_id=game_id,
            client_fingerprint=fingerprint,
            platform="ios",
            metadata={"app_version": "1.0.0"},
        )

        # Verify
        assert device is not None
        assert device.client_fingerprint == fingerprint
        assert device.game_id == game_id
        assert device.account_id == account_id
        assert device.platform == "ios"
        assert device.status == DeviceStatus.ACTIVE
        assert device.metadata == {"app_version": "1.0.0"}
        service.repository.create.assert_called_once()
        service.repository.get_by_game_and_fingerprint.assert_called_once_with(game_id, fingerprint)

    async def test_get_or_create_device_returns_existing_device(self, service, mock_session):
        """Test get_or_create_device returns existing device and updates last_seen_at."""
        # Setup
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        first_seen = datetime.now(UTC)

        # Mock game lookup
        game_mock = MagicMock()
        game_mock.account_id = account_id.uuid
        mock_session.get = AsyncMock(return_value=game_mock)

        # Create existing device
        existing_device = Device(
            game_id=game_id,
            client_fingerprint=fingerprint,
            account_id=account_id,
            platform="ios",
            first_seen_at=first_seen,
            last_seen_at=first_seen,
            metadata={},
        )

        # Mock repository - return existing device
        service.repository.get_by_game_and_fingerprint = AsyncMock(return_value=existing_device)

        # Mock update to return the updated device
        async def mock_update(device: Device) -> Device:
            return device

        service.repository.update = AsyncMock(side_effect=mock_update)

        # Execute
        device = await service.get_or_create_device(
            game_id=game_id,
            client_fingerprint=fingerprint,
            platform="ios",
        )

        # Verify
        assert device.id == existing_device.id
        assert device.last_seen_at >= first_seen
        service.repository.update.assert_called_once()
        service.repository.get_by_game_and_fingerprint.assert_called_once_with(game_id, fingerprint)

    async def test_get_or_create_device_raises_for_nonexistent_game(self, service, mock_session):
        """Test that get_or_create_device for nonexistent game raises error."""
        # Setup
        game_id = GameID(uuid4())
        fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()

        # Mock game lookup - game not found
        mock_session.get = AsyncMock(return_value=None)

        # Execute & Verify
        with pytest.raises(EntityNotFoundError):
            await service.get_or_create_device(
                game_id=game_id,
                client_fingerprint=fingerprint,
                platform="ios",
            )

    async def test_list_devices_by_account(self, service):
        """Test listing devices filtered by account."""
        # Setup
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        devices = [
            Device(
                game_id=game_id,
                client_fingerprint=hashlib.sha256(f"device_{i}".encode()).hexdigest(),
                account_id=account_id,
                platform="android",
                first_seen_at=datetime.now(UTC),
                last_seen_at=datetime.now(UTC),
                metadata={},
            )
            for i in range(3)
        ]

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        expected_result = PaginatedResult(
            items=devices,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        # Mock repository filter
        service.repository.filter = AsyncMock(return_value=expected_result)

        # Execute
        result = await service.list_devices(
            account_id=account_id,
            pagination=pagination,
        )

        # Verify
        assert len(result.items) == 3
        service.repository.filter.assert_called_once_with(
            account_id=account_id,
            game_id=None,
            status=None,
            pagination=pagination,
        )

    async def test_get_device_by_id(self, service):
        """Test getting a device by ID."""
        # Setup
        device_id = uuid4()
        expected_device = Device(
            id=DeviceID(device_id),
            game_id=GameID(uuid4()),
            client_fingerprint=hashlib.sha256(str(uuid4()).encode()).hexdigest(),
            account_id=AccountID(uuid4()),
            platform="ios",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            metadata={},
        )

        # Mock repository get_by_id (called via BaseService.get_by_id)
        service.repository.get_by_id = AsyncMock(return_value=expected_device)

        # Execute
        device = await service.get_device(device_id)

        # Verify
        assert device is not None
        assert device.id == expected_device.id
        service.repository.get_by_id.assert_called_once_with(device_id)

    async def test_get_device_not_found(self, service):
        """Test getting a non-existent device returns None."""
        # Setup
        device_id = uuid4()

        # Mock repository get_by_id
        service.repository.get_by_id = AsyncMock(return_value=None)

        # Execute
        device = await service.get_device(device_id)

        # Verify
        assert device is None
        service.repository.get_by_id.assert_called_once_with(device_id)

    async def test_ban_device(self, service):
        """Test banning a device."""
        # Setup
        device_id = DeviceID(uuid4())
        device = Device(
            id=device_id,
            game_id=GameID(uuid4()),
            client_fingerprint=hashlib.sha256(str(uuid4()).encode()).hexdigest(),
            account_id=AccountID(uuid4()),
            platform="ios",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            metadata={},
            status=DeviceStatus.ACTIVE,
        )

        # Mock repository
        service.repository.get_by_id = AsyncMock(return_value=device)

        async def mock_update(device: Device) -> Device:
            return device

        service.repository.update = AsyncMock(side_effect=mock_update)

        # Execute
        result = await service.ban_device(device_id)

        # Verify
        assert result.status == DeviceStatus.BANNED
        service.repository.update.assert_called_once()

    async def test_suspend_device(self, service):
        """Test suspending a device."""
        # Setup
        device_id = DeviceID(uuid4())
        device = Device(
            id=device_id,
            game_id=GameID(uuid4()),
            client_fingerprint=hashlib.sha256(str(uuid4()).encode()).hexdigest(),
            account_id=AccountID(uuid4()),
            platform="ios",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            metadata={},
            status=DeviceStatus.ACTIVE,
        )

        # Mock repository
        service.repository.get_by_id = AsyncMock(return_value=device)

        async def mock_update(device: Device) -> Device:
            return device

        service.repository.update = AsyncMock(side_effect=mock_update)

        # Execute
        result = await service.suspend_device(device_id)

        # Verify
        assert result.status == DeviceStatus.SUSPENDED
        service.repository.update.assert_called_once()

    async def test_activate_device(self, service):
        """Test activating a banned device."""
        # Setup
        device_id = DeviceID(uuid4())
        device = Device(
            id=device_id,
            game_id=GameID(uuid4()),
            client_fingerprint=hashlib.sha256(str(uuid4()).encode()).hexdigest(),
            account_id=AccountID(uuid4()),
            platform="ios",
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            metadata={},
            status=DeviceStatus.BANNED,
        )

        # Mock repository
        service.repository.get_by_id = AsyncMock(return_value=device)

        async def mock_update(device: Device) -> Device:
            return device

        service.repository.update = AsyncMock(side_effect=mock_update)

        # Execute
        result = await service.activate_device(device_id)

        # Verify
        assert result.status == DeviceStatus.ACTIVE
        service.repository.update.assert_called_once()

    async def test_ban_device_not_found(self, service):
        """Test banning a non-existent device raises error."""
        # Setup
        device_id = DeviceID(uuid4())

        # Mock repository get_by_id - device not found
        service.repository.get_by_id = AsyncMock(return_value=None)

        # Execute & Verify
        with pytest.raises(EntityNotFoundError):
            await service.ban_device(device_id)
