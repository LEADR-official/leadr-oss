"""Tests for player name availability check endpoint."""

import pytest
from httpx import AsyncClient

from leadr.boards.domain.board import BoardType, KeepStrategy
from tests.leadr.scores.api.conftest import make_board


@pytest.mark.asyncio
class TestPlayerNameCheck:
    """Test suite for player name availability check endpoint."""

    async def test_name_available_returns_true(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test that an available name returns available=true."""
        # Arrange
        board = make_board(
            account_id=client_auth.account_id,
            game_id=client_auth.game_id,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
            unique_player_names=True,
        )
        mock_board_service.list_boards.return_value = type(
            "PaginatedResult", (), {"items": [board]}
        )()

        # Mock service to return available
        mock_score_service.check_player_name_availability.return_value = (
            "alice",  # normalised_name
            True,  # available
            [],  # conflicts
        )

        # Act
        response = await mock_client_no_db.get(
            "/client/player-names/check",
            params={"name": "Alice"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Alice"
        assert data["normalised_name"] == "alice"
        assert data["available"] is True
        assert data["conflicts"] == []

    async def test_name_taken_returns_false_with_conflicts(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test that a taken name returns available=false with conflicts list."""
        # Arrange
        board = make_board(
            account_id=client_auth.account_id,
            game_id=client_auth.game_id,
            board_type=BoardType.RUN_IDENTITY,
            unique_player_names=True,
            name="High Scores",
        )
        mock_board_service.list_boards.return_value = type(
            "PaginatedResult", (), {"items": [board]}
        )()

        # Mock service to return conflict
        mock_score_service.check_player_name_availability.return_value = (
            "alice",
            False,
            [(board.id, "High Scores")],  # conflicts
        )

        # Act
        response = await mock_client_no_db.get(
            "/client/player-names/check",
            params={"name": "Alice"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Alice"
        assert data["normalised_name"] == "alice"
        assert data["available"] is False
        assert len(data["conflicts"]) == 1
        assert data["conflicts"][0]["board_name"] == "High Scores"

    async def test_check_specific_board_ids(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test checking specific board IDs only."""
        # Arrange
        board = make_board(
            account_id=client_auth.account_id,
            game_id=client_auth.game_id,
            unique_player_names=True,
        )
        mock_board_service.get_by_id.return_value = board

        mock_score_service.check_player_name_availability.return_value = (
            "player1",
            True,
            [],
        )

        # Act
        response = await mock_client_no_db.get(
            "/client/player-names/check",
            params={
                "name": "Player1",
                "board_ids": str(board.id),
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True

    async def test_case_insensitive_check(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test that name checking is case-insensitive."""
        # Arrange
        board = make_board(
            account_id=client_auth.account_id,
            game_id=client_auth.game_id,
            unique_player_names=True,
        )
        mock_board_service.list_boards.return_value = type(
            "PaginatedResult", (), {"items": [board]}
        )()

        # Service returns normalized lowercase name
        mock_score_service.check_player_name_availability.return_value = (
            "alice",  # normalised to lowercase
            False,  # taken
            [(board.id, "Board")],
        )

        # Act - submit uppercase
        response = await mock_client_no_db.get(
            "/client/player-names/check",
            params={"name": "ALICE"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "ALICE"
        assert data["normalised_name"] == "alice"
        assert data["available"] is False

    async def test_boards_without_unique_names_skipped(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test that boards without unique_player_names are not checked."""
        # Arrange - board has unique_player_names=False
        board = make_board(
            account_id=client_auth.account_id,
            game_id=client_auth.game_id,
            unique_player_names=False,  # Not enforcing unique names
        )
        mock_board_service.list_boards.return_value = type(
            "PaginatedResult", (), {"items": [board]}
        )()

        # Service returns available because no boards need checking
        mock_score_service.check_player_name_availability.return_value = (
            "player",
            True,
            [],
        )

        # Act
        response = await mock_client_no_db.get(
            "/client/player-names/check",
            params={"name": "Player"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["conflicts"] == []

    async def test_name_required(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test that name parameter is required."""
        # Act - missing name param
        response = await mock_client_no_db.get(
            "/client/player-names/check",
        )

        # Assert
        assert response.status_code == 422  # Validation error

    async def test_same_identity_excluded_from_conflicts(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test that the same identity's own name is not a conflict."""
        # Arrange
        board = make_board(
            account_id=client_auth.account_id,
            game_id=client_auth.game_id,
            unique_player_names=True,
        )
        mock_board_service.list_boards.return_value = type(
            "PaginatedResult", (), {"items": [board]}
        )()

        # Service returns available (identity owns this name)
        mock_score_service.check_player_name_availability.return_value = (
            "myname",
            True,
            [],
        )

        # Act
        response = await mock_client_no_db.get(
            "/client/player-names/check",
            params={"name": "MyName"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
