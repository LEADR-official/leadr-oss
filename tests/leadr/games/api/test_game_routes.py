"""Tests for Game API routes - PATCH partial update behavior."""

import pytest
from httpx import AsyncClient

from leadr.common.domain.ids import GameID
from leadr.games.domain.game import Game


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
