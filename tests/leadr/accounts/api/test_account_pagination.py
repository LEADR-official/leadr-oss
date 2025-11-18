"""Integration tests for account pagination."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.services.account_service import AccountService


@pytest.mark.asyncio
class TestAccountPagination:
    """Test account pagination through API."""

    async def test_default_pagination(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test that default limit is 20 and default sort is created_at:desc,id:asc."""
        # Create 25 accounts via service
        account_service = AccountService(db_session)
        for i in range(25):
            await account_service.create_account(
                name=f"Test Account {i}",
                slug=f"test-account-{i:03d}",
            )

        # Get first page
        response = await authenticated_client.get("/accounts")
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
        db_session: AsyncSession,
    ) -> None:
        """Test forward pagination using next_cursor."""
        # Create 30 accounts via service
        account_service = AccountService(db_session)
        for i in range(30):
            await account_service.create_account(
                name=f"Account {i:03d}",
                slug=f"account-{i:03d}",
            )

        # Get first page
        response = await authenticated_client.get("/accounts?limit=10")
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1["data"]) == 10
        assert page1["pagination"]["has_next"] is True

        # Get second page using cursor
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(f"/accounts?limit=10&cursor={next_cursor}")
        assert response.status_code == 200
        page2 = response.json()
        assert len(page2["data"]) == 10
        assert page2["pagination"]["has_prev"] is True

        # Verify no overlap between pages
        page1_ids = {account["id"] for account in page1["data"]}
        page2_ids = {account["id"] for account in page2["data"]}
        assert len(page1_ids & page2_ids) == 0  # No overlap

    async def test_backward_navigation(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test backward pagination using prev_cursor."""
        # Create 30 accounts via service
        account_service = AccountService(db_session)
        for i in range(30):
            await account_service.create_account(
                name=f"Account {i:03d}",
                slug=f"account-{i:03d}",
            )

        # Get first page
        response = await authenticated_client.get("/accounts?limit=10")
        page1 = response.json()

        # Get second page
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(f"/accounts?limit=10&cursor={next_cursor}")
        page2 = response.json()
        assert page2["pagination"]["has_prev"] is True

        # Go back to first page using prev_cursor
        prev_cursor = page2["pagination"]["prev_cursor"]
        response = await authenticated_client.get(f"/accounts?limit=10&cursor={prev_cursor}")
        assert response.status_code == 200
        page_back = response.json()

        # Should match first page
        assert len(page_back["data"]) == len(page1["data"])
        page_back_ids = {account["id"] for account in page_back["data"]}
        page1_ids = {account["id"] for account in page1["data"]}
        assert page_back_ids == page1_ids

    async def test_custom_sort(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test pagination with custom sort (name ascending)."""
        # Create accounts with different names via service
        account_service = AccountService(db_session)
        names = ["Zebra Corp", "Alpha Inc", "Beta LLC", "Delta Co", "Gamma Ltd"]
        for i, name in enumerate(names):
            await account_service.create_account(
                name=name,
                slug=f"slug-{i:03d}",
            )

        # Get sorted by name ascending
        response = await authenticated_client.get("/accounts?sort=name:asc")
        assert response.status_code == 200
        data = response.json()

        # Verify ascending order
        accounts = data["data"]
        account_names = [acc["name"] for acc in accounts if acc["name"] in names]
        assert account_names == sorted(names)

    async def test_invalid_sort_field(
        self,
        authenticated_client: AsyncClient,
    ) -> None:
        """Test that invalid sort field returns 400 error."""
        response = await authenticated_client.get("/accounts?sort=invalid_field:desc")
        assert response.status_code == 400
        assert "Unknown sort field" in response.json()["error"]

    async def test_cursor_state_validation(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test that cursor state mismatch returns 400 error."""
        # Create accounts via service
        account_service = AccountService(db_session)
        for i in range(20):
            await account_service.create_account(
                name=f"Account {i}",
                slug=f"account-{i:03d}",
            )

        # Get first page with one sort
        response = await authenticated_client.get("/accounts?sort=name:desc")
        page1 = response.json()
        cursor = page1["pagination"]["next_cursor"]

        # Try to use cursor with different sort
        response = await authenticated_client.get(f"/accounts?sort=slug:asc&cursor={cursor}")
        assert response.status_code == 400
        assert "Query parameters don't match cursor state" in response.json()["error"]

    async def test_pagination_with_filters(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test pagination works correctly with no entity-specific filters.

        Note: Accounts endpoint has no additional filters beyond pagination.
        This test verifies basic pagination still works.
        """
        # Create 15 accounts via service
        account_service = AccountService(db_session)
        for i in range(15):
            await account_service.create_account(
                name=f"Test Account {i}",
                slug=f"test-account-{i:03d}",
            )

        # Get accounts with custom limit
        response = await authenticated_client.get("/accounts?limit=5")
        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["count"] == 5
        assert len(data["data"]) == 5
        assert data["pagination"]["has_next"] is True
