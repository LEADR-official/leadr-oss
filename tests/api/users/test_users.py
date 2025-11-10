"""End-to-end tests for User API endpoints."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.domain.user import User
from leadr.accounts.services.repositories import AccountRepository, UserRepository
from leadr.common.domain.models import EntityID


@pytest.mark.asyncio
class TestUserAPI:
    """End-to-end test suite for User API routes."""

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

        # Verify we can retrieve it
        user_id = data["id"]
        get_response = await client.get(f"/users/{user_id}")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["id"] == user_id

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
        """Test that listing users without account_id returns 422 validation error."""
        response = await client.get("/users")

        assert response.status_code == 422  # FastAPI validation error
        data = response.json()
        assert "detail" in data  # FastAPI validation error structure

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
        """Test soft-deleting user via PATCH with deleted field."""
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

        # Soft-delete it via PATCH
        response = await client.patch(
            f"/users/{user_id}",
            json={"deleted": True},
        )

        assert response.status_code == 200

        # Verify it's gone from API
        get_response = await client.get(f"/users/{user_id}")
        assert get_response.status_code == 404

    async def test_delete_user_not_found(self, client: AsyncClient):
        """Test soft-deleting non-existent user returns 404."""
        fake_id = EntityID.generate()
        response = await client.patch(
            f"/users/{fake_id}",
            json={"deleted": True},
        )

        assert response.status_code == 404

    async def test_get_user_invalid_uuid(self, client: AsyncClient):
        """Test getting user with invalid UUID returns 422."""
        response = await client.get("/users/not-a-uuid")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data  # FastAPI validation error

    async def test_update_user_invalid_uuid(self, client: AsyncClient):
        """Test updating user with invalid UUID returns 422."""
        response = await client.patch(
            "/users/not-a-uuid",
            json={"display_name": "Updated Name"},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data  # FastAPI validation error

    async def test_create_user_invalid_account_id(self, client: AsyncClient):
        """Test creating user with invalid account ID returns 422."""
        response = await client.post(
            "/users",
            json={
                "account_id": "not-a-uuid",
                "email": "user@example.com",
                "display_name": "John Doe",
            },
        )

        assert response.status_code == 422

    async def test_list_users_invalid_account_id(self, client: AsyncClient):
        """Test listing users with invalid account ID returns 422."""
        response = await client.get("/users?account_id=not-a-uuid")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data  # FastAPI validation error

    async def test_update_user_partial_email_only(self, client: AsyncClient, db_session):
        """Test updating only email of a user."""
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

        # Update only email
        response = await client.patch(
            f"/users/{user_id}",
            json={
                "email": "newemail@example.com",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newemail@example.com"
        assert data["display_name"] == "John Doe"  # unchanged

    async def test_update_user_partial_display_name_only(self, client: AsyncClient, db_session):
        """Test updating only display_name of a user."""
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

        # Update only display_name
        response = await client.patch(
            f"/users/{user_id}",
            json={
                "display_name": "Jane Doe",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@example.com"  # unchanged
        assert data["display_name"] == "Jane Doe"

    async def test_list_users_excludes_deleted(self, client: AsyncClient, db_session):
        """Test that list users excludes soft-deleted users."""
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

        # Soft-delete one
        await user_repo.delete(user1.id)

        # List should only return non-deleted
        response = await client.get(f"/users?account_id={account_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["email"] == "user2@example.com"

    async def test_get_user_deleted(self, client: AsyncClient, db_session):
        """Test getting soft-deleted user returns 404."""
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
        await user_repo.delete(user_id)

        # Try to get it
        response = await client.get(f"/users/{user_id}")

        assert response.status_code == 404

    async def test_update_user_empty_request(self, client: AsyncClient, db_session):
        """Test updating user with empty request body."""
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

        # Update with empty body (all fields None)
        response = await client.patch(
            f"/users/{user_id}",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@example.com"  # unchanged
        assert data["display_name"] == "John Doe"  # unchanged

    async def test_update_user_both_fields_via_api(self, client: AsyncClient):
        """Test updating user through API with both fields."""
        # Create account via API
        account_response = await client.post(
            "/accounts",
            json={
                "name": "Test Account",
                "slug": "test-account",
            },
        )
        assert account_response.status_code == 201
        account_id = account_response.json()["id"]

        # Create user via API
        create_response = await client.post(
            "/users",
            json={
                "account_id": account_id,
                "email": "test@example.com",
                "display_name": "Test User",
            },
        )
        assert create_response.status_code == 201
        user_id = create_response.json()["id"]

        # Update both fields
        update_response = await client.patch(
            f"/users/{user_id}",
            json={
                "email": "updated@example.com",
                "display_name": "Updated User",
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["email"] == "updated@example.com"
        assert update_response.json()["display_name"] == "Updated User"

    async def test_delete_user_via_api(self, client: AsyncClient):
        """Test soft-deleting user created via API."""
        # Create account via API
        account_response = await client.post(
            "/accounts",
            json={
                "name": "Test Account",
                "slug": "test-account",
            },
        )
        assert account_response.status_code == 201
        account_id = account_response.json()["id"]

        # Create user via API
        create_response = await client.post(
            "/users",
            json={
                "account_id": account_id,
                "email": "to-delete@example.com",
                "display_name": "To Delete",
            },
        )
        assert create_response.status_code == 201
        user_id = create_response.json()["id"]

        # Soft-delete it via PATCH
        delete_response = await client.patch(
            f"/users/{user_id}",
            json={"deleted": True},
        )
        assert delete_response.status_code == 200

        # Confirm it's gone
        get_response = await client.get(f"/users/{user_id}")
        assert get_response.status_code == 404
