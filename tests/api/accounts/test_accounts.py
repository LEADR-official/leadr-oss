"""End-to-end tests for Account API endpoints."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository


@pytest.mark.asyncio
class TestAccountAPI:
    """End-to-end test suite for Account API routes."""

    async def test_create_account(self, authenticated_client: AsyncClient):
        """Test creating an account via POST /accounts."""
        response = await authenticated_client.post(
            "/accounts",
            json={
                "name": "Acme Corporation",
                "slug": "acme-corp",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Acme Corporation"
        assert data["slug"] == "acme-corp"
        assert data["status"] == "active"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

        # Verify we can retrieve it
        account_id = data["id"]
        get_response = await authenticated_client.get(f"/accounts/{account_id}")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["id"] == account_id

    async def test_create_account_missing_name(self, authenticated_client: AsyncClient):
        """Test creating account without name returns 422."""
        response = await authenticated_client.post(
            "/accounts",
            json={
                "slug": "acme-corp",
            },
        )

        assert response.status_code == 422

    async def test_create_account_missing_slug(self, authenticated_client: AsyncClient):
        """Test creating account without slug returns 422."""
        response = await authenticated_client.post(
            "/accounts",
            json={
                "name": "Acme Corporation",
            },
        )

        assert response.status_code == 422

    async def test_get_account_by_id(self, authenticated_client: AsyncClient, db_session):
        """Test getting account by ID via GET /accounts/{id}."""
        # Create account first
        repo = AccountRepository(db_session)
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(account)

        # Get it via API
        response = await authenticated_client.get(f"/accounts/{account_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(account_id)
        assert data["name"] == "Acme Corporation"
        assert data["slug"] == "acme-corp"
        assert data["status"] == "active"

    async def test_get_account_by_id_not_found(self, authenticated_client: AsyncClient):
        """Test getting non-existent account returns 404."""
        fake_id = uuid4()
        response = await authenticated_client.get(f"/accounts/{fake_id}")

        assert response.status_code == 404

    async def test_get_account_by_id_deleted(self, authenticated_client: AsyncClient, db_session):
        """Test getting soft-deleted account returns 404."""
        # Create and delete account
        repo = AccountRepository(db_session)
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(account)
        await repo.delete(account_id)

        # Try to get it
        response = await authenticated_client.get(f"/accounts/{account_id}")

        assert response.status_code == 404

    async def test_list_accounts(self, authenticated_client: AsyncClient, db_session):
        """Test listing all accounts via GET /accounts."""
        # Create some accounts
        repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=uuid4(),
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=uuid4(),
            name="Beta Industries",
            slug="beta-industries",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        await repo.create(account1)
        await repo.create(account2)

        # List them
        response = await authenticated_client.get("/accounts")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should include 2 test accounts + 1 from auth fixture
        assert len(data) >= 2
        slugs = {acc["slug"] for acc in data}
        assert "acme-corp" in slugs
        assert "beta-industries" in slugs

    async def test_list_accounts_excludes_deleted(self, authenticated_client: AsyncClient, db_session):
        """Test that list excludes soft-deleted accounts."""
        # Create accounts
        repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=uuid4(),
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=uuid4(),
            name="Beta Industries",
            slug="beta-industries",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        await repo.create(account1)
        await repo.create(account2)

        # Delete one
        await repo.delete(account1.id)

        # List should only show non-deleted
        response = await authenticated_client.get("/accounts")

        assert response.status_code == 200
        data = response.json()
        # Should include 1 test account + 1 from auth fixture (acme-corp was deleted)
        assert len(data) >= 1
        slugs = {acc["slug"] for acc in data}
        assert "beta-industries" in slugs
        assert "acme-corp" not in slugs  # This one was deleted

    async def test_update_account(self, authenticated_client: AsyncClient, db_session):
        """Test updating account via PATCH /accounts/{id}."""
        # Create account
        repo = AccountRepository(db_session)
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(account)

        # Update it
        response = await authenticated_client.patch(
            f"/accounts/{account_id}",
            json={
                "name": "Acme Corp Updated",
                "status": "suspended",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Acme Corp Updated"
        assert data["status"] == "suspended"
        assert data["slug"] == "acme-corp"  # slug unchanged

    async def test_update_account_not_found(self, authenticated_client: AsyncClient):
        """Test updating non-existent account returns 404."""
        fake_id = uuid4()
        response = await authenticated_client.patch(
            f"/accounts/{fake_id}",
            json={"name": "Updated Name"},
        )

        assert response.status_code == 404

    async def test_delete_account(self, authenticated_client: AsyncClient, db_session):
        """Test soft-deleting account via PATCH with deleted field."""
        # Create account
        repo = AccountRepository(db_session)
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(account)

        # Soft-delete it via PATCH
        response = await authenticated_client.patch(
            f"/accounts/{account_id}",
            json={"deleted": True},
        )

        assert response.status_code == 200

        # Verify it's gone from API
        get_response = await authenticated_client.get(f"/accounts/{account_id}")
        assert get_response.status_code == 404

    async def test_delete_account_not_found(self, authenticated_client: AsyncClient):
        """Test soft-deleting non-existent account returns 404."""
        fake_id = uuid4()
        response = await authenticated_client.patch(
            f"/accounts/{fake_id}",
            json={"deleted": True},
        )

        assert response.status_code == 404

    async def test_get_account_invalid_uuid(self, authenticated_client: AsyncClient):
        """Test getting account with invalid UUID returns 422."""
        response = await authenticated_client.get("/accounts/not-a-uuid")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data  # FastAPI validation error

    async def test_update_account_invalid_uuid(self, authenticated_client: AsyncClient):
        """Test updating account with invalid UUID returns 422."""
        response = await authenticated_client.patch(
            "/accounts/not-a-uuid",
            json={"name": "Updated Name"},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data  # FastAPI validation error

    async def test_update_account_partial(self, authenticated_client: AsyncClient, db_session):
        """Test updating only some fields of an account."""
        # Create account
        repo = AccountRepository(db_session)
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(account)

        # Update only name
        response = await authenticated_client.patch(
            f"/accounts/{account_id}",
            json={
                "name": "Acme Corp Updated",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Acme Corp Updated"
        assert data["slug"] == "acme-corp"  # unchanged
        assert data["status"] == "active"  # unchanged

    async def test_update_account_only_slug(self, authenticated_client: AsyncClient, db_session):
        """Test updating only slug of an account."""
        # Create account
        repo = AccountRepository(db_session)
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(account)

        # Update only slug
        response = await authenticated_client.patch(
            f"/accounts/{account_id}",
            json={
                "slug": "acme-corporation",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Acme Corporation"  # unchanged
        assert data["slug"] == "acme-corporation"
        assert data["status"] == "active"  # unchanged

    async def test_update_account_only_status(self, authenticated_client: AsyncClient, db_session):
        """Test updating only status of an account."""
        # Create account
        repo = AccountRepository(db_session)
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(account)

        # Update only status
        response = await authenticated_client.patch(
            f"/accounts/{account_id}",
            json={
                "status": "suspended",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Acme Corporation"  # unchanged
        assert data["slug"] == "acme-corp"  # unchanged
        assert data["status"] == "suspended"

    async def test_update_account_empty_request(self, authenticated_client: AsyncClient, db_session):
        """Test updating account with empty request body."""
        # Create account
        repo = AccountRepository(db_session)
        account_id = uuid4()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await repo.create(account)

        # Update with empty body (all fields None)
        response = await authenticated_client.patch(
            f"/accounts/{account_id}",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Acme Corporation"  # unchanged
        assert data["slug"] == "acme-corp"  # unchanged
        assert data["status"] == "active"  # unchanged

    async def test_update_account_all_fields_via_api(self, authenticated_client: AsyncClient):
        """Test updating account through API with all fields."""
        # Create via API
        create_response = await authenticated_client.post(
            "/accounts",
            json={
                "name": "Test Corp",
                "slug": "test-corp",
            },
        )
        assert create_response.status_code == 201
        account_id = create_response.json()["id"]

        # Update all fields
        update_response = await authenticated_client.patch(
            f"/accounts/{account_id}",
            json={
                "name": "Updated Corp",
                "slug": "updated-corp",
                "status": "suspended",
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Corp"
        assert update_response.json()["slug"] == "updated-corp"
        assert update_response.json()["status"] == "suspended"

    async def test_delete_account_via_api(self, authenticated_client: AsyncClient):
        """Test soft-deleting account created via API."""
        # Create via API
        create_response = await authenticated_client.post(
            "/accounts",
            json={
                "name": "To Delete",
                "slug": "to-delete",
            },
        )
        assert create_response.status_code == 201
        account_id = create_response.json()["id"]

        # Soft-delete it via PATCH
        delete_response = await authenticated_client.patch(
            f"/accounts/{account_id}",
            json={"deleted": True},
        )
        assert delete_response.status_code == 200

        # Confirm it's gone
        get_response = await authenticated_client.get(f"/accounts/{account_id}")
        assert get_response.status_code == 404
