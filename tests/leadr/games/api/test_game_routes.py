"""Tests for Game API routes - PATCH partial update behavior."""

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestGameRoutesPartialUpdate:
    """Test suite for Game PATCH endpoint partial update behavior."""

    async def test_patch_clears_nullable_field_when_sent_as_null(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test that PATCH with explicit null clears a nullable field.

        When a client sends {"description": null}, the description field
        should be cleared (set to NULL in database), not left unchanged.
        """
        # Create account and game with description
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-null",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
            description="Initial description",
        )

        # Verify game has description
        assert game.description == "Initial description"

        # PATCH with null description - should clear it
        response = await authenticated_client.patch(
            f"/games/{game.id}",
            json={"description": None},
        )

        assert response.status_code == 200
        data = response.json()

        # This assertion will FAIL with current implementation
        # because null is treated the same as "not provided"
        assert data["description"] is None, (
            f"Expected description to be cleared to null, but got: {data['description']!r}"
        )

    async def test_patch_omitted_field_remains_unchanged(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test that PATCH with omitted field leaves it unchanged.

        When a client sends {"name": "New Name"} without description,
        the description should remain at its original value.
        """
        # Create account and game with description
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-omit",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
            description="Keep this description",
        )

        # PATCH only name - description should remain unchanged
        response = await authenticated_client.patch(
            f"/games/{game.id}",
            json={"name": "Updated Game Name"},
        )

        assert response.status_code == 200
        data = response.json()

        # Name should be updated
        assert data["name"] == "Updated Game Name"

        # Description should remain unchanged
        assert data["description"] == "Keep this description"

    async def test_patch_multiple_nullable_fields_can_be_cleared(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test clearing multiple nullable fields in single PATCH."""
        # Create account and game with multiple optional fields
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-multi",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
            description="Has description",
            steam_app_id="12345",
            page_url="https://example.com",
        )

        # Clear multiple fields
        response = await authenticated_client.patch(
            f"/games/{game.id}",
            json={
                "description": None,
                "steam_app_id": None,
                "page_url": None,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # All fields should be cleared
        assert data["description"] is None
        assert data["steam_app_id"] is None
        assert data["page_url"] is None

    async def test_patch_mix_of_clear_and_update(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test PATCH with mix of clearing some fields and updating others."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-mix",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Original Name",
            description="Original description",
        )

        # Update name, clear description
        response = await authenticated_client.patch(
            f"/games/{game.id}",
            json={
                "name": "New Name",
                "description": None,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Name should be updated
        assert data["name"] == "New Name"

        # Description should be cleared
        assert data["description"] is None
