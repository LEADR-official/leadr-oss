"""Tests for Game API routes."""

from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from leadr.common.domain.ids import AccountID, GameID
from leadr.games.domain.game import Game


def _make_integrity_error(constraint_name: str) -> IntegrityError:
    """Create an IntegrityError with a specific constraint name, mimicking asyncpg."""
    orig = MagicMock()
    orig.constraint_name = constraint_name
    return IntegrityError("INSERT INTO games ...", {}, orig)


@pytest.mark.asyncio
class TestCreateGameIntegrityErrors:
    """Test that create_game differentiates IntegrityError constraint types."""

    async def test_create_game_duplicate_name_returns_409(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service, mock_hooks
    ):
        """Duplicate (account_id, name) on active games should return 409, not 404."""
        mock_game_service.create_game.side_effect = _make_integrity_error(
            "ix_game_account_name_active"
        )

        response = await mock_client_no_db.post(
            "/games",
            json={
                "account_id": str(admin_auth.account_id),
                "name": "Pong",
            },
        )

        assert response.status_code == 409
        assert "name already exists" in response.json()["error"].lower()

    async def test_create_game_duplicate_slug_returns_409(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service, mock_hooks
    ):
        """Duplicate slug should return 409, not 404."""
        mock_game_service.create_game.side_effect = _make_integrity_error("uq_game_slug")

        response = await mock_client_no_db.post(
            "/games",
            json={
                "account_id": str(admin_auth.account_id),
                "name": "Pong",
            },
        )

        assert response.status_code == 409
        assert "slug already exists" in response.json()["error"].lower()

    async def test_create_game_invalid_account_returns_404(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service, mock_hooks
    ):
        """FK violation (account doesn't exist) should return 404."""
        mock_game_service.create_game.side_effect = _make_integrity_error("games_account_id_fkey")

        response = await mock_client_no_db.post(
            "/games",
            json={
                "account_id": str(AccountID()),
                "name": "Pong",
            },
        )

        assert response.status_code == 404
        assert "account not found" in response.json()["error"].lower()


@pytest.mark.asyncio
class TestGameRoutesPartialUpdate:
    """Test suite for Game PATCH endpoint partial update behavior."""

    async def test_patch_clears_nullable_field_when_sent_as_null(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test that PATCH with explicit null clears a nullable field.

        When a client sends {"description": null}, the description field
        should be cleared (set to NULL in database), not left unchanged.
        """
        # Arrange
        account_id = admin_auth.account_id
        game_id = GameID()
        game_with_description = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            description="Initial description",
        )
        game_cleared = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            description=None,
        )
        mock_game_service.get_by_id_or_raise.return_value = game_with_description
        mock_game_service.update_game.return_value = game_cleared

        # Act
        response = await mock_client_no_db.patch(
            f"/games/{game_id}",
            json={"description": None},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["description"] is None, (
            f"Expected description to be cleared to null, but got: {data['description']!r}"
        )

        mock_game_service.update_game.assert_called_once_with(game_id, description=None)

    async def test_patch_omitted_field_remains_unchanged(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test that PATCH with omitted field leaves it unchanged.

        When a client sends {"name": "New Name"} without description,
        the description should remain at its original value.
        """
        # Arrange
        account_id = admin_auth.account_id
        game_id = GameID()
        original_game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            description="Keep this description",
        )
        updated_game = Game(
            id=game_id,
            account_id=account_id,
            name="Updated Game Name",
            slug="test-game",
            description="Keep this description",
        )
        mock_game_service.get_by_id_or_raise.return_value = original_game
        mock_game_service.update_game.return_value = updated_game

        # Act
        response = await mock_client_no_db.patch(
            f"/games/{game_id}",
            json={"name": "Updated Game Name"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Game Name"
        assert data["description"] == "Keep this description"

        mock_game_service.update_game.assert_called_once_with(game_id, name="Updated Game Name")

    async def test_patch_multiple_nullable_fields_can_be_cleared(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test clearing multiple nullable fields in single PATCH."""
        # Arrange
        account_id = admin_auth.account_id
        game_id = GameID()
        game_with_fields = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            description="Has description",
            steam_app_id="12345",
            page_url="https://example.com",
        )
        game_cleared = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            description=None,
            steam_app_id=None,
            page_url=None,
        )
        mock_game_service.get_by_id_or_raise.return_value = game_with_fields
        mock_game_service.update_game.return_value = game_cleared

        # Act
        response = await mock_client_no_db.patch(
            f"/games/{game_id}",
            json={
                "description": None,
                "steam_app_id": None,
                "page_url": None,
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["description"] is None
        assert data["steam_app_id"] is None
        assert data["page_url"] is None

        mock_game_service.update_game.assert_called_once_with(
            game_id, description=None, steam_app_id=None, page_url=None
        )

    async def test_patch_mix_of_clear_and_update(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test PATCH with mix of clearing some fields and updating others."""
        # Arrange
        account_id = admin_auth.account_id
        game_id = GameID()
        original_game = Game(
            id=game_id,
            account_id=account_id,
            name="Original Name",
            slug="test-game",
            description="Original description",
        )
        updated_game = Game(
            id=game_id,
            account_id=account_id,
            name="New Name",
            slug="test-game",
            description=None,
        )
        mock_game_service.get_by_id_or_raise.return_value = original_game
        mock_game_service.update_game.return_value = updated_game

        # Act
        response = await mock_client_no_db.patch(
            f"/games/{game_id}",
            json={
                "name": "New Name",
                "description": None,
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] is None

        mock_game_service.update_game.assert_called_once_with(
            game_id, name="New Name", description=None
        )
