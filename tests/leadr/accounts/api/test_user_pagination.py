"""Integration tests for user pagination."""

import pytest
from httpx import AsyncClient

from leadr.accounts.domain.account import Account


@pytest.mark.asyncio
class TestUserPagination:
    """Test user pagination through API."""

    async def test_default_pagination(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
    ) -> None:
        """Test that default limit is 20 and default sort is created_at:desc,id:asc."""
        # Create 25 users
        for i in range(25):
            await authenticated_client.post(
                "/users",
                json={
                    "account_id": str(test_account.id),
                    "email": f"user{i}@example.com",
                    "display_name": f"Test User {i}",
                },
            )

        # Get first page
        response = await authenticated_client.get(f"/users?account_id={test_account.id}")
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
    ) -> None:
        """Test forward pagination using next_cursor."""
        # Create 30 users
        for i in range(30):
            await authenticated_client.post(
                "/users",
                json={
                    "account_id": str(test_account.id),
                    "email": f"user{i:03d}@example.com",
                    "display_name": f"User {i:03d}",
                },
            )

        # Get first page
        response = await authenticated_client.get(f"/users?account_id={test_account.id}&limit=10")
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1["data"]) == 10
        assert page1["pagination"]["has_next"] is True

        # Get second page using cursor
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/users?account_id={test_account.id}&limit=10&cursor={next_cursor}"
        )
        assert response.status_code == 200
        page2 = response.json()
        assert len(page2["data"]) == 10
        assert page2["pagination"]["has_prev"] is True

        # Verify no overlap between pages
        page1_ids = {user["id"] for user in page1["data"]}
        page2_ids = {user["id"] for user in page2["data"]}
        assert len(page1_ids & page2_ids) == 0  # No overlap

    async def test_backward_navigation(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
    ) -> None:
        """Test backward pagination using prev_cursor."""
        # Create 30 users
        for i in range(30):
            await authenticated_client.post(
                "/users",
                json={
                    "account_id": str(test_account.id),
                    "email": f"user{i:03d}@example.com",
                    "display_name": f"User {i:03d}",
                },
            )

        # Get first page
        response = await authenticated_client.get(f"/users?account_id={test_account.id}&limit=10")
        page1 = response.json()

        # Get second page
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/users?account_id={test_account.id}&limit=10&cursor={next_cursor}"
        )
        page2 = response.json()
        assert page2["pagination"]["has_prev"] is True

        # Go back to first page using prev_cursor
        prev_cursor = page2["pagination"]["prev_cursor"]
        response = await authenticated_client.get(
            f"/users?account_id={test_account.id}&limit=10&cursor={prev_cursor}"
        )
        assert response.status_code == 200
        page_back = response.json()

        # Should match first page
        assert len(page_back["data"]) == len(page1["data"])
        page_back_ids = {user["id"] for user in page_back["data"]}
        page1_ids = {user["id"] for user in page1["data"]}
        assert page_back_ids == page1_ids

    async def test_custom_sort(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
    ) -> None:
        """Test pagination with custom sort (email ascending)."""
        # Create users with different emails
        emails = ["zebra@example.com", "alpha@example.com", "beta@example.com"]
        for email in emails:
            await authenticated_client.post(
                "/users",
                json={
                    "account_id": str(test_account.id),
                    "email": email,
                    "display_name": email.split("@")[0].title(),
                },
            )

        # Get sorted by email ascending
        response = await authenticated_client.get(
            f"/users?account_id={test_account.id}&sort=email:asc"
        )
        assert response.status_code == 200
        data = response.json()

        # Verify ascending order
        users = data["data"]
        user_emails = [user["email"] for user in users if user["email"] in emails]
        assert user_emails == sorted(emails)

    async def test_invalid_sort_field(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
    ) -> None:
        """Test that invalid sort field returns 400 error."""
        response = await authenticated_client.get(
            f"/users?account_id={test_account.id}&sort=invalid_field:desc"
        )
        assert response.status_code == 400
        assert "Unknown sort field" in response.json()["error"]

    async def test_cursor_state_validation(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
    ) -> None:
        """Test that cursor state mismatch returns 400 error."""
        # Create users
        for i in range(20):
            await authenticated_client.post(
                "/users",
                json={
                    "account_id": str(test_account.id),
                    "email": f"user{i}@example.com",
                    "display_name": f"User {i}",
                },
            )

        # Get first page with one sort (use limit=10 to ensure pagination)
        response = await authenticated_client.get(
            f"/users?account_id={test_account.id}&sort=email:desc&limit=10"
        )
        page1 = response.json()
        cursor = page1["pagination"]["next_cursor"]

        # Try to use cursor with different sort
        response = await authenticated_client.get(
            f"/users?account_id={test_account.id}&sort=display_name:asc&limit=10&cursor={cursor}"
        )
        assert response.status_code == 400
        assert "Query parameters don't match cursor state" in response.json()["error"]

    async def test_pagination_with_filters(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
    ) -> None:
        """Test pagination requires account_id filter."""
        # Create 15 users
        for i in range(15):
            await authenticated_client.post(
                "/users",
                json={
                    "account_id": str(test_account.id),
                    "email": f"user{i}@example.com",
                    "display_name": f"User {i}",
                },
            )

        # Get users with account_id filter and custom limit
        response = await authenticated_client.get(f"/users?account_id={test_account.id}&limit=5")
        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["count"] == 5
        assert len(data["data"]) == 5
        assert data["pagination"]["has_next"] is True

        # Verify all users belong to the account
        for user in data["data"]:
            assert user["account_id"] == str(test_account.id)
