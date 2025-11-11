"""Tests for Client Authentication API routes."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestClientSessionRoutes:
    """Test suite for client session API routes."""

    async def test_start_session_creates_new_device(self, client: AsyncClient, db_session):
        """Test starting a session creates a new device and returns token."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Start session
        device_id = str(uuid4())
        response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "device_id": device_id,
                "platform": "ios",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["device_id"] == device_id
        assert data["game_id"] == str(game.id)
        assert data["platform"] == "ios"
        assert "access_token" in data
        assert "expires_in" in data
        assert data["expires_in"] > 0
        assert len(data["access_token"]) > 50  # JWT tokens are long

    async def test_start_session_updates_existing_device(self, client: AsyncClient, db_session):
        """Test starting a session for existing device updates last_seen_at."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Start first session
        device_id = str(uuid4())
        response1 = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "device_id": device_id,
                "platform": "android",
            },
        )
        assert response1.status_code == 201
        device_id_from_first = response1.json()["id"]

        # Start second session with same device_id
        response2 = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "device_id": device_id,
                "platform": "android",
            },
        )

        assert response2.status_code == 201
        data = response2.json()
        # Should be same device entity
        assert data["id"] == device_id_from_first
        assert data["device_id"] == device_id
        # But new access token
        assert data["access_token"] != response1.json()["access_token"]

    async def test_start_session_with_metadata(self, client: AsyncClient, db_session):
        """Test starting a session with device metadata."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Start session with metadata
        device_id = str(uuid4())
        metadata = {
            "device_model": "iPhone 14 Pro",
            "os_version": "iOS 17.2",
            "app_version": "1.2.3",
        }
        response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "device_id": device_id,
                "platform": "ios",
                "metadata": metadata,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["metadata"] == metadata

    async def test_start_session_without_platform(self, client: AsyncClient, db_session):
        """Test starting a session without platform (optional field)."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Start session without platform
        device_id = str(uuid4())
        response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "device_id": device_id,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["device_id"] == device_id
        assert data["platform"] is None

    async def test_start_session_with_nonexistent_game_returns_404(self, client: AsyncClient):
        """Test starting a session with nonexistent game returns 404."""
        response = await client.post(
            "/client/sessions",
            json={
                "game_id": "00000000-0000-0000-0000-000000000000",
                "device_id": str(uuid4()),
            },
        )

        assert response.status_code == 404
        assert "game" in response.json()["detail"].lower()

    async def test_start_session_requires_game_id(self, client: AsyncClient):
        """Test starting a session without game_id returns 422."""
        response = await client.post(
            "/client/sessions",
            json={
                "device_id": str(uuid4()),
            },
        )

        assert response.status_code == 422

    async def test_start_session_requires_device_id(self, client: AsyncClient):
        """Test starting a session without device_id returns 422."""
        response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(uuid4()),
            },
        )

        assert response.status_code == 422

    async def test_start_session_with_invalid_game_id_format_returns_422(self, client: AsyncClient):
        """Test starting a session with invalid game_id format returns 422."""
        response = await client.post(
            "/client/sessions",
            json={
                "game_id": "not-a-uuid",
                "device_id": str(uuid4()),
            },
        )

        assert response.status_code == 422
