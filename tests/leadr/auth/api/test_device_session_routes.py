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
        hash1 = "cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0"
        hash2 = "f0bfe8b352e3f87c10f5f37ccd2e3a5fb22ba397a54b43172a9770466537bc89"
        device1, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint=hash1,
        )
        device2, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint=hash2,
        )

        # List sessions
        response = await client.get(
            f"/device-sessions?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 2

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
        hash1 = "cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0"
        hash2 = "f0bfe8b352e3f87c10f5f37ccd2e3a5fb22ba397a54b43172a9770466537bc89"
        device1, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint=hash1,
        )
        await device_service.start_session(
            game_id=game.id,
            client_fingerprint=hash2,
        )

        # Filter by device1
        response = await client.get(
            f"/device-sessions?account_id={account.id}&device_id={device1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["device_id"] == str(device1.id)

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
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
            "/device-sessions/ses_00000000-0000-0000-0000-000000000000",
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
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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

    async def test_superadmin_list_sessions_without_account_id_returns_all(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test that superadmin can list sessions WITHOUT account_id and sees all accounts."""
        from datetime import UTC, datetime

        from leadr.accounts.domain.account import Account, AccountStatus
        from leadr.accounts.services.repositories import AccountRepository
        from leadr.common.domain.ids import AccountID

        # Create two accounts with devices/sessions in each
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="Account One Sessions",
            slug="account-one-sessions",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="Account Two Sessions",
            slug="account-two-sessions",
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
            name="Game Account 1",
        )
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game Account 2",
        )

        device_service = DeviceService(db_session)
        hash1 = "aaa93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfa0"
        hash2 = "bbb93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0"
        await device_service.start_session(
            game_id=game1.id,
            client_fingerprint=hash1,
        )
        await device_service.start_session(
            game_id=game2.id,
            client_fingerprint=hash2,
        )

        # List sessions WITHOUT account_id - should return sessions from ALL accounts
        response = await authenticated_client.get("/device-sessions")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        # Should contain sessions from both accounts (at least 2)
        assert len(data["data"]) >= 2
