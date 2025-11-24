"""Integration tests for board template pagination."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from leadr.accounts.domain.account import Account
from leadr.games.domain.game import Game


@pytest.mark.asyncio
class TestBoardTemplatePagination:
    """Test board template pagination through API."""

    async def test_default_pagination(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
    ) -> None:
        """Test that default limit is 20 and default sort is created_at:desc,id:asc."""
        # Create 25 board templates
        for i in range(25):
            await authenticated_client.post(
                "/board-templates",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(test_game.id),
                    "name": f"Test Template {i}",
                    "slug": f"test-template-{i}",
                    "repeat_interval": "1 week",
                    "next_run_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                    "is_active": True,
                    "config": {},
                },
            )

        # Get first page
        response = await authenticated_client.get(f"/board-templates?account_id={test_account.id}")
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
        # Create 30 templates
        for i in range(30):
            await authenticated_client.post(
                "/board-templates",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(test_game.id),
                    "name": f"Template {i:03d}",
                    "slug": f"template-{i:03d}",
                    "repeat_interval": "1 week",
                    "next_run_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                    "is_active": True,
                    "config": {},
                },
            )

        # Get first page
        response = await authenticated_client.get(
            f"/board-templates?account_id={test_account.id}&limit=10"
        )
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1["data"]) == 10
        assert page1["pagination"]["has_next"] is True

        # Get second page using cursor
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/board-templates?account_id={test_account.id}&limit=10&cursor={next_cursor}"
        )
        assert response.status_code == 200
        page2 = response.json()
        assert len(page2["data"]) == 10
        assert page2["pagination"]["has_prev"] is True

        # Verify no overlap between pages
        page1_ids = {template["id"] for template in page1["data"]}
        page2_ids = {template["id"] for template in page2["data"]}
        assert len(page1_ids & page2_ids) == 0  # No overlap

    async def test_backward_navigation(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
    ) -> None:
        """Test backward pagination using prev_cursor."""
        # Create 30 templates
        for i in range(30):
            await authenticated_client.post(
                "/board-templates",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(test_game.id),
                    "name": f"Template {i:03d}",
                    "slug": f"template-{i:03d}",
                    "repeat_interval": "1 week",
                    "next_run_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                    "is_active": True,
                    "config": {},
                },
            )

        # Get first page
        response = await authenticated_client.get(
            f"/board-templates?account_id={test_account.id}&limit=10"
        )
        page1 = response.json()

        # Get second page
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/board-templates?account_id={test_account.id}&limit=10&cursor={next_cursor}"
        )
        page2 = response.json()
        assert page2["pagination"]["has_prev"] is True

        # Go back to first page using prev_cursor
        prev_cursor = page2["pagination"]["prev_cursor"]
        response = await authenticated_client.get(
            f"/board-templates?account_id={test_account.id}&limit=10&cursor={prev_cursor}"
        )
        assert response.status_code == 200
        page_back = response.json()

        # Should match first page
        assert len(page_back["data"]) == len(page1["data"])
        page_back_ids = {template["id"] for template in page_back["data"]}
        page1_ids = {template["id"] for template in page1["data"]}
        assert page_back_ids == page1_ids

    async def test_custom_sort(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
    ) -> None:
        """Test pagination with custom sort (name ascending)."""
        # Create templates with different names
        names = ["Zombie Weekly", "Arena Monthly", "Card Daily", "Dragon Seasonal"]
        slugs = ["zombie-weekly", "arena-monthly", "card-daily", "dragon-seasonal"]
        for name, slug in zip(names, slugs, strict=True):
            await authenticated_client.post(
                "/board-templates",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(test_game.id),
                    "name": name,
                    "slug": slug,
                    "repeat_interval": "1 week",
                    "next_run_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                    "is_active": True,
                    "config": {},
                },
            )

        # Get sorted by name ascending
        response = await authenticated_client.get(
            f"/board-templates?account_id={test_account.id}&sort=name:asc"
        )
        assert response.status_code == 200
        data = response.json()

        # Verify ascending order
        templates = data["data"]
        template_names = [template["name"] for template in templates if template["name"] in names]
        assert template_names == sorted(names)

    async def test_invalid_sort_field(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
    ) -> None:
        """Test that invalid sort field returns 400 error."""
        response = await authenticated_client.get(
            f"/board-templates?account_id={test_account.id}&sort=invalid_field:desc"
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
        # Create templates
        for i in range(20):
            await authenticated_client.post(
                "/board-templates",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(test_game.id),
                    "name": f"Template {i}",
                    "slug": f"template-{i}",
                    "repeat_interval": "1 week",
                    "next_run_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                    "is_active": True,
                    "config": {},
                },
            )

        # Get first page with one sort
        response = await authenticated_client.get(
            f"/board-templates?account_id={test_account.id}&sort=name:desc&limit=10"
        )
        page1 = response.json()
        cursor = page1["pagination"]["next_cursor"]

        # Try to use cursor with different sort
        response = await authenticated_client.get(
            f"/board-templates?account_id={test_account.id}&sort=created_at:asc&limit=10&cursor={cursor}"
        )
        assert response.status_code == 400
        assert "Query parameters don't match cursor state" in response.json()["error"]

    async def test_pagination_with_game_filter(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
    ) -> None:
        """Test pagination with game_id filter."""
        # Create second game
        response = await authenticated_client.post(
            "/games",
            json={
                "account_id": str(test_account.id),
                "name": "Second Game",
                "slug": "second-game",
            },
        )
        second_game_id = response.json()["id"]

        # Create 10 templates for test_game
        for i in range(10):
            await authenticated_client.post(
                "/board-templates",
                json={
                    "account_id": str(test_account.id),
                    "game_id": str(test_game.id),
                    "name": f"Game1 Template {i}",
                    "slug": f"game1-template-{i}",
                    "repeat_interval": "1 week",
                    "next_run_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                    "is_active": True,
                    "config": {},
                },
            )

        # Create 5 templates for second_game
        for i in range(5):
            await authenticated_client.post(
                "/board-templates",
                json={
                    "account_id": str(test_account.id),
                    "game_id": second_game_id,
                    "name": f"Game2 Template {i}",
                    "slug": f"game2-template-{i}",
                    "repeat_interval": "1 week",
                    "next_run_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                    "is_active": True,
                    "config": {},
                },
            )

        # Get templates filtered by test_game
        response = await authenticated_client.get(
            f"/board-templates?account_id={test_account.id}&game_id={test_game.id}&limit=5"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["count"] == 5
        assert len(data["data"]) == 5
        assert data["pagination"]["has_next"] is True

        # Verify all templates belong to test_game
        for template in data["data"]:
            assert template["game_id"] == str(test_game.id)
