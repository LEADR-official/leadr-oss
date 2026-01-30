"""Integration tests for game pagination."""

import pytest
from httpx import AsyncClient

from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.pagination import CursorPosition
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.games.domain.game import Game


@pytest.mark.asyncio
class TestGamePagination:
    """Test game pagination through API."""

    async def test_default_pagination(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ) -> None:
        """Test that default limit is 20 and default sort is created_at:desc,id:asc."""
        # Arrange
        account_id = admin_auth.account_id
        games = [
            Game(account_id=account_id, name=f"Test Game {i}", slug=f"test-game-{i}")
            for i in range(20)
        ]
        result = PaginatedResult(
            items=games,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(values=("2024-01-01", "123"), entity_id="123"),
            prev_position=None,
        )
        mock_game_service.list_games.return_value = result

        # Act
        response = await mock_client_no_db.get(f"/games?account_id={account_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify paginated response structure
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

        # Verify pagination metadata
        pagination = data["pagination"]
        assert "next_cursor" in pagination
        assert "prev_cursor" in pagination
        assert "has_next" in pagination
        assert "has_prev" in pagination
        assert "count" in pagination

        # Should have 20 items (default limit)
        assert pagination["count"] == 20
        assert len(data["data"]) == 20
        assert pagination["has_next"] is True
        assert pagination["has_prev"] is False
        assert pagination["next_cursor"] is not None

    async def test_forward_navigation(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ) -> None:
        """Test forward pagination using next_cursor."""
        # Arrange
        account_id = admin_auth.account_id
        page1_games = [
            Game(account_id=account_id, name=f"Game {i:03d}", slug=f"game-{i:03d}")
            for i in range(10)
        ]
        page2_games = [
            Game(account_id=account_id, name=f"Game {i:03d}", slug=f"game-{i:03d}")
            for i in range(10, 20)
        ]

        page1_result = PaginatedResult(
            items=page1_games,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(values=("2024-01-01", "page1"), entity_id="page1"),
            prev_position=None,
        )
        page2_result = PaginatedResult(
            items=page2_games,
            has_next=True,
            has_prev=True,
            next_position=CursorPosition(values=("2024-01-01", "page2"), entity_id="page2"),
            prev_position=CursorPosition(values=("2024-01-01", "page1"), entity_id="page1"),
        )
        mock_game_service.list_games.side_effect = [page1_result, page2_result]

        # Act - Get first page
        response1 = await mock_client_no_db.get(f"/games?account_id={account_id}&limit=10")
        assert response1.status_code == 200
        page1 = response1.json()
        assert len(page1["data"]) == 10
        assert page1["pagination"]["has_next"] is True

        # Get second page using cursor
        next_cursor = page1["pagination"]["next_cursor"]
        response2 = await mock_client_no_db.get(
            f"/games?account_id={account_id}&limit=10&cursor={next_cursor}"
        )

        # Assert
        assert response2.status_code == 200
        page2 = response2.json()
        assert len(page2["data"]) == 10
        assert page2["pagination"]["has_prev"] is True

        # Verify no overlap between pages
        page1_ids = {game["id"] for game in page1["data"]}
        page2_ids = {game["id"] for game in page2["data"]}
        assert len(page1_ids & page2_ids) == 0  # No overlap

    async def test_backward_navigation(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ) -> None:
        """Test backward pagination using prev_cursor."""
        # Arrange
        account_id = admin_auth.account_id
        page1_games = [
            Game(account_id=account_id, name=f"Game {i:03d}", slug=f"game-{i:03d}")
            for i in range(10)
        ]
        page2_games = [
            Game(account_id=account_id, name=f"Game {i:03d}", slug=f"game-{i:03d}")
            for i in range(10, 20)
        ]

        page1_result = PaginatedResult(
            items=page1_games,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(values=("2024-01-01", "page1"), entity_id="page1"),
            prev_position=None,
        )
        page2_result = PaginatedResult(
            items=page2_games,
            has_next=True,
            has_prev=True,
            next_position=CursorPosition(values=("2024-01-01", "page2"), entity_id="page2"),
            prev_position=CursorPosition(values=("2024-01-01", "page1"), entity_id="page1"),
        )
        page1_again_result = PaginatedResult(
            items=page1_games,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(values=("2024-01-01", "page1"), entity_id="page1"),
            prev_position=None,
        )
        mock_game_service.list_games.side_effect = [
            page1_result,
            page2_result,
            page1_again_result,
        ]

        # Act - Get first page
        response1 = await mock_client_no_db.get(f"/games?account_id={account_id}&limit=10")
        page1 = response1.json()

        # Get second page
        next_cursor = page1["pagination"]["next_cursor"]
        response2 = await mock_client_no_db.get(
            f"/games?account_id={account_id}&limit=10&cursor={next_cursor}"
        )
        page2 = response2.json()
        assert page2["pagination"]["has_prev"] is True

        # Go back to first page using prev_cursor
        prev_cursor = page2["pagination"]["prev_cursor"]
        response3 = await mock_client_no_db.get(
            f"/games?account_id={account_id}&limit=10&cursor={prev_cursor}"
        )

        # Assert
        assert response3.status_code == 200
        page_back = response3.json()

        # Should match first page
        assert len(page_back["data"]) == len(page1["data"])
        page_back_ids = {game["id"] for game in page_back["data"]}
        page1_ids = {game["id"] for game in page1["data"]}
        assert page_back_ids == page1_ids

    async def test_custom_sort(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ) -> None:
        """Test pagination with custom sort (name ascending)."""
        # Arrange
        account_id = admin_auth.account_id
        sorted_names = ["Arena Battle", "Card Master", "Dragon Quest", "Zombie Shooter"]
        games = [
            Game(account_id=account_id, name=name, slug=name.lower().replace(" ", "-"))
            for name in sorted_names
        ]
        result = PaginatedResult(
            items=games,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_game_service.list_games.return_value = result

        # Act
        response = await mock_client_no_db.get(f"/games?account_id={account_id}&sort=name:asc")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify ascending order
        games = data["data"]
        game_names = [game["name"] for game in games]
        assert game_names == sorted_names

    async def test_invalid_sort_field(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ) -> None:
        """Test that invalid sort field returns 400 error."""
        # Arrange
        account_id = admin_auth.account_id
        mock_game_service.list_games.side_effect = ValueError("Unknown sort field: invalid_field")

        # Act
        response = await mock_client_no_db.get(
            f"/games?account_id={account_id}&sort=invalid_field:desc"
        )

        # Assert
        assert response.status_code == 400
        assert "Unknown sort field" in response.json()["error"]

    async def test_cursor_state_validation(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ) -> None:
        """Test that cursor state mismatch returns 400 error."""
        # Arrange
        account_id = admin_auth.account_id
        page1_games = [
            Game(account_id=account_id, name=f"Game {i}", slug=f"game-{i}") for i in range(10)
        ]
        page1_result = PaginatedResult(
            items=page1_games,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(values=("Game 10", "123"), entity_id="123"),
            prev_position=None,
        )
        mock_game_service.list_games.side_effect = [
            page1_result,
            CursorValidationError("Query parameters don't match cursor state"),
        ]

        # Act - Get first page with one sort
        response1 = await mock_client_no_db.get(
            f"/games?account_id={account_id}&sort=name:desc&limit=10"
        )
        page1 = response1.json()
        cursor = page1["pagination"]["next_cursor"]

        # Try to use cursor with different sort
        response2 = await mock_client_no_db.get(
            f"/games?account_id={account_id}&sort=created_at:asc&limit=10&cursor={cursor}"
        )

        # Assert
        assert response2.status_code == 400
        assert "Query parameters don't match cursor state" in response2.json()["error"]

    async def test_pagination_with_filters(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ) -> None:
        """Test pagination requires account_id filter."""
        # Arrange
        account_id = admin_auth.account_id
        games = [Game(account_id=account_id, name=f"Game {i}", slug=f"game-{i}") for i in range(5)]
        result = PaginatedResult(
            items=games,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(values=("2024-01-01", "123"), entity_id="123"),
            prev_position=None,
        )
        mock_game_service.list_games.return_value = result

        # Act
        response = await mock_client_no_db.get(f"/games?account_id={account_id}&limit=5")

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["count"] == 5
        assert len(data["data"]) == 5
        assert data["pagination"]["has_next"] is True

        # Verify all games belong to the account
        for game in data["data"]:
            assert game["account_id"] == str(account_id)
