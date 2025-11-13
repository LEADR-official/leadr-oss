"""Tests for Device API routes."""

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.auth.services.device_service import DeviceService
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestDeviceRoutes:
    """Test suite for Device API routes."""

    async def test_list_devices(self, client: AsyncClient, db_session, test_api_key):
        """Test listing devices via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create devices
        device_service = DeviceService(db_session)
        device1, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
            platform="iOS",
        )
        device2, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-002",
            platform="Android",
        )

        # List devices
        response = await client.get(
            f"/devices?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        device_ids = {d["device_id"] for d in data}
        assert "test-device-001" in device_ids
        assert "test-device-002" in device_ids

    async def test_list_devices_filter_by_game(self, client: AsyncClient, db_session, test_api_key):
        """Test filtering devices by game_id via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account.id,
            name="Game 1",
        )
        game2 = await game_service.create_game(
            account_id=account.id,
            name="Game 2",
        )

        # Create devices for both games
        device_service = DeviceService(db_session)
        await device_service.start_session(
            game_id=game1.id,
            device_id="game1-device",
        )
        await device_service.start_session(
            game_id=game2.id,
            device_id="game2-device",
        )

        # Filter by game1
        response = await client.get(
            f"/devices?account_id={account.id}&game_id={game1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["device_id"] == "game1-device"

    async def test_list_devices_filter_by_status(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering devices by status via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create devices
        device_service = DeviceService(db_session)
        device1, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="active-device",
        )
        device2, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="banned-device",
        )

        # Ban one device
        device2.ban()
        await device_service.repository.update(device2)

        # Filter by ACTIVE status
        response = await client.get(
            f"/devices?account_id={account.id}&status=active",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["device_id"] == "active-device"
        assert data[0]["status"] == "active"

    async def test_get_device(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a single device by ID via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create device
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
            platform="iOS",
        )

        # Get device
        response = await client.get(
            f"/devices/{device.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(device.id)
        assert data["device_id"] == "test-device-001"
        assert data["platform"] == "iOS"
        assert data["status"] == "active"

    async def test_get_device_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a non-existent device returns 404."""
        response = await client.get(
            "/devices/00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404

    async def test_ban_device(self, client: AsyncClient, db_session, test_api_key):
        """Test banning a device via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create device
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        # Ban device
        response = await client.patch(
            f"/devices/{device.id}",
            json={"status": "banned"},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "banned"

    async def test_suspend_device(self, client: AsyncClient, db_session, test_api_key):
        """Test suspending a device via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create device
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        # Suspend device
        response = await client.patch(
            f"/devices/{device.id}",
            json={"status": "suspended"},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "suspended"

    async def test_activate_device(self, client: AsyncClient, db_session, test_api_key):
        """Test activating a suspended device via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create and suspend device
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )
        device.suspend()
        await device_service.repository.update(device)

        # Activate device
        response = await client.patch(
            f"/devices/{device.id}",
            json={"status": "active"},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    async def test_list_devices_requires_account_id(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that listing devices requires account_id parameter."""
        response = await client.get(
            "/devices",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        assert "account_id" in response.json()["detail"].lower()
