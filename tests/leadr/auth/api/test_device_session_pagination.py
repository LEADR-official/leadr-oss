"""Integration tests for device session pagination."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account
from leadr.auth.services.device_service import DeviceService
from leadr.games.domain.game import Game


@pytest.mark.asyncio
class TestDeviceSessionPagination:
    """Test device session pagination through API."""

    async def test_default_pagination(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
        db_session: AsyncSession,
    ) -> None:
        """Test that default limit is 20 and default sort is created_at:desc,id:asc."""
        # Create 25 device sessions via start_session
        device_service = DeviceService(db_session)
        for i in range(25):
            await device_service.start_session(
                game_id=test_game.id,
                device_id=f"device-{i:03d}",
                platform="ios",
            )

        # Get first page
        response = await authenticated_client.get(f"/device-sessions?account_id={test_account.id}")
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
        # Create 30 device sessions
        device_service = DeviceService(db_session)
        for i in range(30):
            await device_service.start_session(
                game_id=test_game.id,
                device_id=f"device-{i:03d}",
                platform="android",
            )

        # Get first page
        response = await authenticated_client.get(
            f"/device-sessions?account_id={test_account.id}&limit=10"
        )
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1["data"]) == 10
        assert page1["pagination"]["has_next"] is True

        # Get second page using cursor
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/device-sessions?account_id={test_account.id}&limit=10&cursor={next_cursor}"
        )
        assert response.status_code == 200
        page2 = response.json()
        assert len(page2["data"]) == 10
        assert page2["pagination"]["has_prev"] is True

        # Verify no overlap between pages
        page1_ids = {session["id"] for session in page1["data"]}
        page2_ids = {session["id"] for session in page2["data"]}
        assert len(page1_ids & page2_ids) == 0  # No overlap

    async def test_backward_navigation(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
        db_session: AsyncSession,
    ) -> None:
        """Test backward pagination using prev_cursor."""
        # Create 30 device sessions
        device_service = DeviceService(db_session)
        for i in range(30):
            await device_service.start_session(
                game_id=test_game.id,
                device_id=f"device-{i:03d}",
                platform="web",
            )

        # Get first page
        response = await authenticated_client.get(
            f"/device-sessions?account_id={test_account.id}&limit=10"
        )
        page1 = response.json()

        # Get second page
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/device-sessions?account_id={test_account.id}&limit=10&cursor={next_cursor}"
        )
        page2 = response.json()
        assert page2["pagination"]["has_prev"] is True

        # Go back to first page using prev_cursor
        prev_cursor = page2["pagination"]["prev_cursor"]
        response = await authenticated_client.get(
            f"/device-sessions?account_id={test_account.id}&limit=10&cursor={prev_cursor}"
        )
        assert response.status_code == 200
        page_back = response.json()

        # Should match first page
        assert len(page_back["data"]) == len(page1["data"])
        page_back_ids = {session["id"] for session in page_back["data"]}
        page1_ids = {session["id"] for session in page1["data"]}
        assert page_back_ids == page1_ids

    async def test_custom_sort(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
        db_session: AsyncSession,
    ) -> None:
        """Test pagination with custom sort (created_at ascending)."""
        # Create device sessions with different timestamps
        device_service = DeviceService(db_session)
        for i in range(5):
            await device_service.start_session(
                game_id=test_game.id,
                device_id=f"device-{i:03d}",
                platform="ios",
            )

        # Get sorted by created_at ascending
        response = await authenticated_client.get(
            f"/device-sessions?account_id={test_account.id}&sort=created_at:asc"
        )
        assert response.status_code == 200
        data = response.json()

        # Verify ascending order by timestamps
        sessions = data["data"]
        assert len(sessions) == 5
        for i in range(len(sessions) - 1):
            assert sessions[i]["created_at"] <= sessions[i + 1]["created_at"]

    async def test_invalid_sort_field(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
    ) -> None:
        """Test that invalid sort field returns 400 error."""
        response = await authenticated_client.get(
            f"/device-sessions?account_id={test_account.id}&sort=invalid_field:desc"
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
        # Create device sessions
        device_service = DeviceService(db_session)
        for i in range(20):
            await device_service.start_session(
                game_id=test_game.id,
                device_id=f"device-{i:03d}",
                platform="ios",
            )

        # Get first page with one sort
        response = await authenticated_client.get(
            f"/device-sessions?account_id={test_account.id}&sort=created_at:desc&limit=10"
        )
        page1 = response.json()
        cursor = page1["pagination"]["next_cursor"]

        # Try to use cursor with different sort
        response = await authenticated_client.get(
            f"/device-sessions?account_id={test_account.id}&sort=id:asc&cursor={cursor}"
        )
        assert response.status_code == 400
        assert "Query parameters don't match cursor state" in response.json()["error"]

    async def test_pagination_with_device_filter(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_game: Game,
        db_session: AsyncSession,
    ) -> None:
        """Test pagination with device_id filter."""
        device_service = DeviceService(db_session)

        # Create 10 sessions for first device
        device1, _, _, _ = await device_service.start_session(
            game_id=test_game.id,
            device_id="primary-device",
            platform="ios",
        )
        for _i in range(9):
            await device_service.start_session(
                game_id=test_game.id,
                device_id="primary-device",
                platform="ios",
            )

        # Create 5 sessions for second device
        for _i in range(5):
            await device_service.start_session(
                game_id=test_game.id,
                device_id="secondary-device",
                platform="android",
            )

        # Get sessions filtered by first device
        response = await authenticated_client.get(
            f"/device-sessions?account_id={test_account.id}&device_id={device1.id}&limit=5"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["count"] == 5
        assert len(data["data"]) == 5
        assert data["pagination"]["has_next"] is True

        # Verify all sessions belong to device1
        for session in data["data"]:
            assert session["device_id"] == str(device1.id)
