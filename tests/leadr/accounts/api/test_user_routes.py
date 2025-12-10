"""Tests for User API routes - superadmin optional account_id."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.dependencies import get_user_service
from leadr.accounts.services.repositories import AccountRepository
from leadr.common.domain.ids import AccountID


@pytest.mark.asyncio
class TestSuperadminOptionalAccountId:
    """Test suite for superadmin optional account_id on list endpoints."""

    async def test_superadmin_list_users_without_account_id_returns_all(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test that superadmin can list users WITHOUT account_id and sees all accounts."""
        # Create two accounts with users in each
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="Account One",
            slug="account-one",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="Account Two",
            slug="account-two",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create users in each account
        user_service = await get_user_service(db_session)
        await user_service.create_user(
            account_id=account1.id,
            email="user1@account1.com",
            display_name="User Account 1",
        )
        await user_service.create_user(
            account_id=account2.id,
            email="user2@account2.com",
            display_name="User Account 2",
        )

        # List users WITHOUT account_id - should return users from ALL accounts
        response = await authenticated_client.get("/users")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        # Should contain users from both accounts
        emails = {u["email"] for u in data["data"]}
        assert "user1@account1.com" in emails
        assert "user2@account2.com" in emails

    async def test_superadmin_list_users_with_account_id_returns_scoped(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test that superadmin can still scope by account_id when provided."""
        # Create two accounts with users in each
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="Account One",
            slug="account-one-scoped",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="Account Two",
            slug="account-two-scoped",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create users in each account
        user_service = await get_user_service(db_session)
        await user_service.create_user(
            account_id=account1.id,
            email="scoped-user1@account1.com",
            display_name="Scoped User 1",
        )
        await user_service.create_user(
            account_id=account2.id,
            email="scoped-user2@account2.com",
            display_name="Scoped User 2",
        )

        # List users WITH account_id - should return only that account's users
        response = await authenticated_client.get(f"/users?account_id={account1.id}")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

        # Should only contain users from account1
        emails = {u["email"] for u in data["data"]}
        assert "scoped-user1@account1.com" in emails
        assert "scoped-user2@account2.com" not in emails
