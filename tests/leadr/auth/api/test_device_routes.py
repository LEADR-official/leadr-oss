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
        hash1 = "cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0"
        hash2 = "f0bfe8b352e3f87c10f5f37ccd2e3a5fb22ba397a54b43172a9770466537bc89"
        device1 = await device_service.get_or_create_device(
            game_id=game.id,
            client_fingerprint=hash1,
            platform="iOS",
        )
        device2 = await device_service.get_or_create_device(
            game_id=game.id,
            client_fingerprint=hash2,
            platform="Android",
        )

        # List devices
        response = await client.get(
            f"/devices?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 2
        device_ids = {d["client_fingerprint"] for d in data["data"]}
        assert hash1 in device_ids
        assert hash2 in device_ids

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
        hash1 = "cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0"
        hash2 = "f0bfe8b352e3f87c10f5f37ccd2e3a5fb22ba397a54b43172a9770466537bc89"
        await device_service.get_or_create_device(
            game_id=game1.id,
            client_fingerprint=hash1,
        )
        await device_service.get_or_create_device(
            game_id=game2.id,
            client_fingerprint=hash2,
        )

        # Filter by game1
        response = await client.get(
            f"/devices?account_id={account.id}&game_id={game1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["client_fingerprint"] == hash1

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
        hash1 = "cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0"
        hash2 = "f0bfe8b352e3f87c10f5f37ccd2e3a5fb22ba397a54b43172a9770466537bc89"
        device1 = await device_service.get_or_create_device(
            game_id=game.id,
            client_fingerprint=hash1,
        )
        device2 = await device_service.get_or_create_device(
            game_id=game.id,
            client_fingerprint=hash2,
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
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["client_fingerprint"] == hash1
        assert data["data"][0]["status"] == "active"

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
        hash1 = "cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0"
        device = await device_service.get_or_create_device(
            game_id=game.id,
            client_fingerprint=hash1,
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
        assert data["client_fingerprint"] == hash1
        assert data["platform"] == "iOS"
        assert data["status"] == "active"

    async def test_get_device_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a non-existent device returns 404."""
        response = await client.get(
            "/devices/dev_00000000-0000-0000-0000-000000000000",
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
        device = await device_service.get_or_create_device(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
        device = await device_service.get_or_create_device(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
        device = await device_service.get_or_create_device(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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

    async def test_superadmin_list_devices_without_account_id_returns_all(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test that superadmin can list devices WITHOUT account_id and sees all accounts."""
        from datetime import UTC, datetime

        from leadr.accounts.domain.account import Account, AccountStatus
        from leadr.accounts.services.repositories import AccountRepository
        from leadr.common.domain.ids import AccountID

        # Create two accounts with devices in each
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="Account One Devices",
            slug="account-one-devices",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="Account Two Devices",
            slug="account-two-devices",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create games and devices for each account
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account1.id,
            name="Game Account 1 Dev",
        )
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game Account 2 Dev",
        )

        device_service = DeviceService(db_session)
        hash1 = "ccc93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfc0"
        hash2 = "ddd93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfd0"
        await device_service.get_or_create_device(
            game_id=game1.id,
            client_fingerprint=hash1,
        )
        await device_service.get_or_create_device(
            game_id=game2.id,
            client_fingerprint=hash2,
        )

        # List devices WITHOUT account_id - should return devices from ALL accounts
        response = await authenticated_client.get("/devices")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        # Should contain devices from both accounts
        fingerprints = {d["client_fingerprint"] for d in data["data"]}
        assert hash1 in fingerprints
        assert hash2 in fingerprints
