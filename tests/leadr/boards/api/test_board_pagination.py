"""Integration tests for board pagination."""

import pytest
from httpx import AsyncClient

from leadr.accounts.domain.account import Account
from leadr.games.domain.game import Game


@pytest.mark.asyncio
class TestBoardPagination:
    """Test board pagination through API."""

    async def test_default_pagination(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
    ) -> None:
        """Test that default limit is 20 and default sort is created_at:desc,id:asc."""
        # Create 25 boards
        for i in range(25):
            await authenticated_client.post(
                "/boards",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(test_game.id),
                    "name": f"Test Board {i}",
                    "icon": "trophy",
                    "short_code": f"TB{i:04d}",
                    "unit": "points",
                    "is_active": True,
                    "sort_direction": "DESCENDING",
                    "keep_strategy": "BEST_ONLY",
                },
            )

        # Get first page
        response = await authenticated_client.get(f"/boards?account_id={test_account.id}")
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
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
    ) -> None:
        """Test forward pagination using next_cursor."""
        # Create 30 boards
        for i in range(30):
            await authenticated_client.post(
                "/boards",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(test_game.id),
                    "name": f"Board {i:03d}",
                    "icon": "trophy",
                    "short_code": f"BRD{i:03d}",
                    "unit": "points",
                    "is_active": True,
                    "sort_direction": "DESCENDING",
                    "keep_strategy": "BEST_ONLY",
                },
            )

        # Get first page
        response = await authenticated_client.get(f"/boards?account_id={test_account.id}&limit=10")
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1["data"]) == 10
        assert page1["pagination"]["has_next"] is True

        # Get second page using cursor
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/boards?account_id={test_account.id}&limit=10&cursor={next_cursor}"
        )
        assert response.status_code == 200
        page2 = response.json()
        assert len(page2["data"]) == 10
        assert page2["pagination"]["has_prev"] is True

        # Verify no overlap between pages
        page1_ids = {board["id"] for board in page1["data"]}
        page2_ids = {board["id"] for board in page2["data"]}
        assert len(page1_ids & page2_ids) == 0  # No overlap

    async def test_backward_navigation(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
    ) -> None:
        """Test backward pagination using prev_cursor."""
        # Create 30 boards
        for i in range(30):
            await authenticated_client.post(
                "/boards",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(test_game.id),
                    "name": f"Board {i:03d}",
                    "icon": "trophy",
                    "short_code": f"BRD{i:03d}",
                    "unit": "points",
                    "is_active": True,
                    "sort_direction": "DESCENDING",
                    "keep_strategy": "BEST_ONLY",
                },
            )

        # Get first page
        response = await authenticated_client.get(f"/boards?account_id={test_account.id}&limit=10")
        page1 = response.json()

        # Get second page
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/boards?account_id={test_account.id}&limit=10&cursor={next_cursor}"
        )
        page2 = response.json()
        assert page2["pagination"]["has_prev"] is True

        # Go back to first page using prev_cursor
        prev_cursor = page2["pagination"]["prev_cursor"]
        response = await authenticated_client.get(
            f"/boards?account_id={test_account.id}&limit=10&cursor={prev_cursor}"
        )
        assert response.status_code == 200
        page_back = response.json()

        # Should match first page
        assert len(page_back["data"]) == len(page1["data"])
        page_back_ids = {board["id"] for board in page_back["data"]}
        page1_ids = {board["id"] for board in page1["data"]}
        assert page_back_ids == page1_ids

    async def test_custom_sort(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
    ) -> None:
        """Test pagination with custom sort (name ascending)."""
        # Create boards with different names
        names = ["Zombie Score", "Arena Points", "Card Wins", "Dragon Kills"]
        for i, name in enumerate(names):
            await authenticated_client.post(
                "/boards",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(test_game.id),
                    "name": name,
                    "icon": "trophy",
                    "short_code": f"TST{i:02d}",
                    "unit": "points",
                    "is_active": True,
                    "sort_direction": "DESCENDING",
                    "keep_strategy": "BEST_ONLY",
                },
            )

        # Get sorted by name ascending
        response = await authenticated_client.get(
            f"/boards?account_id={test_account.id}&sort=name:asc"
        )
        assert response.status_code == 200
        data = response.json()

        # Verify ascending order
        boards = data["data"]
        board_names = [board["name"] for board in boards if board["name"] in names]
        assert board_names == sorted(names)

    async def test_invalid_sort_field(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
    ) -> None:
        """Test that invalid sort field returns 400 error."""
        response = await authenticated_client.get(
            f"/boards?account_id={test_account.id}&sort=invalid_field:desc"
        )
        assert response.status_code == 400
        assert "Unknown sort field" in response.json()["error"]

    async def test_cursor_state_validation(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
    ) -> None:
        """Test that cursor state mismatch returns 400 error."""
        # Create boards
        for i in range(20):
            await authenticated_client.post(
                "/boards",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(test_game.id),
                    "name": f"Board {i}",
                    "icon": "trophy",
                    "short_code": f"BRD{i:02d}",
                    "unit": "points",
                    "is_active": True,
                    "sort_direction": "DESCENDING",
                    "keep_strategy": "BEST_ONLY",
                },
            )

        # Get first page with one sort (use limit=10 to ensure pagination)
        response = await authenticated_client.get(
            f"/boards?account_id={test_account.id}&sort=name:desc&limit=10"
        )
        page1 = response.json()
        cursor = page1["pagination"]["next_cursor"]

        # Try to use cursor with different sort
        response = await authenticated_client.get(
            f"/boards?account_id={test_account.id}&sort=short_code:asc&limit=10&cursor={cursor}"
        )
        assert response.status_code == 400
        assert "Query parameters don't match cursor state" in response.json()["error"]

    async def test_pagination_with_code_filter(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
    ) -> None:
        """Test pagination with code filter."""
        # Create boards with unique short codes
        test_code = "FILTER01"

        # Create 1 board with test_code (short_code is unique)
        await authenticated_client.post(
            "/boards",
            json={
                "account_id": str(test_account.id),
                "game_id": str(test_game.id),
                "name": "Test Board",
                "icon": "trophy",
                "short_code": test_code,
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "BEST_ONLY",
            },
        )

        # Create 10 boards with other codes
        for i in range(10):
            await authenticated_client.post(
                "/boards",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(test_game.id),
                    "name": f"Other Board {i}",
                    "icon": "medal",
                    "short_code": f"OTHER{i:02d}",
                    "unit": "points",
                    "is_active": True,
                    "sort_direction": "DESCENDING",
                    "keep_strategy": "BEST_ONLY",
                },
            )

        # Get boards filtered by code
        response = await authenticated_client.get(f"/boards?code={test_code}")
        assert response.status_code == 200
        data = response.json()

        # Should get exactly 1 board (short_code is unique)
        assert data["pagination"]["count"] == 1
        assert len(data["data"]) == 1
        assert data["pagination"]["has_next"] is False

        # Verify the board has the test_code
        assert data["data"][0]["short_code"] == test_code
