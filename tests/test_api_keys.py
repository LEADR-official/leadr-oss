"""Integration tests for API Key CRUD endpoints."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.common.domain.models import EntityID


@pytest.mark.asyncio
class TestCreateAPIKey:
    """Test suite for POST /v1/api-keys endpoint."""

    async def test_create_api_key_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test creating an API key with valid data."""
        # Create an account first
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
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

        # Create API key
        response = await client.post(
            "/api-keys",
            json={
                "account_id": str(account_id.value),
                "name": "Test API Key",
            },
        )

        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "Test API Key"
        assert data["key"].startswith("ldr_")
        assert data["prefix"].startswith("ldr_")
        assert data["status"] == "active"
        assert "id" in data
        assert "created_at" in data
        assert len(data["key"]) > 36  # Should have sufficient entropy

    async def test_create_api_key_with_expiration(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test creating an API key with expiration date."""
        # Create an account first
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
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

        # Create API key with expiration
        expires_at = now + timedelta(days=90)
        response = await client.post(
            "/api-keys",
            json={
                "account_id": str(account_id.value),
                "name": "Temporary Key",
                "expires_at": expires_at.isoformat(),
            },
        )

        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "Temporary Key"
        assert data["expires_at"] is not None

    async def test_create_api_key_missing_account_id(self, client: AsyncClient):
        """Test creating an API key without account_id returns 422."""
        response = await client.post(
            "/api-keys",
            json={
                "name": "Test API Key",
            },
        )

        assert response.status_code == 422

    async def test_create_api_key_missing_name(self, client: AsyncClient, db_session: AsyncSession):
        """Test creating an API key without name returns 422."""
        # Create an account first
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
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

        response = await client.post(
            "/api-keys",
            json={
                "account_id": str(account_id.value),
            },
        )

        assert response.status_code == 422

    async def test_create_api_key_invalid_account_id_format(self, client: AsyncClient):
        """Test creating an API key with invalid UUID format returns 422."""
        response = await client.post(
            "/api-keys",
            json={
                "account_id": "not-a-uuid",
                "name": "Test API Key",
            },
        )

        assert response.status_code == 422

    async def test_create_api_key_nonexistent_account(self, client: AsyncClient):
        """Test creating an API key for non-existent account returns 404."""
        non_existent_id = EntityID.generate()

        response = await client.post(
            "/api-keys",
            json={
                "account_id": str(non_existent_id.value),
                "name": "Test API Key",
            },
        )

        # Should return 404 since account doesn't exist
        assert response.status_code == 404

    async def test_create_api_key_returns_plain_key_once(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test that plain key is returned in create response but not in subsequent GETs."""
        # Create an account first
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
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

        # Create API key
        create_response = await client.post(
            "/api-keys",
            json={
                "account_id": str(account_id.value),
                "name": "Test API Key",
            },
        )

        assert create_response.status_code == 201
        create_data = create_response.json()
        plain_key = create_data["key"]
        key_id = create_data["id"]

        # Verify plain key is returned in create response
        assert plain_key.startswith("ldr_")

        # Try to get the key by ID - should not return the plain key
        get_response = await client.get(f"/api-keys/{key_id}")
        assert get_response.status_code == 200

        get_data = get_response.json()
        # Should not have 'key' field in subsequent responses
        assert "key" not in get_data
        # Should have prefix for identification
        assert "prefix" in get_data
