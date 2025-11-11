"""Tests for Game API routes."""

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService


@pytest.mark.asyncio
class TestGameRoutes:
    """Test suite for Game API routes."""

    async def test_create_game(self, client: AsyncClient, db_session):
        """Test creating a game via API."""
        # Create account first
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create game
        response = await client.post(
            "/v1/games",
            json={
                "account_id": str(account.id),
                "name": "Super Awesome Game",
                "steam_app_id": "123456",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Super Awesome Game"
        assert data["steam_app_id"] == "123456"
        assert data["account_id"] == str(account.id)
        assert "id" in data
        assert "created_at" in data

    async def test_create_game_with_account_not_found(self, client: AsyncClient):
        """Test creating a game with non-existent account returns 404."""
        response = await client.post(
            "/v1/games",
            json={
                "account_id": "00000000-0000-0000-0000-000000000000",
                "name": "Super Awesome Game",
            },
        )

        assert response.status_code == 404
        assert "Account not found" in response.json()["detail"]

    async def test_get_game(self, client: AsyncClient, db_session):
        """Test retrieving a game by ID via API."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        create_response = await client.post(
            "/v1/games",
            json={
                "account_id": str(account.id),
                "name": "Super Awesome Game",
            },
        )
        game_id = create_response.json()["id"]

        # Retrieve it
        response = await client.get(f"/v1/games/{game_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == game_id
        assert data["name"] == "Super Awesome Game"

    async def test_get_game_not_found(self, client: AsyncClient):
        """Test retrieving a non-existent game returns 404."""
        response = await client.get("/v1/games/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_list_games(self, client: AsyncClient, db_session):
        """Test listing games for an account via API."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create multiple games
        await client.post(
            "/v1/games",
            json={"account_id": str(account.id), "name": "Game One"},
        )
        await client.post(
            "/v1/games",
            json={"account_id": str(account.id), "name": "Game Two"},
        )

        # List games
        response = await client.get(f"/v1/games?account_id={account.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = {g["name"] for g in data}
        assert "Game One" in names
        assert "Game Two" in names

    async def test_list_games_requires_account_id(self, client: AsyncClient):
        """Test that listing games requires account_id parameter."""
        response = await client.get("/v1/games")

        assert response.status_code == 422  # Validation error

    async def test_list_games_filters_by_account(self, client: AsyncClient, db_session):
        """Test that listing games filters by account."""
        # Create two accounts
        account_service = AccountService(db_session)
        account1 = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )
        account2 = await account_service.create_account(
            name="Beta Industries",
            slug="beta-industries",
        )

        # Create games for each account
        await client.post(
            "/v1/games",
            json={"account_id": str(account1.id), "name": "Account 1 Game"},
        )
        await client.post(
            "/v1/games",
            json={"account_id": str(account2.id), "name": "Account 2 Game"},
        )

        # List games for account 1
        response = await client.get(f"/v1/games?account_id={account1.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Account 1 Game"

    async def test_update_game(self, client: AsyncClient, db_session):
        """Test updating a game via API."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        create_response = await client.post(
            "/v1/games",
            json={
                "account_id": str(account.id),
                "name": "Super Awesome Game",
            },
        )
        game_id = create_response.json()["id"]

        # Update it
        response = await client.patch(
            f"/v1/games/{game_id}",
            json={
                "name": "Ultra Awesome Game",
                "steam_app_id": "999999",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Ultra Awesome Game"
        assert data["steam_app_id"] == "999999"

    async def test_update_game_not_found(self, client: AsyncClient):
        """Test updating a non-existent game returns 404."""
        response = await client.patch(
            "/v1/games/00000000-0000-0000-0000-000000000000",
            json={"name": "New Name"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_soft_delete_game(self, client: AsyncClient, db_session):
        """Test soft-deleting a game via API."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        create_response = await client.post(
            "/v1/games",
            json={
                "account_id": str(account.id),
                "name": "Super Awesome Game",
            },
        )
        game_id = create_response.json()["id"]

        # Soft-delete it
        response = await client.patch(
            f"/v1/games/{game_id}",
            json={"deleted": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == game_id

        # Verify it's not returned by get
        get_response = await client.get(f"/v1/games/{game_id}")
        assert get_response.status_code == 404

    async def test_list_games_excludes_deleted(self, client: AsyncClient, db_session):
        """Test that list endpoint excludes soft-deleted games."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create games
        game1_response = await client.post(
            "/v1/games",
            json={"account_id": str(account.id), "name": "Game One"},
        )
        game1_id = game1_response.json()["id"]

        await client.post(
            "/v1/games",
            json={"account_id": str(account.id), "name": "Game Two"},
        )

        # Soft-delete one
        await client.patch(f"/v1/games/{game1_id}", json={"deleted": True})

        # List should only return non-deleted
        response = await client.get(f"/v1/games?account_id={account.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Game Two"
