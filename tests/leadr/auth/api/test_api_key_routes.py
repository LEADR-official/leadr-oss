"""Tests for API Key API routes - superadmin optional account_id."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.dependencies import get_user_service
from leadr.accounts.services.repositories import AccountRepository
from leadr.auth.services.dependencies import get_api_key_service
from leadr.common.domain.ids import AccountID


@pytest.mark.asyncio
class TestSuperadminOptionalAccountId:
    """Test suite for superadmin optional account_id on list endpoints."""

    async def test_superadmin_list_api_keys_without_account_id_returns_all(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test that superadmin can list API keys WITHOUT account_id and sees all accounts."""
        # Create two accounts with API keys in each
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="Account One",
            slug="account-one-apikeys",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="Account Two",
            slug="account-two-apikeys",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create users and API keys in each account
        user_service = await get_user_service(db_session)
        api_key_service = await get_api_key_service(db_session)

        user1 = await user_service.create_user(
            account_id=account1.id,
            email="apikey-user1@account1.com",
            display_name="API Key User 1",
        )
        user2 = await user_service.create_user(
            account_id=account2.id,
            email="apikey-user2@account2.com",
            display_name="API Key User 2",
        )

        await api_key_service.create_api_key(
            account_id=account1.id,
            user_id=user1.id,
            name="Account 1 Key",
        )
        await api_key_service.create_api_key(
            account_id=account2.id,
            user_id=user2.id,
            name="Account 2 Key",
        )

        # List API keys WITHOUT account_id - should return keys from ALL accounts
        response = await authenticated_client.get("/api-keys")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        # Should contain API keys from both accounts
        key_names = {k["name"] for k in data["data"]}
        assert "Account 1 Key" in key_names
        assert "Account 2 Key" in key_names
