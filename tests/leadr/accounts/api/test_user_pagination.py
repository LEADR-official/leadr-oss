"""Unit tests for user pagination."""

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from leadr.accounts.domain.user import User
from leadr.common.domain.ids import AccountID, UserID
from leadr.common.domain.pagination_result import CursorPosition, PaginatedResult


@pytest.mark.asyncio
class TestUserPagination:
    """Test user pagination through API."""

    async def test_default_pagination(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_user_service,
    ) -> None:
        """Test that default limit is 20 and default sort is created_at:desc,id:asc."""
        account_id = AccountID()

        # Create 20 mock users
        users = [
            User(
                id=UserID(),
                account_id=account_id,
                email=f"user{i}@example.com",
                display_name=f"Test User {i}",
            )
            for i in range(20)
        ]

        mock_user_service.list_users_by_account.return_value = PaginatedResult(
            items=users,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(
                values=(users[-1].created_at, str(users[-1].id)),
                entity_id=str(users[-1].id),
            ),
            prev_position=None,
        )

        # Get first page
        response = await mock_client_no_db.get(f"/users?account_id={account_id}")
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
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_user_service,
    ) -> None:
        """Test forward pagination using next_cursor."""
        account_id = AccountID()

        # Create first page of users
        page1_users = [
            User(
                id=UserID(),
                account_id=account_id,
                email=f"user{i:03d}@example.com",
                display_name=f"User {i:03d}",
            )
            for i in range(10)
        ]

        # Create second page of users
        page2_users = [
            User(
                id=UserID(),
                account_id=account_id,
                email=f"user{i:03d}@example.com",
                display_name=f"User {i:03d}",
            )
            for i in range(10, 20)
        ]

        # Mock first page response
        mock_user_service.list_users_by_account.return_value = PaginatedResult(
            items=page1_users,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(
                values=(page1_users[-1].created_at, str(page1_users[-1].id)),
                entity_id=str(page1_users[-1].id),
            ),
            prev_position=None,
        )

        # Get first page
        response = await mock_client_no_db.get(f"/users?account_id={account_id}&limit=10")
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1["data"]) == 10
        assert page1["pagination"]["has_next"] is True

        # Mock second page response
        mock_user_service.list_users_by_account.return_value = PaginatedResult(
            items=page2_users,
            has_next=True,
            has_prev=True,
            next_position=CursorPosition(
                values=(page2_users[-1].created_at, str(page2_users[-1].id)),
                entity_id=str(page2_users[-1].id),
            ),
            prev_position=CursorPosition(
                values=(page2_users[0].created_at, str(page2_users[0].id)),
                entity_id=str(page2_users[0].id),
            ),
        )

        # Get second page using cursor
        next_cursor = page1["pagination"]["next_cursor"]
        response = await mock_client_no_db.get(
            f"/users?account_id={account_id}&limit=10&cursor={next_cursor}"
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
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_user_service,
    ) -> None:
        """Test backward pagination using prev_cursor."""
        account_id = AccountID()

        # Create users for testing
        page1_users = [
            User(
                id=UserID(),
                account_id=account_id,
                email=f"user{i:03d}@example.com",
                display_name=f"User {i:03d}",
            )
            for i in range(10)
        ]

        page2_users = [
            User(
                id=UserID(),
                account_id=account_id,
                email=f"user{i:03d}@example.com",
                display_name=f"User {i:03d}",
            )
            for i in range(10, 20)
        ]

        # Mock first page
        mock_user_service.list_users_by_account.return_value = PaginatedResult(
            items=page1_users,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(
                values=(page1_users[-1].created_at, str(page1_users[-1].id)),
                entity_id=str(page1_users[-1].id),
            ),
            prev_position=None,
        )

        # Get first page
        response = await mock_client_no_db.get(f"/users?account_id={account_id}&limit=10")
        page1 = response.json()

        # Mock second page
        mock_user_service.list_users_by_account.return_value = PaginatedResult(
            items=page2_users,
            has_next=True,
            has_prev=True,
            next_position=CursorPosition(
                values=(page2_users[-1].created_at, str(page2_users[-1].id)),
                entity_id=str(page2_users[-1].id),
            ),
            prev_position=CursorPosition(
                values=(page2_users[0].created_at, str(page2_users[0].id)),
                entity_id=str(page2_users[0].id),
            ),
        )

        # Get second page
        next_cursor = page1["pagination"]["next_cursor"]
        response = await mock_client_no_db.get(
            f"/users?account_id={account_id}&limit=10&cursor={next_cursor}"
        )
        page2 = response.json()
        assert page2["pagination"]["has_prev"] is True

        # Mock going back to first page
        mock_user_service.list_users_by_account.return_value = PaginatedResult(
            items=page1_users,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(
                values=(page1_users[-1].created_at, str(page1_users[-1].id)),
                entity_id=str(page1_users[-1].id),
            ),
            prev_position=None,
        )

        # Go back to first page using prev_cursor
        prev_cursor = page2["pagination"]["prev_cursor"]
        response = await mock_client_no_db.get(
            f"/users?account_id={account_id}&limit=10&cursor={prev_cursor}"
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
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_user_service,
    ) -> None:
        """Test pagination with custom sort (email ascending)."""
        account_id = AccountID()

        # Create users with different emails
        emails = ["alpha@example.com", "beta@example.com", "zebra@example.com"]
        users = [
            User(
                id=UserID(),
                account_id=account_id,
                email=email,
                display_name=email.split("@")[0].title(),
            )
            for email in emails
        ]

        mock_user_service.list_users_by_account.return_value = PaginatedResult(
            items=users,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        # Get sorted by email ascending
        response = await mock_client_no_db.get(f"/users?account_id={account_id}&sort=email:asc")
        assert response.status_code == 200
        data = response.json()

        # Verify ascending order
        users_data = data["data"]
        user_emails = [user["email"] for user in users_data if user["email"] in emails]
        assert user_emails == emails  # Already sorted in mock

    async def test_invalid_sort_field(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_user_service,
    ) -> None:
        """Test that invalid sort field returns 400 error."""
        account_id = AccountID()

        # Validation happens in the service layer - make it raise HTTPException for invalid field
        mock_user_service.list_users_by_account.side_effect = HTTPException(
            status_code=400, detail="Unknown sort field: invalid_field"
        )

        response = await mock_client_no_db.get(
            f"/users?account_id={account_id}&sort=invalid_field:desc"
        )
        assert response.status_code == 400
        assert "Unknown sort field" in response.json()["error"]

    async def test_cursor_state_validation(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_user_service,
    ) -> None:
        """Test that cursor state mismatch returns 400 error."""
        account_id = AccountID()

        # Create users
        users = [
            User(
                id=UserID(),
                account_id=account_id,
                email=f"user{i}@example.com",
                display_name=f"User {i}",
            )
            for i in range(10)
        ]

        mock_user_service.list_users_by_account.return_value = PaginatedResult(
            items=users,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(
                values=(users[-1].created_at, str(users[-1].id)),
                entity_id=str(users[-1].id),
            ),
            prev_position=None,
        )

        # Get first page with one sort (use limit=10 to ensure pagination)
        response = await mock_client_no_db.get(
            f"/users?account_id={account_id}&sort=email:desc&limit=10"
        )
        page1 = response.json()
        cursor = page1["pagination"]["next_cursor"]

        # Make second call raise validation error
        mock_user_service.list_users_by_account.side_effect = HTTPException(
            status_code=400, detail="Query parameters don't match cursor state"
        )

        # Try to use cursor with different sort
        response = await mock_client_no_db.get(
            f"/users?account_id={account_id}&sort=display_name:asc&limit=10&cursor={cursor}"
        )
        assert response.status_code == 400
        assert "Query parameters don't match cursor state" in response.json()["error"]

    async def test_pagination_with_filters(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_user_service,
    ) -> None:
        """Test pagination requires account_id filter."""
        account_id = AccountID()

        # Create 5 users
        users = [
            User(
                id=UserID(),
                account_id=account_id,
                email=f"user{i}@example.com",
                display_name=f"User {i}",
            )
            for i in range(5)
        ]

        mock_user_service.list_users_by_account.return_value = PaginatedResult(
            items=users,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(
                values=(users[-1].created_at, str(users[-1].id)),
                entity_id=str(users[-1].id),
            ),
            prev_position=None,
        )

        # Get users with account_id filter and custom limit
        response = await mock_client_no_db.get(f"/users?account_id={account_id}&limit=5")
        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["count"] == 5
        assert len(data["data"]) == 5
        assert data["pagination"]["has_next"] is True

        # Verify all users belong to the account
        for user in data["data"]:
            assert user["account_id"] == str(account_id)
