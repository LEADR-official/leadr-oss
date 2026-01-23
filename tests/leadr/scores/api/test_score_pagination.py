"""Integration tests for score pagination."""

import pytest
from httpx import AsyncClient

from leadr.accounts.domain.account import Account
from leadr.auth.domain.device import Device
from leadr.boards.domain.board import Board


@pytest.mark.asyncio
class TestScorePagination:
    """Test score pagination through API."""

    async def test_get_scores_returns_paginated_response(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        run_runs_board: Board,
        test_device: Device,
    ) -> None:
        """Test that GET /scores returns paginated response format."""
        response = await authenticated_client.get(
            f"/scores?account_id={test_account.id}&board_id={run_runs_board.id}"
        )
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

    async def test_pagination_default_limit_20(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        run_runs_board: Board,
        test_device: Device,
    ) -> None:
        """Test that default page size is 20."""
        # Create 25 scores - using RUN_RUNS board to keep all
        for i in range(25):
            await authenticated_client.post(
                "/scores",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(run_runs_board.game_id),
                    "board_id": str(run_runs_board.id),
                    "device_id": str(test_device.id),
                    "player_name": f"Player{i}",
                    "value": float(100 + i),
                },
            )

        # Get first page
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}"
        )
        assert response.status_code == 200
        data = response.json()

        # Should have 20 items (default limit)
        assert data["pagination"]["count"] == 20
        assert len(data["data"]) == 20
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["has_prev"] is False
        assert data["pagination"]["next_cursor"] is not None

    async def test_pagination_custom_limit(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        run_runs_board: Board,
        test_device: Device,
    ) -> None:
        """Test custom page size."""
        # Create 15 scores
        for i in range(15):
            await authenticated_client.post(
                "/scores",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(run_runs_board.game_id),
                    "board_id": str(run_runs_board.id),
                    "device_id": str(test_device.id),
                    "player_name": f"Player{i}",
                    "value": float(100 + i),
                },
            )

        # Get with limit=5
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}&limit=5"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["count"] == 5
        assert len(data["data"]) == 5
        assert data["pagination"]["has_next"] is True

    async def test_pagination_forward_navigation(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        run_runs_board: Board,
        test_device: Device,
    ) -> None:
        """Test forward pagination using next_cursor."""
        # Create 30 scores
        for i in range(30):
            await authenticated_client.post(
                "/scores",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(run_runs_board.game_id),
                    "board_id": str(run_runs_board.id),
                    "device_id": str(test_device.id),
                    "player_name": f"Player{i}",
                    "value": float(1000 - i),  # Descending values
                },
            )

        # Get first page
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}&limit=10"
        )
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1["data"]) == 10
        assert page1["pagination"]["has_next"] is True

        # Get second page using cursor
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}&limit=10&cursor={next_cursor}"
        )
        assert response.status_code == 200
        page2 = response.json()
        assert len(page2["data"]) == 10
        assert page2["pagination"]["has_prev"] is True

        # Verify no overlap between pages
        page1_ids = {score["id"] for score in page1["data"]}
        page2_ids = {score["id"] for score in page2["data"]}
        assert len(page1_ids & page2_ids) == 0  # No overlap

    async def test_pagination_backward_navigation(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        run_runs_board: Board,
        test_device: Device,
    ) -> None:
        """Test backward pagination using prev_cursor."""
        # Create 30 scores
        for i in range(30):
            await authenticated_client.post(
                "/scores",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(run_runs_board.game_id),
                    "board_id": str(run_runs_board.id),
                    "device_id": str(test_device.id),
                    "player_name": f"Player{i}",
                    "value": float(1000 - i),
                },
            )

        # Get first page
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}&limit=10"
        )
        page1 = response.json()

        # Get second page
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}&limit=10&cursor={next_cursor}"
        )
        page2 = response.json()
        assert page2["pagination"]["has_prev"] is True

        # Go back to first page using prev_cursor
        prev_cursor = page2["pagination"]["prev_cursor"]
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}&limit=10&cursor={prev_cursor}"
        )
        assert response.status_code == 200
        page_back = response.json()

        # Should match first page
        assert len(page_back["data"]) == len(page1["data"])
        page_back_ids = {score["id"] for score in page_back["data"]}
        page1_ids = {score["id"] for score in page1["data"]}
        assert page_back_ids == page1_ids

    async def test_pagination_custom_sort_value_desc(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        run_runs_board: Board,
        test_device: Device,
    ) -> None:
        """Test pagination with custom sort (value descending)."""
        # Create scores with different values
        values = [100, 500, 300, 800, 200]
        for i, value in enumerate(values):
            await authenticated_client.post(
                "/scores",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(run_runs_board.game_id),
                    "board_id": str(run_runs_board.id),
                    "device_id": str(test_device.id),
                    "player_name": f"Player{i}",
                    "value": float(value),
                },
            )

        # Get sorted by value descending
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}&sort=value:desc"
        )
        assert response.status_code == 200
        data = response.json()

        # Verify descending order
        scores = data["data"]
        assert len(scores) == 5
        assert scores[0]["value"] == 800
        assert scores[1]["value"] == 500
        assert scores[2]["value"] == 300
        assert scores[3]["value"] == 200
        assert scores[4]["value"] == 100

    async def test_pagination_invalid_sort_field_returns_400(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        run_runs_board: Board,
        test_device: Device,
    ) -> None:
        """Test that invalid sort field returns 400 error."""
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}&sort=invalid_field:desc"
        )
        assert response.status_code == 400
        assert "Unknown sort field" in response.json()["error"]

    async def test_pagination_invalid_cursor_returns_400(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        run_runs_board: Board,
        test_device: Device,
    ) -> None:
        """Test that invalid cursor returns 400 error."""
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}&cursor=invalid-cursor"
        )
        assert response.status_code == 400
        assert "Invalid pagination cursor" in response.json()["error"]

    async def test_pagination_cursor_state_mismatch_returns_400(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        run_runs_board: Board,
        test_device: Device,
    ) -> None:
        """Test that cursor state mismatch returns 400 error."""
        # Create scores
        for i in range(20):
            await authenticated_client.post(
                "/scores",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(run_runs_board.game_id),
                    "board_id": str(run_runs_board.id),
                    "device_id": str(test_device.id),
                    "player_name": f"Player{i}",
                    "value": float(100 + i),
                },
            )

        # Get first page with one sort (use limit=10 to ensure pagination)
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}&sort=value:desc&limit=10"
        )
        page1 = response.json()
        cursor = page1["pagination"]["next_cursor"]

        # Try to use cursor with different sort
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}&sort=created_at:asc&limit=10&cursor={cursor}"
        )
        assert response.status_code == 400
        assert "Query parameters don't match cursor state" in response.json()["error"]

    async def test_pagination_empty_results(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        run_runs_board: Board,
        test_device: Device,
    ) -> None:
        """Test pagination with no results."""
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["data"] == []
        assert data["pagination"]["count"] == 0
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["has_prev"] is False
        assert data["pagination"]["next_cursor"] is None
        assert data["pagination"]["prev_cursor"] is None

    async def test_pagination_single_result(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        run_runs_board: Board,
        test_device: Device,
    ) -> None:
        """Test pagination with single result."""
        # Create one score
        await authenticated_client.post(
            "/scores",
            json={
                "account_id": str(test_account.id),
                "game_id": str(run_runs_board.game_id),
                "board_id": str(run_runs_board.id),
                "device_id": str(test_device.id),
                "player_name": "SinglePlayer",
                "value": 100.0,
            },
        )

        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["count"] == 1
        assert len(data["data"]) == 1
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["has_prev"] is False

    async def test_pagination_last_page_has_no_next(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        run_runs_board: Board,
        test_device: Device,
    ) -> None:
        """Test that last page has has_next=False and no next_cursor."""
        # Create exactly 25 scores
        for i in range(25):
            await authenticated_client.post(
                "/scores",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(run_runs_board.game_id),
                    "board_id": str(run_runs_board.id),
                    "device_id": str(test_device.id),
                    "player_name": f"Player{i}",
                    "value": float(100 + i),
                },
            )

        # Get first page (20 items)
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}&limit=20"
        )
        page1 = response.json()
        assert page1["pagination"]["has_next"] is True

        # Get second page (should be last page with 5 items)
        cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}&limit=20&cursor={cursor}"
        )
        page2 = response.json()

        assert page2["pagination"]["count"] == 5
        assert page2["pagination"]["has_next"] is False
        assert page2["pagination"]["next_cursor"] is None
        assert page2["pagination"]["has_prev"] is True

    async def test_pagination_with_filters(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        run_runs_board: Board,
        test_device: Device,
    ) -> None:
        """Test pagination works correctly with filters."""
        device1 = str(test_device.id)  # Use the DeviceID, not the plain device_id string
        device2 = "dev_" + "2" * 32  # Different device (placeholder DeviceID)

        # Create 10 scores for device1
        for i in range(10):
            await authenticated_client.post(
                "/scores",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(run_runs_board.game_id),
                    "board_id": str(run_runs_board.id),
                    "device_id": device1,
                    "player_name": f"Player{i}",
                    "value": float(100 + i),
                },
            )

        # Create 10 scores for device2
        for i in range(10):
            await authenticated_client.post(
                "/scores",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(run_runs_board.game_id),
                    "board_id": str(run_runs_board.id),
                    "device_id": device2,
                    "player_name": f"Player{i}",
                    "value": float(200 + i),
                },
            )

        # Get scores filtered by device1
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}&device_id={device1}"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["count"] == 10
        # Verify all scores are from device1
        for score in data["data"]:
            assert score["device_id"] == device1

    async def test_pagination_default_sort_uses_board_sort_direction_descending(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        run_runs_board: Board,
        test_device: Device,
    ) -> None:
        """Test that default sort uses board.sort_direction (DESCENDING - high scores first)."""
        # Create scores with different values in mixed order
        values = [100, 500, 300, 800, 200]
        for i, value in enumerate(values):
            await authenticated_client.post(
                "/scores",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(run_runs_board.game_id),
                    "board_id": str(run_runs_board.id),
                    "device_id": str(test_device.id),
                    "player_name": f"Player{i}",
                    "value": float(value),
                },
            )

        # Get scores without explicit sort - should use board's sort_direction
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}"
        )
        assert response.status_code == 200
        data = response.json()

        # test_board has DESCENDING sort_direction, so should be sorted high to low
        scores = data["data"]
        assert len(scores) == 5
        score_values = [s["value"] for s in scores]
        assert score_values == [800, 500, 300, 200, 100]

    async def test_pagination_explicit_sort_overrides_board_default(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        run_runs_board: Board,
        test_device: Device,
    ) -> None:
        """Test that explicit sort param overrides board's default sort_direction."""
        # Create scores with different values
        values = [100, 500, 300, 800, 200]
        for i, value in enumerate(values):
            await authenticated_client.post(
                "/scores",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(run_runs_board.game_id),
                    "board_id": str(run_runs_board.id),
                    "device_id": str(test_device.id),
                    "player_name": f"Player{i}",
                    "value": float(value),
                },
            )

        # Get scores with explicit ascending sort (even though board is DESCENDING)
        response = await authenticated_client.get(
            f"/scores?account_id={str(test_account.id)}&board_id={str(run_runs_board.id)}&sort=value:asc"
        )
        assert response.status_code == 200
        data = response.json()

        # Should be sorted low to high because of explicit sort
        scores = data["data"]
        assert len(scores) == 5
        score_values = [s["value"] for s in scores]
        assert score_values == [100, 200, 300, 500, 800]
