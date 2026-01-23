"""Tests for Client Score API routes."""

import hashlib
from uuid import uuid4

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.auth.services.device_service import DeviceService
from leadr.boards.services.board_service import BoardService
from leadr.games.services.game_service import GameService
from leadr.scores.services.score_service import ScoreService


@pytest.mark.asyncio
class TestGetScoreClient:
    """Test suite for GET /client/scores/{score_id} endpoint."""

    async def test_get_score_success(self, client: AsyncClient, db_session):
        """Test fetching a score from the same game as the authenticated device."""
        # Create account, game, and board
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

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
        )

        # Start client session
        device_fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": device_fingerprint,
                "platform": "ios",
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        # Look up device via DeviceService (device_id no longer in session response)
        device_service = DeviceService(db_session)
        device = await device_service.repository.get_by_game_and_fingerprint(
            game.id, device_fingerprint
        )
        assert device is not None

        # Create a score for this device/board
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=1000.0,
        )

        # Fetch the score via client API
        response = await client.get(
            f"/client/scores/{score.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(score.id)
        assert data["player_name"] == "TestPlayer"
        assert data["value"] == 1000.0
        assert data["board_id"] == str(board.id)
        assert data["game_id"] == str(game.id)
        assert data["account_id"] == str(account.id)
        # Client response should have rank computed
        assert data["rank"] == 1
        # Client response should NOT include device_id or geo fields
        assert "device_id" not in data
        assert "timezone" not in data
        assert "country" not in data
        assert "city" not in data

    async def test_get_score_different_game_returns_403(self, client: AsyncClient, db_session):
        """Test that fetching a score from a different game returns 403."""
        # Create account with two games
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-2games",
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

        board_service = BoardService(db_session)
        # Create board for game2
        board2 = await board_service.create_board(
            account_id=account.id,
            game_id=game2.id,
            name="Board for Game 2",
        )

        # Start session for game1
        device_fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game1.id),
                "client_fingerprint": device_fingerprint,
                "platform": "android",
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        # Create device for game2 to create score
        device2_fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        await client.post(
            "/client/sessions",
            json={
                "game_id": str(game2.id),
                "client_fingerprint": device2_fingerprint,
                "platform": "android",
            },
        )

        # Look up device via DeviceService
        device_service = DeviceService(db_session)
        device2 = await device_service.repository.get_by_game_and_fingerprint(
            game2.id, device2_fingerprint
        )
        assert device2 is not None

        # Create a score for game2
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game2.id,
            board_id=board2.id,
            device_id=device2.id,
            player_name="Game2Player",
            value=2000.0,
        )

        # Try to fetch game2's score using game1's device token
        response = await client.get(
            f"/client/scores/{score.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 403
        assert "access" in response.json()["error"].lower()

    async def test_get_score_not_found_returns_404(self, client: AsyncClient, db_session):
        """Test that fetching a non-existent score returns 404."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-notfound",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Start session
        device_fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": device_fingerprint,
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        # Try to fetch non-existent score
        fake_score_id = f"scr_{uuid4()}"
        response = await client.get(
            f"/client/scores/{fake_score_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 404

    async def test_get_score_without_auth_returns_401(self, client: AsyncClient):
        """Test that fetching a score without authentication returns 401."""
        fake_score_id = f"scr_{uuid4()}"
        response = await client.get(f"/client/scores/{fake_score_id}")

        assert response.status_code == 401
        assert "required" in response.json()["error"].lower()

    async def test_get_score_with_invalid_token_returns_401(self, client: AsyncClient):
        """Test that fetching a score with invalid token returns 401."""
        fake_score_id = f"scr_{uuid4()}"
        response = await client.get(
            f"/client/scores/{fake_score_id}",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["error"].lower()
