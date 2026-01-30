"""Unit tests for account pagination."""

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.common.domain.ids import AccountID
from leadr.common.domain.pagination_result import CursorPosition, PaginatedResult


@pytest.mark.asyncio
class TestAccountPagination:
    """Test account pagination through API."""

    async def test_default_pagination(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_account_service,
    ) -> None:
        """Test that default limit is 20 and default sort is created_at:desc,id:asc."""
        # Create 25 mock accounts (but return only first 20)
        accounts = [
            Account(
                id=AccountID(),
                name=f"Test Account {i}",
                slug=f"test-account-{i:03d}",
                status=AccountStatus.ACTIVE,
            )
            for i in range(20)
        ]

        mock_account_service.list_accounts.return_value = PaginatedResult(
            items=accounts,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(
                values=(accounts[-1].created_at, str(accounts[-1].id)),
                entity_id=str(accounts[-1].id),
            ),
            prev_position=None,
        )

        # Get first page
        response = await mock_client_no_db.get("/accounts")
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
        mock_account_service,
    ) -> None:
        """Test forward pagination using next_cursor."""
        # Create first page of accounts
        page1_accounts = [
            Account(
                id=AccountID(),
                name=f"Account {i:03d}",
                slug=f"account-{i:03d}",
                status=AccountStatus.ACTIVE,
            )
            for i in range(10)
        ]

        # Create second page of accounts
        page2_accounts = [
            Account(
                id=AccountID(),
                name=f"Account {i:03d}",
                slug=f"account-{i:03d}",
                status=AccountStatus.ACTIVE,
            )
            for i in range(10, 20)
        ]

        # Mock first page response
        mock_account_service.list_accounts.return_value = PaginatedResult(
            items=page1_accounts,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(
                values=(page1_accounts[-1].created_at, str(page1_accounts[-1].id)),
                entity_id=str(page1_accounts[-1].id),
            ),
            prev_position=None,
        )

        # Get first page
        response = await mock_client_no_db.get("/accounts?limit=10")
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1["data"]) == 10
        assert page1["pagination"]["has_next"] is True

        # Mock second page response
        mock_account_service.list_accounts.return_value = PaginatedResult(
            items=page2_accounts,
            has_next=True,
            has_prev=True,
            next_position=CursorPosition(
                values=(page2_accounts[-1].created_at, str(page2_accounts[-1].id)),
                entity_id=str(page2_accounts[-1].id),
            ),
            prev_position=CursorPosition(
                values=(page2_accounts[0].created_at, str(page2_accounts[0].id)),
                entity_id=str(page2_accounts[0].id),
            ),
        )

        # Get second page using cursor
        next_cursor = page1["pagination"]["next_cursor"]
        response = await mock_client_no_db.get(f"/accounts?limit=10&cursor={next_cursor}")
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
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_account_service,
    ) -> None:
        """Test backward pagination using prev_cursor."""
        # Create accounts for testing
        page1_accounts = [
            Account(
                id=AccountID(),
                name=f"Account {i:03d}",
                slug=f"account-{i:03d}",
                status=AccountStatus.ACTIVE,
            )
            for i in range(10)
        ]

        page2_accounts = [
            Account(
                id=AccountID(),
                name=f"Account {i:03d}",
                slug=f"account-{i:03d}",
                status=AccountStatus.ACTIVE,
            )
            for i in range(10, 20)
        ]

        # Mock first page
        mock_account_service.list_accounts.return_value = PaginatedResult(
            items=page1_accounts,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(
                values=(page1_accounts[-1].created_at, str(page1_accounts[-1].id)),
                entity_id=str(page1_accounts[-1].id),
            ),
            prev_position=None,
        )

        # Get first page
        response = await mock_client_no_db.get("/accounts?limit=10")
        page1 = response.json()

        # Mock second page
        mock_account_service.list_accounts.return_value = PaginatedResult(
            items=page2_accounts,
            has_next=True,
            has_prev=True,
            next_position=CursorPosition(
                values=(page2_accounts[-1].created_at, str(page2_accounts[-1].id)),
                entity_id=str(page2_accounts[-1].id),
            ),
            prev_position=CursorPosition(
                values=(page2_accounts[0].created_at, str(page2_accounts[0].id)),
                entity_id=str(page2_accounts[0].id),
            ),
        )

        # Get second page
        next_cursor = page1["pagination"]["next_cursor"]
        response = await mock_client_no_db.get(f"/accounts?limit=10&cursor={next_cursor}")
        page2 = response.json()
        assert page2["pagination"]["has_prev"] is True

        # Mock going back to first page
        mock_account_service.list_accounts.return_value = PaginatedResult(
            items=page1_accounts,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(
                values=(page1_accounts[-1].created_at, str(page1_accounts[-1].id)),
                entity_id=str(page1_accounts[-1].id),
            ),
            prev_position=None,
        )

        # Go back to first page using prev_cursor
        prev_cursor = page2["pagination"]["prev_cursor"]
        response = await mock_client_no_db.get(f"/accounts?limit=10&cursor={prev_cursor}")
        assert response.status_code == 200
        page_back = response.json()

        # Should match first page
        assert len(page_back["data"]) == len(page1["data"])
        page_back_ids = {account["id"] for account in page_back["data"]}
        page1_ids = {account["id"] for account in page1["data"]}
        assert page_back_ids == page1_ids

    async def test_custom_sort(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_account_service,
    ) -> None:
        """Test pagination with custom sort (name ascending)."""
        # Create accounts with different names
        names = ["Alpha Inc", "Beta LLC", "Delta Co", "Gamma Ltd", "Zebra Corp"]
        accounts = [
            Account(
                id=AccountID(),
                name=name,
                slug=f"slug-{i:03d}",
                status=AccountStatus.ACTIVE,
            )
            for i, name in enumerate(names)
        ]

        mock_account_service.list_accounts.return_value = PaginatedResult(
            items=accounts,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        # Get sorted by name ascending
        response = await mock_client_no_db.get("/accounts?sort=name:asc")
        assert response.status_code == 200
        data = response.json()

        # Verify ascending order
        accounts_data = data["data"]
        account_names = [acc["name"] for acc in accounts_data if acc["name"] in names]
        assert account_names == names  # Already sorted in mock

    async def test_invalid_sort_field(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_account_service,
    ) -> None:
        """Test that invalid sort field returns 400 error."""
        # Validation happens in the service layer - make it raise HTTPException for invalid field
        mock_account_service.list_accounts.side_effect = HTTPException(
            status_code=400, detail="Unknown sort field: invalid_field"
        )

        response = await mock_client_no_db.get("/accounts?sort=invalid_field:desc")
        assert response.status_code == 400
        assert "Unknown sort field" in response.json()["error"]

    async def test_cursor_state_validation(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_account_service,
    ) -> None:
        """Test that cursor state mismatch returns 400 error."""
        # Create accounts
        accounts = [
            Account(
                id=AccountID(),
                name=f"Account {i}",
                slug=f"account-{i:03d}",
                status=AccountStatus.ACTIVE,
            )
            for i in range(10)
        ]

        mock_account_service.list_accounts.return_value = PaginatedResult(
            items=accounts,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(
                values=(accounts[-1].created_at, str(accounts[-1].id)),
                entity_id=str(accounts[-1].id),
            ),
            prev_position=None,
        )

        # Get first page with one sort
        response = await mock_client_no_db.get("/accounts?sort=name:desc")
        page1 = response.json()
        cursor = page1["pagination"]["next_cursor"]

        # Make second call raise validation error
        mock_account_service.list_accounts.side_effect = HTTPException(
            status_code=400, detail="Query parameters don't match cursor state"
        )

        # Try to use cursor with different sort
        response = await mock_client_no_db.get(f"/accounts?sort=slug:asc&cursor={cursor}")
        assert response.status_code == 400
        assert "Query parameters don't match cursor state" in response.json()["error"]

    async def test_pagination_with_filters(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_account_service,
    ) -> None:
        """Test pagination works correctly with no entity-specific filters.

        Note: Accounts endpoint has no additional filters beyond pagination.
        This test verifies basic pagination still works.
        """
        # Create 5 accounts
        accounts = [
            Account(
                id=AccountID(),
                name=f"Test Account {i}",
                slug=f"test-account-{i:03d}",
                status=AccountStatus.ACTIVE,
            )
            for i in range(5)
        ]

        mock_account_service.list_accounts.return_value = PaginatedResult(
            items=accounts,
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(
                values=(accounts[-1].created_at, str(accounts[-1].id)),
                entity_id=str(accounts[-1].id),
            ),
            prev_position=None,
        )

        # Get accounts with custom limit
        response = await mock_client_no_db.get("/accounts?limit=5")
        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["count"] == 5
        assert len(data["data"]) == 5
        assert data["pagination"]["has_next"] is True
