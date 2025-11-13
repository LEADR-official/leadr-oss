"""Tests for Device Session API routes."""

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.auth.services.device_service import DeviceService
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestDeviceSessionRoutes:
    """Test suite for Device Session API routes."""

    async def test_list_sessions(self, client: AsyncClient, db_session, test_api_key):
        """Test listing device sessions via API."""
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

        # Create devices and sessions
        device_service = DeviceService(db_session)
        device1, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )
        device2, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-002",
        )

        # List sessions
        response = await client.get(
            f"/device-sessions?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_list_sessions_filter_by_device(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering sessions by device_id via API."""
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

        # Create devices and sessions
        device_service = DeviceService(db_session)
        device1, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )
        await device_service.start_session(
            game_id=game.id,
            device_id="test-device-002",
        )

        # Filter by device1
        response = await client.get(
            f"/device-sessions?account_id={account.id}&device_id={device1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["device_id"] == str(device1.id)

    async def test_get_session(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a single device session by ID via API."""
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

        # Create device and session
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        # Get the session
        sessions = await device_service.session_repo.filter(
            account_id=account.id,
            device_id=device.id,
        )
        session = sessions[0]

        # Get session via API
        response = await client.get(
            f"/device-sessions/{session.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(session.id)
        assert data["device_id"] == str(device.id)

    async def test_get_session_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a non-existent session returns 404."""
        response = await client.get(
            "/device-sessions/00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404

    async def test_revoke_session(self, client: AsyncClient, db_session, test_api_key):
        """Test revoking a device session via API."""
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

        # Create device and session
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        # Get the session
        sessions = await device_service.session_repo.filter(
            account_id=account.id,
            device_id=device.id,
        )
        session = sessions[0]

        # Revoke session
        response = await client.patch(
            f"/device-sessions/{session.id}",
            json={"revoked": True},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["revoked_at"] is not None

    async def test_list_sessions_requires_account_id(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that listing sessions requires account_id parameter."""
        response = await client.get(
            "/device-sessions",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        assert "account_id" in response.json()["detail"].lower()
