"""Unit tests for User API routes - superadmin optional account_id."""

import pytest
from httpx import AsyncClient

from leadr.accounts.domain.user import User
from leadr.common.domain.ids import AccountID, UserID
from leadr.common.domain.pagination_result import PaginatedResult


@pytest.mark.asyncio
class TestSuperadminOptionalAccountId:
    """Test suite for superadmin optional account_id on list endpoints."""

    async def test_superadmin_list_users_without_account_id_returns_all(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_user_service
    ):
        """Test that superadmin can list users WITHOUT account_id and sees all accounts."""
        # Create mock users from two different accounts
        account1_id = AccountID()
        account2_id = AccountID()

        user1 = User(
            id=UserID(),
            account_id=account1_id,
            email="user1@account1.com",
            display_name="User Account 1",
        )
        user2 = User(
            id=UserID(),
            account_id=account2_id,
            email="user2@account2.com",
            display_name="User Account 2",
        )

        # Mock service to return both users
        mock_user_service.list_users_by_account.return_value = PaginatedResult(
            items=[user1, user2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        # List users WITHOUT account_id - should return users from ALL accounts
        response = await mock_client_no_db.get("/users")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        # Should contain users from both accounts
        emails = {u["email"] for u in data["data"]}
        assert "user1@account1.com" in emails
        assert "user2@account2.com" in emails

        # Verify service was called without account_id filter
        mock_user_service.list_users_by_account.assert_called_once()

    async def test_superadmin_list_users_with_account_id_returns_scoped(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_user_service
    ):
        """Test that superadmin can still scope by account_id when provided."""
        # Create mock users from two different accounts
        account1_id = AccountID()

        user1 = User(
            id=UserID(),
            account_id=account1_id,
            email="scoped-user1@account1.com",
            display_name="Scoped User 1",
        )

        # Mock service to return only user1 (filtered by account_id)
        mock_user_service.list_users_by_account.return_value = PaginatedResult(
            items=[user1],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        # List users WITH account_id - should return only that account's users
        response = await mock_client_no_db.get(f"/users?account_id={account1_id}")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

        # Should only contain users from account1
        emails = {u["email"] for u in data["data"]}
        assert "scoped-user1@account1.com" in emails
        assert len(emails) == 1

        # Verify service was called with account_id filter
        mock_user_service.list_users_by_account.assert_called_once()
