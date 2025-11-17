"""Tests for API authentication requirements."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.accounts.services.user_service import UserService
from leadr.auth.services.api_key_service import APIKeyService
from leadr.common.domain.ids import AccountID


@pytest.mark.asyncio
class TestAPIAuthentication:
    """Test suite for API authentication requirements."""

    async def test_protected_endpoint_without_api_key_returns_401(self, client: AsyncClient):
        """Test that protected endpoints return 401 when no API key is provided."""
        # Try to access a protected endpoint without API key
        response = await client.post(
            "/accounts",
            json={
                "name": "Test Account",
                "slug": "test-account",
            },
        )

        assert response.status_code == 401
        assert "required" in response.json()["detail"].lower()

    async def test_protected_endpoint_with_invalid_api_key_returns_401(self, client: AsyncClient):
        """Test that protected endpoints return 401 with invalid API key."""
        # Try to access a protected endpoint with an invalid key
        response = await client.post(
            "/accounts",
            json={
                "name": "Test Account",
                "slug": "test-account",
            },
            headers={"leadr-api-key": "ldr_invalid_key_123"},
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    async def test_protected_endpoint_with_valid_api_key_succeeds(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test that protected endpoints succeed with valid API key."""
        # Create account and API key
        account_repo = AccountRepository(db_session)
        account_id = AccountID()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create user for API key (superadmin to allow creating accounts)
        user_service = UserService(db_session)
        user = await user_service.create_user(
            account_id=account_id,
            email=f"test-{str(account_id)[:8]}@example.com",
            display_name="Test User",
            super_admin=True,
        )

        # Create API key
        service = APIKeyService(db_session)
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            user_id=user.id,
            name="Test Key",
            expires_at=None,
        )

        # Access protected endpoint with valid key
        response = await client.post(
            "/accounts",
            json={
                "name": "New Account",
                "slug": "new-account",
            },
            headers={"leadr-api-key": plain_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Account"
        assert data["slug"] == "new-account"

    async def test_multiple_protected_endpoints_require_auth(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test that multiple endpoints require authentication."""
        # Create test account for GET endpoint
        account_repo = AccountRepository(db_session)
        account_id = AccountID()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Test GET endpoint without auth
        response = await client.get(f"/accounts/{account_id}")
        assert response.status_code == 401

        # Test LIST endpoint without auth
        response = await client.get("/accounts")
        assert response.status_code == 401

        # Test PATCH endpoint without auth
        response = await client.patch(
            f"/accounts/{account_id}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 401

        # Test API Keys endpoints without auth
        response = await client.post(
            "/api-keys",
            json={
                "account_id": str(account_id),
                "name": "Test Key",
            },
        )
        assert response.status_code == 401

        response = await client.get("/api-keys", params={"account_id": str(account_id)})
        assert response.status_code == 401
