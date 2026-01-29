"""Tests for Game API routes."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.account_service import AccountService
from leadr.accounts.services.repositories import AccountRepository
from leadr.common.domain.ids import AccountID
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestGameRoutes:
    """Test suite for Game API routes."""

    async def test_create_game(self, client: AsyncClient, db_session, test_api_key):
        """Test creating a game via API."""
        # Create account first
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create game
        response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Super Awesome Game",
                "steam_app_id": "123456",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Super Awesome Game"
        assert data["steam_app_id"] == "123456"
        assert data["account_id"] == str(account.id)
        assert "id" in data
        assert "created_at" in data

    async def test_create_game_with_account_not_found(self, client: AsyncClient, test_api_key):
        """Test creating a game with non-existent account returns 404."""
        response = await client.post(
            "/games",
            json={
                "account_id": "acc_00000000-0000-0000-0000-000000000000",
                "name": "Super Awesome Game",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "Account not found" in response.json()["error"]

    async def test_get_game(self, client: AsyncClient, db_session, test_api_key):
        """Test retrieving a game by ID via API."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        create_response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Super Awesome Game",
            },
            headers={"leadr-api-key": test_api_key},
        )
        game_id = create_response.json()["id"]

        # Retrieve it
        response = await client.get(f"/games/{game_id}", headers={"leadr-api-key": test_api_key})

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == game_id
        assert data["name"] == "Super Awesome Game"

    async def test_get_game_not_found(self, client: AsyncClient, test_api_key):
        """Test retrieving a non-existent game returns 404."""
        response = await client.get(
            "/games/gam_00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_list_games(self, client: AsyncClient, db_session, test_api_key):
        """Test listing games for an account via API."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create multiple games
        await client.post(
            "/games",
            json={"account_id": str(account.id), "name": "Game One"},
            headers={"leadr-api-key": test_api_key},
        )
        await client.post(
            "/games",
            json={"account_id": str(account.id), "name": "Game Two"},
            headers={"leadr-api-key": test_api_key},
        )

        # List games
        response = await client.get(
            f"/games?account_id={account.id}", headers={"leadr-api-key": test_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 2
        names = {g["name"] for g in data["data"]}
        assert "Game One" in names
        assert "Game Two" in names

    async def test_list_games_filters_by_account(
        self, client: AsyncClient, db_session, test_api_key
    ):
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
            "/games",
            json={"account_id": str(account1.id), "name": "Account 1 Game"},
            headers={"leadr-api-key": test_api_key},
        )
        await client.post(
            "/games",
            json={"account_id": str(account2.id), "name": "Account 2 Game"},
            headers={"leadr-api-key": test_api_key},
        )

        # List games for account 1
        response = await client.get(
            f"/games?account_id={account1.id}", headers={"leadr-api-key": test_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Account 1 Game"

    async def test_update_game(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a game via API."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        create_response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Super Awesome Game",
            },
            headers={"leadr-api-key": test_api_key},
        )
        game_id = create_response.json()["id"]

        # Update it
        response = await client.patch(
            f"/games/{game_id}",
            json={
                "name": "Ultra Awesome Game",
                "steam_app_id": "999999",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Ultra Awesome Game"
        assert data["steam_app_id"] == "999999"

    async def test_update_game_not_found(self, client: AsyncClient, test_api_key):
        """Test updating a non-existent game returns 404."""
        response = await client.patch(
            "/games/gam_00000000-0000-0000-0000-000000000000",
            json={"name": "New Name"},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_soft_delete_game(self, client: AsyncClient, db_session, test_api_key):
        """Test soft-deleting a game via API."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        create_response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Super Awesome Game",
            },
            headers={"leadr-api-key": test_api_key},
        )
        game_id = create_response.json()["id"]

        # Soft-delete it
        response = await client.patch(
            f"/games/{game_id}",
            json={"deleted": True},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == game_id

        # Verify it's not returned by get
        get_response = await client.get(
            f"/games/{game_id}", headers={"leadr-api-key": test_api_key}
        )
        assert get_response.status_code == 404

    async def test_list_games_excludes_deleted(self, client: AsyncClient, db_session, test_api_key):
        """Test that list endpoint excludes soft-deleted games."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create games
        game1_response = await client.post(
            "/games",
            json={"account_id": str(account.id), "name": "Game One"},
            headers={"leadr-api-key": test_api_key},
        )
        game1_id = game1_response.json()["id"]

        await client.post(
            "/games",
            json={"account_id": str(account.id), "name": "Game Two"},
            headers={"leadr-api-key": test_api_key},
        )

        # Soft-delete one
        await client.patch(
            f"/games/{game1_id}", json={"deleted": True}, headers={"leadr-api-key": test_api_key}
        )

        # List should only return non-deleted
        response = await client.get(
            f"/games?account_id={account.id}", headers={"leadr-api-key": test_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Game Two"

    async def test_create_game_with_anti_cheat_enabled_default(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that anti_cheat_enabled defaults to True when creating a game."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Super Awesome Game",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["anti_cheat_enabled"] is True

    async def test_create_game_with_anti_cheat_disabled(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a game with anti_cheat_enabled explicitly set to False."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Custom Anti-Cheat Game",
                "anti_cheat_enabled": False,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Custom Anti-Cheat Game"
        assert data["anti_cheat_enabled"] is False

    async def test_update_game_anti_cheat_enabled(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test updating a game's anti_cheat_enabled field."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create game with anti-cheat enabled (default)
        create_response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Game to Update",
            },
            headers={"leadr-api-key": test_api_key},
        )
        game_id = create_response.json()["id"]
        assert create_response.json()["anti_cheat_enabled"] is True

        # Disable anti-cheat
        update_response = await client.patch(
            f"/games/{game_id}",
            json={"anti_cheat_enabled": False},
            headers={"leadr-api-key": test_api_key},
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["anti_cheat_enabled"] is False

        # Re-enable anti-cheat
        update_response2 = await client.patch(
            f"/games/{game_id}",
            json={"anti_cheat_enabled": True},
            headers={"leadr-api-key": test_api_key},
        )

        assert update_response2.status_code == 200
        data2 = update_response2.json()
        assert data2["anti_cheat_enabled"] is True

    async def test_get_game_includes_anti_cheat_enabled(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that retrieving a game includes the anti_cheat_enabled field."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create game with anti-cheat disabled
        create_response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Test Game",
                "anti_cheat_enabled": False,
            },
            headers={"leadr-api-key": test_api_key},
        )
        game_id = create_response.json()["id"]

        # Retrieve game
        get_response = await client.get(
            f"/games/{game_id}", headers={"leadr-api-key": test_api_key}
        )

        assert get_response.status_code == 200
        data = get_response.json()
        assert "anti_cheat_enabled" in data
        assert data["anti_cheat_enabled"] is False

    async def test_superadmin_list_games_without_account_id_returns_all(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test that superadmin can list games WITHOUT account_id and sees all accounts."""
        # Create two accounts with games in each
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="Account One Games",
            slug="account-one-games",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="Account Two Games",
            slug="account-two-games",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create games in each account
        game_service = GameService(db_session)
        await game_service.create_game(
            account_id=account1.id,
            name="Game from Account 1",
        )
        await game_service.create_game(
            account_id=account2.id,
            name="Game from Account 2",
        )

        # List games WITHOUT account_id - should return games from ALL accounts
        response = await authenticated_client.get("/games")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        # Should contain games from both accounts
        game_names = {g["name"] for g in data["data"]}
        assert "Game from Account 1" in game_names
        assert "Game from Account 2" in game_names

    async def test_create_game_with_tags_and_description(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a game with tags and description via API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Adventure Game",
                "description": "An epic journey awaits",
                "tags": ["adventure", "rpg", "story"],
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Adventure Game"
        assert data["description"] == "An epic journey awaits"
        assert data["tags"] == ["adventure", "rpg", "story"]

    async def test_create_game_tags_defaults_to_empty_list(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that tags defaults to empty list when not provided via API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Simple Game",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tags"] == []
        assert data["description"] is None

    async def test_update_game_tags(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a game's tags via API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        create_response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Game to Update Tags",
            },
            headers={"leadr-api-key": test_api_key},
        )
        game_id = create_response.json()["id"]

        # Update tags
        update_response = await client.patch(
            f"/games/{game_id}",
            json={"tags": ["action", "puzzle"]},
            headers={"leadr-api-key": test_api_key},
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["tags"] == ["action", "puzzle"]

    async def test_update_game_description(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a game's description via API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        create_response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Game to Update Description",
            },
            headers={"leadr-api-key": test_api_key},
        )
        game_id = create_response.json()["id"]

        # Update description
        update_response = await client.patch(
            f"/games/{game_id}",
            json={"description": "A brand new description"},
            headers={"leadr-api-key": test_api_key},
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["description"] == "A brand new description"

    async def test_get_game_returns_tags_and_description(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that retrieving a game includes tags and description."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create game with tags and description
        create_response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Full Game",
                "description": "A complete game",
                "tags": ["complete", "full"],
            },
            headers={"leadr-api-key": test_api_key},
        )
        game_id = create_response.json()["id"]

        # Retrieve game
        get_response = await client.get(
            f"/games/{game_id}", headers={"leadr-api-key": test_api_key}
        )

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["description"] == "A complete game"
        assert data["tags"] == ["complete", "full"]

    async def test_create_game_with_page_url(self, client: AsyncClient, db_session, test_api_key):
        """Test creating a game with page_url via API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Game with Page",
                "page_url": "https://example.com/game",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Game with Page"
        assert data["page_url"] == "https://example.com/game"

    async def test_update_game_page_url(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a game's page_url via API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        create_response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Game to Update URL",
            },
            headers={"leadr-api-key": test_api_key},
        )
        game_id = create_response.json()["id"]

        # Update page_url
        update_response = await client.patch(
            f"/games/{game_id}",
            json={"page_url": "https://example.com/updated"},
            headers={"leadr-api-key": test_api_key},
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["page_url"] == "https://example.com/updated"

    async def test_game_page_url_defaults_to_none(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that page_url defaults to None when not provided via API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        response = await client.post(
            "/games",
            json={
                "account_id": str(account.id),
                "name": "Simple Game",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["page_url"] is None
