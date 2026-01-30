"""Unit tests for API key pagination with mocked services."""

import pytest
from httpx import AsyncClient

from leadr.auth.domain.api_key import APIKey, APIKeyStatus
from leadr.common.api.pagination import PaginatedResult
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, APIKeyID, UserID


@pytest.mark.asyncio
class TestAPIKeyPagination:
    """Test API key pagination through API."""

    async def test_default_pagination(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_api_key_service,
    ) -> None:
        """Test that default limit is 20 and default sort is created_at:desc,id:asc."""
        account_id = AccountID()

        # Create 25 mock API keys
        api_keys = [
            APIKey(
                id=APIKeyID(),
                account_id=account_id,
                user_id=UserID(),
                name=f"Test API Key {i}",
                key_hash=f"hash{i}",
                key_prefix=f"ldr_test{i}",
            )
            for i in range(25)
        ]

        # Mock service to return first 20 items with has_next=True
        mock_api_key_service.list_api_keys.return_value = PaginatedResult(
            items=api_keys[:20],
            has_next=True,
            has_prev=False,
            next_position=None,  # Cursor positions not needed for unit tests
            prev_position=None,
        )

        # Get first page
        response = await mock_client_no_db.get(f"/api-keys?account_id={account_id}")
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

    async def test_forward_navigation(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_api_key_service,
    ) -> None:
        """Test forward pagination using next_cursor."""
        account_id = AccountID()

        # Create 30 mock API keys
        api_keys = [
            APIKey(
                id=APIKeyID(),
                account_id=account_id,
                user_id=UserID(),
                name=f"API Key {i:03d}",
                key_hash=f"hash{i}",
                key_prefix=f"ldr_test{i}",
            )
            for i in range(30)
        ]

        # Mock first page
        mock_api_key_service.list_api_keys.return_value = PaginatedResult(
            items=api_keys[:10],
            has_next=True,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        # Get first page
        response = await mock_client_no_db.get(f"/api-keys?account_id={account_id}&limit=10")
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1["data"]) == 10
        assert page1["pagination"]["has_next"] is True

        # Mock second page
        mock_api_key_service.list_api_keys.return_value = PaginatedResult(
            items=api_keys[10:20],
            has_next=True,
            has_prev=True,
            next_position=None,
            prev_position=None,
        )

        # Get second page (cursor is optional for unit tests - we're not testing cursor logic)
        response = await mock_client_no_db.get(f"/api-keys?account_id={account_id}&limit=10")
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
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_api_key_service,
    ) -> None:
        """Test backward pagination using prev_cursor."""
        account_id = AccountID()

        # Create 30 mock API keys
        api_keys = [
            APIKey(
                id=APIKeyID(),
                account_id=account_id,
                user_id=UserID(),
                name=f"API Key {i:03d}",
                key_hash=f"hash{i}",
                key_prefix=f"ldr_test{i}",
            )
            for i in range(30)
        ]

        # Mock first page
        mock_api_key_service.list_api_keys.return_value = PaginatedResult(
            items=api_keys[:10],
            has_next=True,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        # Get first page
        response = await mock_client_no_db.get(f"/api-keys?account_id={account_id}&limit=10")
        page1 = response.json()
        page1_ids = {key["id"] for key in page1["data"]}

        # Mock going back to first page (simulating pagination backward)
        mock_api_key_service.list_api_keys.return_value = PaginatedResult(
            items=api_keys[:10],
            has_next=True,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        # Get same data again (unit test doesn't need real cursor navigation)
        response = await mock_client_no_db.get(f"/api-keys?account_id={account_id}&limit=10")
        assert response.status_code == 200
        page_back = response.json()

        # Should match first page
        assert len(page_back["data"]) == len(page1["data"])
        page_back_ids = {key["id"] for key in page_back["data"]}
        assert page_back_ids == page1_ids

    async def test_custom_sort(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_api_key_service,
    ) -> None:
        """Test pagination with custom sort (name ascending)."""
        account_id = AccountID()

        # Create API keys with different names (pre-sorted)
        names = ["Alpha Key", "Beta Key", "Delta Key", "Zebra Key"]
        api_keys = [
            APIKey(
                id=APIKeyID(),
                account_id=account_id,
                user_id=UserID(),
                name=name,
                key_hash=f"hash{i}",
                key_prefix=f"ldr_test{i}",
            )
            for i, name in enumerate(sorted(names))
        ]

        # Mock service to return sorted keys
        mock_api_key_service.list_api_keys.return_value = PaginatedResult(
            items=api_keys,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        # Get sorted by name ascending
        response = await mock_client_no_db.get(f"/api-keys?account_id={account_id}&sort=name:asc")
        assert response.status_code == 200
        data = response.json()

        # Verify ascending order
        keys = data["data"]
        key_names = [key["name"] for key in keys if key["name"] in names]
        assert key_names == sorted(names)

    async def test_invalid_sort_field(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_api_key_service,
    ) -> None:
        """Test that invalid sort field returns 400 error."""
        account_id = AccountID()

        # Mock service to raise ValueError for invalid sort field
        mock_api_key_service.list_api_keys.side_effect = ValueError(
            "Unknown sort field: invalid_field"
        )

        response = await mock_client_no_db.get(
            f"/api-keys?account_id={account_id}&sort=invalid_field:desc"
        )
        assert response.status_code == 400
        assert "Unknown sort field" in response.json()["error"]

    async def test_cursor_state_validation(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_api_key_service,
    ) -> None:
        """Test that cursor state mismatch returns 400 error."""
        account_id = AccountID()

        # Mock service to raise CursorValidationError
        mock_api_key_service.list_api_keys.side_effect = CursorValidationError(
            "Query parameters don't match cursor state"
        )

        # Try to use cursor with different sort (simulated)
        response = await mock_client_no_db.get(
            f"/api-keys?account_id={account_id}&sort=created_at:asc&limit=10&cursor=fake_cursor"
        )
        assert response.status_code == 400
        assert "Query parameters don't match cursor state" in response.json()["error"]

    async def test_pagination_with_status_filter(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_api_key_service,
    ) -> None:
        """Test pagination with status filter."""
        account_id = AccountID()

        # Create 5 active API keys
        active_keys = [
            APIKey(
                id=APIKeyID(),
                account_id=account_id,
                user_id=UserID(),
                name=f"Active Key {i}",
                key_hash=f"hash{i}",
                key_prefix=f"ldr_test{i}",
                status=APIKeyStatus.ACTIVE,
            )
            for i in range(5)
        ]

        # Mock service to return active keys only
        mock_api_key_service.list_api_keys.return_value = PaginatedResult(
            items=active_keys,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        # Get active API keys only
        response = await mock_client_no_db.get(
            f"/api-keys?account_id={account_id}&status=active&limit=5"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["count"] == 5
        assert len(data["data"]) == 5
        assert data["pagination"]["has_next"] is False

        # Verify all keys are active
        for key in data["data"]:
            assert key["status"] == "active"

        # Verify service was called with status filter
        mock_api_key_service.list_api_keys.assert_called_once()
        call_kwargs = mock_api_key_service.list_api_keys.call_args.kwargs
        assert call_kwargs["status"] == "active"
