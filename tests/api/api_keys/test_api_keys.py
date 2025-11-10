"""Integration tests for API Key CRUD endpoints."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository


@pytest.mark.asyncio
class TestCreateAPIKey:
    """Test suite for POST /v1/api-keys endpoint."""

    async def test_create_api_key_success(self, authenticated_client: AsyncClient, db_session: AsyncSession):
        """Test creating an API key with valid data."""
        # Create an account first
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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
        response = await authenticated_client.post(
            "/api-keys",
            json={
                "account_id": str(account_id),
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
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test creating an API key with expiration date."""
        # Create an account first
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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
        response = await authenticated_client.post(
            "/api-keys",
            json={
                "account_id": str(account_id),
                "name": "Temporary Key",
                "expires_at": expires_at.isoformat(),
            },
        )

        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "Temporary Key"
        assert data["expires_at"] is not None

    async def test_create_api_key_missing_account_id(self, authenticated_client: AsyncClient):
        """Test creating an API key without account_id returns 422."""
        response = await authenticated_client.post(
            "/api-keys",
            json={
                "name": "Test API Key",
            },
        )

        assert response.status_code == 422

    async def test_create_api_key_missing_name(self, authenticated_client: AsyncClient, db_session: AsyncSession):
        """Test creating an API key without name returns 422."""
        # Create an account first
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        response = await authenticated_client.post(
            "/api-keys",
            json={
                "account_id": str(account_id),
            },
        )

        assert response.status_code == 422

    async def test_create_api_key_invalid_account_id_format(self, authenticated_client: AsyncClient):
        """Test creating an API key with invalid UUID format returns 422."""
        response = await authenticated_client.post(
            "/api-keys",
            json={
                "account_id": "not-a-uuid",
                "name": "Test API Key",
            },
        )

        assert response.status_code == 422

    async def test_create_api_key_nonexistent_account(self, authenticated_client: AsyncClient):
        """Test creating an API key for non-existent account returns 404."""
        non_existent_id = uuid4()

        response = await authenticated_client.post(
            "/api-keys",
            json={
                "account_id": str(non_existent_id),
                "name": "Test API Key",
            },
        )

        # Should return 404 since account doesn't exist
        assert response.status_code == 404

    async def test_create_api_key_returns_plain_key_once(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that plain key is returned in create response but not in subsequent GETs."""
        # Create an account first
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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
        create_response = await authenticated_client.post(
            "/api-keys",
            json={
                "account_id": str(account_id),
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
        get_response = await authenticated_client.get(f"/api-keys/{key_id}")
        assert get_response.status_code == 200

        get_data = get_response.json()
        # Should not have 'key' field in subsequent responses
        assert "key" not in get_data
        # Should have prefix for identification
        assert "prefix" in get_data


@pytest.mark.asyncio
class TestListAPIKeys:
    """Test suite for GET /v1/api-keys endpoint (list/filter)."""

    async def test_list_api_keys_by_account(self, authenticated_client: AsyncClient, db_session: AsyncSession):
        """Test listing API keys filtered by account_id."""
        # Create two accounts
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1_id = uuid4()
        account1 = Account(
            id=account1_id,
            name="Account 1",
            slug="account-1",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)

        account2_id = uuid4()
        account2 = Account(
            id=account2_id,
            name="Account 2",
            slug="account-2",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account2)

        # Create API keys for both accounts
        # Account 1: 3 keys
        for i in range(3):
            await authenticated_client.post(
                "/api-keys",
                json={
                    "account_id": str(account1_id),
                    "name": f"Account 1 Key {i + 1}",
                },
            )

        # Account 2: 2 keys
        for i in range(2):
            await authenticated_client.post(
                "/api-keys",
                json={
                    "account_id": str(account2_id),
                    "name": f"Account 2 Key {i + 1}",
                },
            )

        # List keys for account 1
        response = await authenticated_client.get(f"/api-keys?account_id={account1_id}")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 3
        for item in data:
            assert item["account_id"] == str(account1_id)
            assert "key" not in item  # Should not expose plain keys in list
            assert "prefix" in item

        # List keys for account 2
        response = await authenticated_client.get(f"/api-keys?account_id={account2_id}")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        for item in data:
            assert item["account_id"] == str(account2_id)

    async def test_list_api_keys_filter_by_status(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test listing API keys filtered by status."""
        # Create an account
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        # Create multiple API keys
        created_keys = []
        for i in range(3):
            response = await authenticated_client.post(
                "/api-keys",
                json={
                    "account_id": str(account_id),
                    "name": f"Test Key {i + 1}",
                },
            )
            created_keys.append(response.json())

        # TODO: Revoke one key once PATCH endpoint is implemented
        # For now, all keys should be active

        # Filter by active status for this account
        response = await authenticated_client.get(f"/api-keys?account_id={account_id}&status=active")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 3  # Exactly our 3 keys (filtered by account and status)
        for item in data:
            assert item["status"] == "active"

    async def test_list_api_keys_filter_by_account_and_status(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test listing API keys with multiple filters (account_id + status)."""
        # Create an account
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        # Create API keys
        for i in range(2):
            await authenticated_client.post(
                "/api-keys",
                json={
                    "account_id": str(account_id),
                    "name": f"Test Key {i + 1}",
                },
            )

        # Filter by both account_id and status
        response = await authenticated_client.get(f"/api-keys?account_id={account_id}&status=active")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        for item in data:
            assert item["account_id"] == str(account_id)
            assert item["status"] == "active"

    async def test_list_api_keys_no_filters_returns_all(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test listing API keys without filters returns all keys."""
        # Create an account and some keys
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        # Create 3 API keys
        for i in range(3):
            await authenticated_client.post(
                "/api-keys",
                json={
                    "account_id": str(account_id),
                    "name": f"Test Key {i + 1}",
                },
            )

        # List all keys for the account
        response = await authenticated_client.get(f"/api-keys?account_id={account_id}")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 3  # Exactly our 3 keys (filtered by account)

    async def test_list_api_keys_empty_result(self, authenticated_client: AsyncClient):
        """Test listing API keys with filter that matches nothing returns empty list."""
        # Query for a non-existent account
        non_existent_id = uuid4()
        response = await authenticated_client.get(f"/api-keys?account_id={non_existent_id}")
        assert response.status_code == 200

        data = response.json()
        assert data == []

    async def test_list_api_keys_invalid_account_id_format(self, authenticated_client: AsyncClient):
        """Test listing API keys with invalid account_id format returns 422."""
        response = await authenticated_client.get("/api-keys?account_id=not-a-uuid")
        assert response.status_code == 422

    async def test_list_api_keys_invalid_status(self, authenticated_client: AsyncClient):
        """Test listing API keys with invalid status value returns 422."""
        response = await authenticated_client.get("/api-keys?status=invalid-status")
        assert response.status_code == 422


@pytest.mark.asyncio
class TestGetSingleAPIKey:
    """Test suite for GET /v1/api-keys/{key_id} endpoint."""

    async def test_get_api_key_success(self, authenticated_client: AsyncClient, db_session: AsyncSession):
        """Test getting a single API key by ID."""
        # Create an account
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        # Create an API key
        create_response = await authenticated_client.post(
            "/api-keys",
            json={
                "account_id": str(account_id),
                "name": "Test API Key",
            },
        )
        assert create_response.status_code == 201
        key_id = create_response.json()["id"]

        # Get the API key by ID
        response = await authenticated_client.get(f"/api-keys/{key_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == key_id
        assert data["name"] == "Test API Key"
        assert data["account_id"] == str(account_id)
        assert data["status"] == "active"
        assert "key" not in data  # Plain key should not be returned
        assert "prefix" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_get_api_key_not_found(self, authenticated_client: AsyncClient):
        """Test getting a non-existent API key returns 404."""
        non_existent_id = uuid4()
        response = await authenticated_client.get(f"/api-keys/{non_existent_id}")
        assert response.status_code == 404

    async def test_get_api_key_invalid_uuid_format(self, authenticated_client: AsyncClient):
        """Test getting an API key with invalid UUID format returns 422."""
        response = await authenticated_client.get("/api-keys/not-a-uuid")
        assert response.status_code == 422

    async def test_get_api_key_includes_all_fields(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that get response includes all expected fields."""
        # Create an account
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        # Create an API key with expiration
        expires_at = now + timedelta(days=90)
        create_response = await authenticated_client.post(
            "/api-keys",
            json={
                "account_id": str(account_id),
                "name": "Test API Key",
                "expires_at": expires_at.isoformat(),
            },
        )
        key_id = create_response.json()["id"]

        # Get the API key
        response = await authenticated_client.get(f"/api-keys/{key_id}")
        assert response.status_code == 200

        data = response.json()
        # Verify all expected fields are present
        assert "id" in data
        assert "account_id" in data
        assert "name" in data
        assert "prefix" in data
        assert "status" in data
        assert "last_used_at" in data
        assert "expires_at" in data
        assert "created_at" in data
        assert "updated_at" in data
        # Verify sensitive fields are NOT present
        assert "key" not in data
        assert "key_hash" not in data


@pytest.mark.asyncio
class TestUpdateAPIKey:
    """Test suite for PATCH /v1/api-keys/{key_id} endpoint."""

    async def test_update_api_key_revoke_status(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test revoking an API key by updating status to revoked."""
        # Create an account
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        # Create an API key
        create_response = await authenticated_client.post(
            "/api-keys",
            json={
                "account_id": str(account_id),
                "name": "Test API Key",
            },
        )
        key_id = create_response.json()["id"]

        # Revoke the key
        response = await authenticated_client.patch(
            f"/api-keys/{key_id}",
            json={"status": "revoked"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == key_id
        assert data["status"] == "revoked"

        # Verify status was updated by fetching again
        get_response = await authenticated_client.get(f"/api-keys/{key_id}")
        assert get_response.json()["status"] == "revoked"

    async def test_update_api_key_not_found(self, authenticated_client: AsyncClient):
        """Test updating a non-existent API key returns 404."""
        non_existent_id = uuid4()
        response = await authenticated_client.patch(
            f"/api-keys/{non_existent_id}",
            json={"status": "revoked"},
        )
        assert response.status_code == 404

    async def test_update_api_key_invalid_status(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test updating with invalid status value returns 422."""
        # Create an account
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        # Create an API key
        create_response = await authenticated_client.post(
            "/api-keys",
            json={
                "account_id": str(account_id),
                "name": "Test API Key",
            },
        )
        key_id = create_response.json()["id"]

        # Try to update with invalid status
        response = await authenticated_client.patch(
            f"/api-keys/{key_id}",
            json={"status": "invalid-status"},
        )
        assert response.status_code == 422

    async def test_update_api_key_soft_delete(self, authenticated_client: AsyncClient, db_session: AsyncSession):
        """Test soft deleting an API key via PATCH."""
        # Create an account
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        # Create an API key
        create_response = await authenticated_client.post(
            "/api-keys",
            json={
                "account_id": str(account_id),
                "name": "Test API Key",
            },
        )
        key_id = create_response.json()["id"]

        # Soft delete the key
        response = await authenticated_client.patch(
            f"/api-keys/{key_id}",
            json={"deleted": True},
        )
        # For now, this should succeed as a placeholder
        assert response.status_code == 200

    async def test_update_api_key_empty_body(self, authenticated_client: AsyncClient, db_session: AsyncSession):
        """Test updating with empty body returns 200 but no changes."""
        # Create an account
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        # Create an API key
        create_response = await authenticated_client.post(
            "/api-keys",
            json={
                "account_id": str(account_id),
                "name": "Test API Key",
            },
        )
        key_id = create_response.json()["id"]
        original_status = create_response.json()["status"]

        # Update with empty body
        response = await authenticated_client.patch(f"/api-keys/{key_id}", json={})
        assert response.status_code == 200

        # Status should remain unchanged
        data = response.json()
        assert data["status"] == original_status

    async def test_update_api_key_invalid_uuid_format(self, authenticated_client: AsyncClient):
        """Test updating with invalid UUID format returns 422."""
        response = await authenticated_client.patch(
            "/api-keys/not-a-uuid",
            json={"status": "revoked"},
        )
        assert response.status_code == 422

    async def test_update_api_key_cannot_change_name(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that attempting to change name field is ignored or rejected."""
        # Create an account
        account_repo = AccountRepository(db_session)
        account_id = uuid4()
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

        # Create an API key
        create_response = await authenticated_client.post(
            "/api-keys",
            json={
                "account_id": str(account_id),
                "name": "Original Name",
            },
        )
        key_id = create_response.json()["id"]

        # Try to update name (should be ignored since UpdateAPIKeyRequest
        # only allows status/deleted)
        response = await authenticated_client.patch(
            f"/api-keys/{key_id}",
            json={"name": "New Name"},
        )
        # Should succeed but name should remain unchanged
        assert response.status_code == 200

        # Verify name didn't change
        get_response = await authenticated_client.get(f"/api-keys/{key_id}")
        assert get_response.json()["name"] == "Original Name"
