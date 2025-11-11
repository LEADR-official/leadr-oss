"""Tests for Score API routes."""

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.accounts.services.user_service import UserService
from leadr.boards.domain.board import KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.games.services.game_service import GameService
from leadr.scores.services.score_service import ScoreService


@pytest.mark.asyncio
class TestScoreRoutes:
    """Test suite for Score API routes."""

    async def test_create_score(self, client: AsyncClient, db_session, test_api_key):
        """Test creating a score via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
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
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create score
        response = await client.post(
            "/scores",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "board_id": str(board.id),
                "user_id": str(user.id),
                "player_name": "SpeedRunner99",
                "value": 123.45,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["player_name"] == "SpeedRunner99"
        assert data["value"] == 123.45
        assert data["account_id"] == str(account.id)
        assert data["game_id"] == str(game.id)
        assert data["board_id"] == str(board.id)
        assert data["user_id"] == str(user.id)
        assert "id" in data
        assert "created_at" in data

    async def test_create_score_with_optional_fields(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score with optional fields via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
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
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create score with optional fields
        response = await client.post(
            "/scores",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "board_id": str(board.id),
                "user_id": str(user.id),
                "player_name": "SpeedRunner99",
                "value": 123.45,
                "value_display": "2:03.45",
                "filter_timezone": "America/New_York",
                "filter_country": "USA",
                "filter_city": "New York",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["value_display"] == "2:03.45"
        assert data["filter_timezone"] == "America/New_York"
        assert data["filter_country"] == "USA"
        assert data["filter_city"] == "New York"

    async def test_create_score_with_board_not_found(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score with non-existent board returns 404."""
        # Create account, user, and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Try to create score with non-existent board
        response = await client.post(
            "/scores",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "board_id": "00000000-0000-0000-0000-000000000000",
                "user_id": str(user.id),
                "player_name": "SpeedRunner99",
                "value": 123.45,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_create_score_with_board_from_different_account(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score with board from different account returns 400."""
        # Create two accounts
        account_service = AccountService(db_session)
        account1 = await account_service.create_account(
            name="Account 1",
            slug="account-1",
        )
        account2 = await account_service.create_account(
            name="Account 2",
            slug="account-2",
        )

        # Create user for account1
        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account1.id,
            email="player@example.com",
            display_name="Test Player",
        )

        # Create games for both accounts
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account1.id,
            name="Game 1",
        )
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game 2",
        )

        # Create board for account2
        board_service = BoardService(db_session)
        board2 = await board_service.create_board(
            account_id=account2.id,
            game_id=game2.id,
            name="Account 2 Board",
            icon="star",
            short_code="A2B1",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Try to create score for account1 with account2's board
        response = await client.post(
            "/scores",
            json={
                "account_id": str(account1.id),
                "game_id": str(game1.id),
                "board_id": str(board2.id),
                "user_id": str(user.id),
                "player_name": "SpeedRunner99",
                "value": 123.45,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        assert "does not belong to account" in response.json()["detail"].lower()

    async def test_create_score_with_mismatched_game_id(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score with mismatched game_id returns 400."""
        # Create account and user
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
        )

        # Create two games
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account.id,
            name="Game 1",
        )
        game2 = await game_service.create_game(
            account_id=account.id,
            name="Game 2",
        )

        # Create board for game1
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game1.id,
            name="Game 1 Board",
            icon="trophy",
            short_code="G1B1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Try to create score with game2 (mismatched)
        response = await client.post(
            "/scores",
            json={
                "account_id": str(account.id),
                "game_id": str(game2.id),
                "board_id": str(board.id),
                "user_id": str(user.id),
                "player_name": "SpeedRunner99",
                "value": 123.45,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        assert "does not match board" in response.json()["detail"].lower()

    async def test_get_score(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a score by ID via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
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
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create score
        score_service = ScoreService(db_session)
        score = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            user_id=user.id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        # Get score
        response = await client.get(
            f"/scores/{score.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(score.id)
        assert data["player_name"] == "SpeedRunner99"

    async def test_get_score_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a non-existent score returns 404."""
        response = await client.get(
            "/scores/00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404

    async def test_list_scores(self, client: AsyncClient, db_session, test_api_key):
        """Test listing scores for an account via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
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
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create multiple scores
        score_service = ScoreService(db_session)
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            user_id=user.id,
            player_name="Player1",
            value=100.0,
        )
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            user_id=user.id,
            player_name="Player2",
            value=200.0,
        )

        # List scores
        response = await client.get(
            f"/scores?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = {s["player_name"] for s in data}
        assert "Player1" in names
        assert "Player2" in names

    async def test_list_scores_filters_by_board(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering scores by board_id via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board 1",
            icon="trophy",
            short_code="B1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )
        board2 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board 2",
            icon="star",
            short_code="B2",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Create scores for both boards
        score_service = ScoreService(db_session)
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board1.id,
            user_id=user.id,
            player_name="Board1Score",
            value=100.0,
        )
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board2.id,
            user_id=user.id,
            player_name="Board2Score",
            value=200.0,
        )

        # Filter by board1
        response = await client.get(
            f"/scores?account_id={account.id}&board_id={board1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["player_name"] == "Board1Score"

    async def test_update_score(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a score via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
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
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create score
        score_service = ScoreService(db_session)
        score = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            user_id=user.id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        # Update score
        response = await client.patch(
            f"/scores/{score.id}",
            json={
                "player_name": "NewName",
                "value": 200.0,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["player_name"] == "NewName"
        assert data["value"] == 200.0

    async def test_update_score_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a non-existent score returns 404."""
        response = await client.patch(
            "/scores/00000000-0000-0000-0000-000000000000",
            json={"player_name": "NewName"},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404

    async def test_soft_delete_score(self, client: AsyncClient, db_session, test_api_key):
        """Test soft-deleting a score via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
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
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create score
        score_service = ScoreService(db_session)
        score = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            user_id=user.id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        # Soft-delete score
        response = await client.patch(
            f"/scores/{score.id}",
            json={"deleted": True},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200

        # Verify it's not in list
        response = await client.get(
            f"/scores?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        assert len(response.json()) == 0

    async def test_list_scores_excludes_deleted(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that list_scores excludes soft-deleted scores."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
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
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create two scores
        score_service = ScoreService(db_session)
        score1 = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            user_id=user.id,
            player_name="Score1",
            value=100.0,
        )
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            user_id=user.id,
            player_name="Score2",
            value=200.0,
        )

        # Soft-delete score1
        await score_service.soft_delete(score1.id)

        # List should only return score2
        response = await client.get(
            f"/scores?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["player_name"] == "Score2"
