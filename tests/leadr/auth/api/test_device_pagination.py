"""Integration tests for device pagination."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account
from leadr.auth.services.device_service import DeviceService
from leadr.common.domain.ids import GameID
from leadr.games.domain.game import Game


@pytest.mark.asyncio
class TestDevicePagination:
    """Test device pagination through API."""

    async def test_default_pagination(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
        db_session: AsyncSession,
    ) -> None:
        """Test that default limit is 20 and default sort is created_at:desc,id:asc."""
        # Create 25 devices via start_session
        device_service = DeviceService(db_session)
        for i in range(25):
            await device_service.get_or_create_device(
                game_id=test_game.id,
                client_fingerprint=f"{i:064x}",
                platform="ios",
            )

        # Get first page
        response = await authenticated_client.get(f"/devices?account_id={test_account.id}")
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
        db_session: AsyncSession,
    ) -> None:
        """Test forward pagination using next_cursor."""
        # Create 30 devices
        device_service = DeviceService(db_session)
        for i in range(30):
            await device_service.get_or_create_device(
                game_id=test_game.id,
                client_fingerprint=f"{i:064x}",
                platform="android",
            )

        # Get first page
        response = await authenticated_client.get(f"/devices?account_id={test_account.id}&limit=10")
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1["data"]) == 10
        assert page1["pagination"]["has_next"] is True

        # Get second page using cursor
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/devices?account_id={test_account.id}&limit=10&cursor={next_cursor}"
        )
        assert response.status_code == 200
        page2 = response.json()
        assert len(page2["data"]) == 10
        assert page2["pagination"]["has_prev"] is True

        # Verify no overlap between pages
        page1_ids = {device["id"] for device in page1["data"]}
        page2_ids = {device["id"] for device in page2["data"]}
        assert len(page1_ids & page2_ids) == 0  # No overlap

    async def test_backward_navigation(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
        db_session: AsyncSession,
    ) -> None:
        """Test backward pagination using prev_cursor."""
        # Create 30 devices
        device_service = DeviceService(db_session)
        for i in range(30):
            await device_service.get_or_create_device(
                game_id=test_game.id,
                client_fingerprint=f"{i:064x}",
                platform="web",
            )

        # Get first page
        response = await authenticated_client.get(f"/devices?account_id={test_account.id}&limit=10")
        page1 = response.json()

        # Get second page
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/devices?account_id={test_account.id}&limit=10&cursor={next_cursor}"
        )
        page2 = response.json()
        assert page2["pagination"]["has_prev"] is True

        # Go back to first page using prev_cursor
        prev_cursor = page2["pagination"]["prev_cursor"]
        response = await authenticated_client.get(
            f"/devices?account_id={test_account.id}&limit=10&cursor={prev_cursor}"
        )
        assert response.status_code == 200
        page_back = response.json()

        # Should match first page
        assert len(page_back["data"]) == len(page1["data"])
        page_back_ids = {device["id"] for device in page_back["data"]}
        page1_ids = {device["id"] for device in page1["data"]}
        assert page_back_ids == page1_ids

    async def test_custom_sort(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
        db_session: AsyncSession,
    ) -> None:
        """Test pagination with custom sort (platform ascending)."""
        # Create devices with different platforms
        device_service = DeviceService(db_session)
        platforms = ["ios", "android", "web", "windows"]
        for i, platform in enumerate(platforms):
            await device_service.get_or_create_device(
                game_id=test_game.id,
                client_fingerprint=f"{i:064x}",
                platform=platform,
            )

        # Get sorted by platform ascending
        response = await authenticated_client.get(
            f"/devices?account_id={test_account.id}&sort=platform:asc"
        )
        assert response.status_code == 200
        data = response.json()

        # Verify ascending order
        devices = data["data"]
        device_platforms = [
            device["platform"] for device in devices if device["platform"] in platforms
        ]
        assert device_platforms == sorted(platforms)

    async def test_invalid_sort_field(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
    ) -> None:
        """Test that invalid sort field returns 400 error."""
        response = await authenticated_client.get(
            f"/devices?account_id={test_account.id}&sort=invalid_field:desc"
        )
        assert response.status_code == 400
        assert "Unknown sort field" in response.json()["error"]

    async def test_cursor_state_validation(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
        db_session: AsyncSession,
    ) -> None:
        """Test that cursor state mismatch returns 400 error."""
        # Create devices
        device_service = DeviceService(db_session)
        for i in range(20):
            await device_service.get_or_create_device(
                game_id=test_game.id,
                client_fingerprint=f"{i:064x}",
                platform="ios",
            )

        # Get first page with one sort
        response = await authenticated_client.get(
            f"/devices?account_id={test_account.id}&sort=platform:desc&limit=10"
        )
        page1 = response.json()
        cursor = page1["pagination"]["next_cursor"]

        # Try to use cursor with different sort
        response = await authenticated_client.get(
            f"/devices?account_id={test_account.id}&sort=created_at:asc&cursor={cursor}"
        )
        assert response.status_code == 400
        assert "Query parameters don't match cursor state" in response.json()["error"]

    async def test_pagination_with_game_filter(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
        db_session: AsyncSession,
    ) -> None:
        """Test pagination with game_id filter."""
        # Create second game
        response = await authenticated_client.post(
            "/games",
            json={
                "account_id": str(test_account.id),
                "name": "Second Game",
            },
        )
        second_game_data = response.json()
        second_game_id = GameID(second_game_data["id"])

        # Create 10 devices for test_game
        device_service = DeviceService(db_session)
        for i in range(10):
            await device_service.get_or_create_device(
                game_id=test_game.id,
                client_fingerprint=f"{i + 100:064x}",  # Offset to avoid collisions
                platform="ios",
            )

        # Create 5 devices for second_game
        for i in range(5):
            await device_service.get_or_create_device(
                game_id=second_game_id,
                client_fingerprint=f"{i + 200:064x}",  # Different offset
                platform="android",
            )

        # Get devices filtered by test_game
        response = await authenticated_client.get(
            f"/devices?account_id={test_account.id}&game_id={test_game.id}&limit=5"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["count"] == 5
        assert len(data["data"]) == 5
        assert data["pagination"]["has_next"] is True

        # Verify all devices belong to test_game
        for device in data["data"]:
            assert device["game_id"] == str(test_game.id)

    async def test_pagination_with_status_filter(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
        db_session: AsyncSession,
    ) -> None:
        """Test pagination with status filter."""
        # Create 10 devices (all start as active)
        device_service = DeviceService(db_session)
        device_ids = []
        for i in range(10):
            device = await device_service.get_or_create_device(
                game_id=test_game.id,
                client_fingerprint=f"{i:064x}",
                platform="ios",
            )
            device_ids.append(device.id)

        # Ban 5 devices
        for i in range(5):
            await device_service.ban_device(device_ids[i])

        # Get active devices only
        response = await authenticated_client.get(
            f"/devices?account_id={test_account.id}&status=active&limit=5"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["count"] == 5
        assert len(data["data"]) == 5
        # Note: has_next would be False since there are exactly 5 active devices

        # Verify all devices are active
        for device in data["data"]:
            assert device["status"] == "active"
