"""Tests for BoardTemplate API routes."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestBoardTemplateRoutes:
    """Test suite for BoardTemplate API routes."""

    async def test_create_board_template(self, client: AsyncClient, db_session, test_api_key):
        """Test creating a board template via API."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board template
        next_run_at = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        response = await client.post(
            "/board-templates",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Weekly Speed Run Template",
                "repeat_interval": "7 days",
                "next_run_at": next_run_at,
                "is_active": True,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Weekly Speed Run Template"
        assert data["repeat_interval"] == "7 days"
        assert data["account_id"] == str(account.id)
        assert data["game_id"] == str(game.id)
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    async def test_create_board_template_with_optional_fields(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a board template with optional fields via API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        next_run_at = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        response = await client.post(
            "/board-templates",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Weekly Template",
                "name_template": "Week {week} Competition",
                "repeat_interval": "7 days",
                "config": {"unit": "seconds", "sort_direction": "ASCENDING"},
                "config_template": {"tags": ["weekly", "speedrun"]},
                "next_run_at": next_run_at,
                "is_active": True,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name_template"] == "Week {week} Competition"
        assert data["config"] == {"unit": "seconds", "sort_direction": "ASCENDING"}
        assert data["config_template"] == {"tags": ["weekly", "speedrun"]}

    async def test_create_board_template_with_game_not_found(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a board template with non-existent game returns 404."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        next_run_at = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        response = await client.post(
            "/board-templates",
            json={
                "account_id": str(account.id),
                "game_id": "gam_00000000-0000-0000-0000-000000000000",
                "name": "Invalid Template",
                "repeat_interval": "7 days",
                "next_run_at": next_run_at,
                "is_active": True,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404

    async def test_get_board_template(self, client: AsyncClient, db_session, test_api_key):
        """Test retrieving a board template by ID via API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create template
        next_run_at = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        create_response = await client.post(
            "/board-templates",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Test Template",
                "repeat_interval": "7 days",
                "next_run_at": next_run_at,
                "is_active": True,
            },
            headers={"leadr-api-key": test_api_key},
        )
        template_id = create_response.json()["id"]

        # Get template
        response = await client.get(
            f"/board-templates/{template_id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == template_id
        assert data["name"] == "Test Template"

    async def test_get_nonexistent_board_template_returns_404(
        self, client: AsyncClient, test_api_key
    ):
        """Test retrieving a nonexistent board template returns 404."""
        response = await client.get(
            "/board-templates/tpl_00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404

    async def test_list_board_templates_by_account(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test listing board templates by account."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create two templates
        next_run_at = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        await client.post(
            "/board-templates",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Template 1",
                "repeat_interval": "7 days",
                "next_run_at": next_run_at,
                "is_active": True,
            },
            headers={"leadr-api-key": test_api_key},
        )
        await client.post(
            "/board-templates",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Template 2",
                "repeat_interval": "1 month",
                "next_run_at": next_run_at,
                "is_active": True,
            },
            headers={"leadr-api-key": test_api_key},
        )

        # List templates
        response = await client.get(
            f"/board-templates?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_list_board_templates_by_game(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test listing board templates by game."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account.id,
            name="Game 1",
        )
        game2 = await game_service.create_game(
            account_id=account.id,
            name="Game 2",
        )

        # Create templates for different games
        next_run_at = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        await client.post(
            "/board-templates",
            json={
                "account_id": str(account.id),
                "game_id": str(game1.id),
                "name": "Game 1 Template",
                "repeat_interval": "7 days",
                "next_run_at": next_run_at,
                "is_active": True,
            },
            headers={"leadr-api-key": test_api_key},
        )
        await client.post(
            "/board-templates",
            json={
                "account_id": str(account.id),
                "game_id": str(game2.id),
                "name": "Game 2 Template",
                "repeat_interval": "1 month",
                "next_run_at": next_run_at,
                "is_active": True,
            },
            headers={"leadr-api-key": test_api_key},
        )

        # List templates for game1
        response = await client.get(
            f"/board-templates?account_id={account.id}&game_id={game1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["game_id"] == str(game1.id)

    async def test_update_board_template(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a board template via API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create template
        next_run_at = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        create_response = await client.post(
            "/board-templates",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Original Template",
                "repeat_interval": "7 days",
                "next_run_at": next_run_at,
                "is_active": True,
            },
            headers={"leadr-api-key": test_api_key},
        )
        template_id = create_response.json()["id"]

        # Update template
        response = await client.patch(
            f"/board-templates/{template_id}",
            json={
                "name": "Updated Template",
                "is_active": False,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Template"
        assert data["is_active"] is False

    async def test_soft_delete_board_template(self, client: AsyncClient, db_session, test_api_key):
        """Test soft deleting a board template via API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create template
        next_run_at = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        create_response = await client.post(
            "/board-templates",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Template to Delete",
                "repeat_interval": "7 days",
                "next_run_at": next_run_at,
                "is_active": True,
            },
            headers={"leadr-api-key": test_api_key},
        )
        template_id = create_response.json()["id"]

        # Soft delete
        response = await client.patch(
            f"/board-templates/{template_id}",
            json={"deleted": True},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200

        # Verify not retrievable
        get_response = await client.get(
            f"/board-templates/{template_id}",
            headers={"leadr-api-key": test_api_key},
        )
        assert get_response.status_code == 404
