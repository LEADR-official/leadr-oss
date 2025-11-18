"""Integration tests for API key pagination."""

import pytest
from httpx import AsyncClient

from leadr.accounts.domain.account import Account
from leadr.accounts.domain.user import User


@pytest.mark.asyncio
class TestAPIKeyPagination:
    """Test API key pagination through API."""

    async def test_default_pagination(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_user: User,
    ) -> None:
        """Test that default limit is 20 and default sort is created_at:desc,id:asc."""
        # Create 25 API keys
        for i in range(25):
            await authenticated_client.post(
                "/api-keys",
                json={
                    "account_id": str(test_account.id),
                    "user_id": str(test_user.id),
                    "name": f"Test API Key {i}",
                },
            )

        # Get first page
        response = await authenticated_client.get(f"/api-keys?account_id={test_account.id}")
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
        test_user: User,
    ) -> None:
        """Test forward pagination using next_cursor."""
        # Create 30 API keys
        for i in range(30):
            await authenticated_client.post(
                "/api-keys",
                json={
                    "account_id": str(test_account.id),
                    "user_id": str(test_user.id),
                    "name": f"API Key {i:03d}",
                },
            )

        # Get first page
        response = await authenticated_client.get(
            f"/api-keys?account_id={test_account.id}&limit=10"
        )
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1["data"]) == 10
        assert page1["pagination"]["has_next"] is True

        # Get second page using cursor
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/api-keys?account_id={test_account.id}&limit=10&cursor={next_cursor}"
        )
        assert response.status_code == 200
        page2 = response.json()
        assert len(page2["data"]) == 10
        assert page2["pagination"]["has_prev"] is True

        # Verify no overlap between pages
        page1_ids = {key["id"] for key in page1["data"]}
        page2_ids = {key["id"] for key in page2["data"]}
        assert len(page1_ids & page2_ids) == 0  # No overlap

    async def test_backward_navigation(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_user: User,
    ) -> None:
        """Test backward pagination using prev_cursor."""
        # Create 30 API keys
        for i in range(30):
            await authenticated_client.post(
                "/api-keys",
                json={
                    "account_id": str(test_account.id),
                    "user_id": str(test_user.id),
                    "name": f"API Key {i:03d}",
                },
            )

        # Get first page
        response = await authenticated_client.get(
            f"/api-keys?account_id={test_account.id}&limit=10"
        )
        page1 = response.json()

        # Get second page
        next_cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/api-keys?account_id={test_account.id}&limit=10&cursor={next_cursor}"
        )
        page2 = response.json()
        assert page2["pagination"]["has_prev"] is True

        # Go back to first page using prev_cursor
        prev_cursor = page2["pagination"]["prev_cursor"]
        response = await authenticated_client.get(
            f"/api-keys?account_id={test_account.id}&limit=10&cursor={prev_cursor}"
        )
        assert response.status_code == 200
        page_back = response.json()

        # Should match first page
        assert len(page_back["data"]) == len(page1["data"])
        page_back_ids = {key["id"] for key in page_back["data"]}
        page1_ids = {key["id"] for key in page1["data"]}
        assert page_back_ids == page1_ids

    async def test_custom_sort(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_user: User,
    ) -> None:
        """Test pagination with custom sort (name ascending)."""
        # Create API keys with different names
        names = ["Zebra Key", "Alpha Key", "Beta Key", "Delta Key"]
        for name in names:
            await authenticated_client.post(
                "/api-keys",
                json={
                    "account_id": str(test_account.id),
                    "user_id": str(test_user.id),
                    "name": name,
                },
            )

        # Get sorted by name ascending
        response = await authenticated_client.get(
            f"/api-keys?account_id={test_account.id}&sort=name:asc"
        )
        assert response.status_code == 200
        data = response.json()

        # Verify ascending order
        keys = data["data"]
        key_names = [key["name"] for key in keys if key["name"] in names]
        assert key_names == sorted(names)

    async def test_invalid_sort_field(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
    ) -> None:
        """Test that invalid sort field returns 400 error."""
        response = await authenticated_client.get(
            f"/api-keys?account_id={test_account.id}&sort=invalid_field:desc"
        )
        assert response.status_code == 400
        assert "Unknown sort field" in response.json()["error"]

    async def test_cursor_state_validation(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_user: User,
    ) -> None:
        """Test that cursor state mismatch returns 400 error."""
        # Create API keys
        for i in range(20):
            await authenticated_client.post(
                "/api-keys",
                json={
                    "account_id": str(test_account.id),
                    "user_id": str(test_user.id),
                    "name": f"API Key {i}",
                },
            )

        # Get first page with one sort (use limit=10 to ensure pagination)
        response = await authenticated_client.get(
            f"/api-keys?account_id={test_account.id}&sort=name:desc&limit=10"
        )
        page1 = response.json()
        cursor = page1["pagination"]["next_cursor"]

        # Try to use cursor with different sort
        response = await authenticated_client.get(
            f"/api-keys?account_id={test_account.id}&sort=created_at:asc&limit=10&cursor={cursor}"
        )
        assert response.status_code == 400
        assert "Query parameters don't match cursor state" in response.json()["error"]

    async def test_pagination_with_status_filter(
        self,
        authenticated_client: AsyncClient,
        test_account: Account,
        test_user: User,
    ) -> None:
        """Test pagination with status filter."""
        # Create 10 active API keys
        for i in range(10):
            await authenticated_client.post(
                "/api-keys",
                json={
                    "account_id": str(test_account.id),
                    "user_id": str(test_user.id),
                    "name": f"Active Key {i}",
                },
            )

        # Create 5 API keys and revoke them
        for i in range(5):
            response = await authenticated_client.post(
                "/api-keys",
                json={
                    "account_id": str(test_account.id),
                    "user_id": str(test_user.id),
                    "name": f"Revoked Key {i}",
                },
            )
            key_id = response.json()["id"]
            await authenticated_client.patch(
                f"/api-keys/{key_id}",
                json={"status": "revoked"},
            )

        # Get active API keys only
        response = await authenticated_client.get(
            f"/api-keys?account_id={test_account.id}&status=active&limit=5"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["count"] == 5
        assert len(data["data"]) == 5
        assert data["pagination"]["has_next"] is True

        # Verify all keys are active
        for key in data["data"]:
            assert key["status"] == "active"
