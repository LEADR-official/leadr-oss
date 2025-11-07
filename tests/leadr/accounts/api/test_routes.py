"""Tests for Account and User API routes."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.domain.user import User
from leadr.accounts.services.repositories import AccountRepository, UserRepository
from leadr.common.domain.models import EntityID


@pytest.mark.asyncio
class TestAccountRoutes:
    """Test suite for Account API routes."""

    async def test_create_account(self, client: AsyncClient):
        """Test creating an account via POST /accounts."""
        response = await client.post(
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

    async def test_create_account_missing_name(self, client: AsyncClient):
        """Test creating account without name returns 422."""
        response = await client.post(
            "/accounts",
            json={
                "slug": "acme-corp",
            },
        )

        assert response.status_code == 422

    async def test_create_account_missing_slug(self, client: AsyncClient):
        """Test creating account without slug returns 422."""
        response = await client.post(
            "/accounts",
            json={
                "name": "Acme Corporation",
            },
        )

        assert response.status_code == 422

    async def test_get_account_by_id(self, client: AsyncClient, db_session):
        """Test getting account by ID via GET /accounts/{id}."""
        # Create account first
        repo = AccountRepository(db_session)
        account_id = EntityID.generate()
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
        response = await client.get(f"/accounts/{account_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(account_id)
        assert data["name"] == "Acme Corporation"
        assert data["slug"] == "acme-corp"
        assert data["status"] == "active"

    async def test_get_account_by_id_not_found(self, client: AsyncClient):
        """Test getting non-existent account returns 404."""
        fake_id = EntityID.generate()
        response = await client.get(f"/accounts/{fake_id}")

        assert response.status_code == 404

    async def test_get_account_by_id_deleted(self, client: AsyncClient, db_session):
        """Test getting soft-deleted account returns 404."""
        # Create and delete account
        repo = AccountRepository(db_session)
        account_id = EntityID.generate()
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
        response = await client.get(f"/accounts/{account_id}")

        assert response.status_code == 404

    async def test_list_accounts(self, client: AsyncClient, db_session):
        """Test listing all accounts via GET /accounts."""
        # Create some accounts
        repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=EntityID.generate(),
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=EntityID.generate(),
            name="Beta Industries",
            slug="beta-industries",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        await repo.create(account1)
        await repo.create(account2)

        # List them
        response = await client.get("/accounts")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        slugs = {acc["slug"] for acc in data}
        assert "acme-corp" in slugs
        assert "beta-industries" in slugs

    async def test_list_accounts_excludes_deleted(self, client: AsyncClient, db_session):
        """Test that list excludes soft-deleted accounts."""
        # Create accounts
        repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=EntityID.generate(),
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=EntityID.generate(),
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
        response = await client.get("/accounts")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["slug"] == "beta-industries"

    async def test_update_account(self, client: AsyncClient, db_session):
        """Test updating account via PATCH /accounts/{id}."""
        # Create account
        repo = AccountRepository(db_session)
        account_id = EntityID.generate()
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
        response = await client.patch(
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

    async def test_update_account_not_found(self, client: AsyncClient):
        """Test updating non-existent account returns 404."""
        fake_id = EntityID.generate()
        response = await client.patch(
            f"/accounts/{fake_id}",
            json={"name": "Updated Name"},
        )

        assert response.status_code == 404

    async def test_delete_account(self, client: AsyncClient, db_session):
        """Test soft-deleting account via POST /accounts/{id}/delete."""
        # Create account
        repo = AccountRepository(db_session)
        account_id = EntityID.generate()
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

        # Delete it
        response = await client.post(f"/accounts/{account_id}/delete")

        assert response.status_code == 204

        # Verify it's gone from API
        get_response = await client.get(f"/accounts/{account_id}")
        assert get_response.status_code == 404

    async def test_delete_account_not_found(self, client: AsyncClient):
        """Test deleting non-existent account returns 404."""
        fake_id = EntityID.generate()
        response = await client.post(f"/accounts/{fake_id}/delete")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestUserRoutes:
    """Test suite for User API routes."""

    async def test_create_user(self, client: AsyncClient, db_session):
        """Test creating a user via POST /users."""
        # Create account first
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create user
        response = await client.post(
            "/users",
            json={
                "account_id": str(account_id),
                "email": "user@example.com",
                "display_name": "John Doe",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["account_id"] == str(account_id)
        assert data["email"] == "user@example.com"
        assert data["display_name"] == "John Doe"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_user_missing_fields(self, client: AsyncClient):
        """Test creating user without required fields returns 422."""
        response = await client.post(
            "/users",
            json={
                "email": "user@example.com",
            },
        )

        assert response.status_code == 422

    async def test_get_user_by_id(self, client: AsyncClient, db_session):
        """Test getting user by ID via GET /users/{id}."""
        # Create account and user
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        user_repo = UserRepository(db_session)
        user_id = EntityID.generate()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user)

        # Get it via API
        response = await client.get(f"/users/{user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(user_id)
        assert data["account_id"] == str(account_id)
        assert data["email"] == "user@example.com"
        assert data["display_name"] == "John Doe"

    async def test_get_user_by_id_not_found(self, client: AsyncClient):
        """Test getting non-existent user returns 404."""
        fake_id = EntityID.generate()
        response = await client.get(f"/users/{fake_id}")

        assert response.status_code == 404

    async def test_list_users_by_account(self, client: AsyncClient, db_session):
        """Test listing users by account via GET /users?account_id={id}."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create users
        user_repo = UserRepository(db_session)

        user1 = User(
            id=EntityID.generate(),
            account_id=account_id,
            email="user1@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )
        user2 = User(
            id=EntityID.generate(),
            account_id=account_id,
            email="user2@example.com",
            display_name="Jane Smith",
            created_at=now,
            updated_at=now,
        )

        await user_repo.create(user1)
        await user_repo.create(user2)

        # List them
        response = await client.get(f"/users?account_id={account_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        emails = {u["email"] for u in data}
        assert "user1@example.com" in emails
        assert "user2@example.com" in emails

    async def test_list_users_requires_account_id(self, client: AsyncClient):
        """Test that listing users without account_id returns 400."""
        response = await client.get("/users")

        assert response.status_code == 400

    async def test_update_user(self, client: AsyncClient, db_session):
        """Test updating user via PATCH /users/{id}."""
        # Create account and user
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        user_repo = UserRepository(db_session)
        user_id = EntityID.generate()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user)

        # Update it
        response = await client.patch(
            f"/users/{user_id}",
            json={
                "display_name": "John Smith",
                "email": "john.smith@example.com",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "John Smith"
        assert data["email"] == "john.smith@example.com"

    async def test_update_user_not_found(self, client: AsyncClient):
        """Test updating non-existent user returns 404."""
        fake_id = EntityID.generate()
        response = await client.patch(
            f"/users/{fake_id}",
            json={"display_name": "Updated Name"},
        )

        assert response.status_code == 404

    async def test_delete_user(self, client: AsyncClient, db_session):
        """Test soft-deleting user via POST /users/{id}/delete."""
        # Create account and user
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        user_repo = UserRepository(db_session)
        user_id = EntityID.generate()

        user = User(
            id=user_id,
            account_id=account_id,
            email="user@example.com",
            display_name="John Doe",
            created_at=now,
            updated_at=now,
        )
        await user_repo.create(user)

        # Delete it
        response = await client.post(f"/users/{user_id}/delete")

        assert response.status_code == 204

        # Verify it's gone from API
        get_response = await client.get(f"/users/{user_id}")
        assert get_response.status_code == 404

    async def test_delete_user_not_found(self, client: AsyncClient):
        """Test deleting non-existent user returns 404."""
        fake_id = EntityID.generate()
        response = await client.post(f"/users/{fake_id}/delete")

        assert response.status_code == 404
