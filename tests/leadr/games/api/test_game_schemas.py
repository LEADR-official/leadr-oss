"""Tests for Game API schemas."""

from datetime import UTC, datetime
from unittest.mock import patch

from leadr.common.domain.ids import AccountID, GameID
from leadr.games.api.game_schemas import GameResponse
from leadr.games.domain.game import Game


class TestGameResponseUrl:
    """Tests for GameResponse.url computed field."""

    def test_url_is_none_when_boards_ui_domain_not_set(self):
        """Test that url is None when BOARDS_UI_DOMAIN is not configured."""
        now = datetime.now(UTC)
        game = Game(
            id=GameID(),
            account_id=AccountID(),
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        response = GameResponse.from_domain(game)

        # By default BOARDS_UI_DOMAIN is None
        assert response.url is None

    def test_url_returns_correct_url_when_boards_ui_domain_is_set(self):
        """Test that url returns correct URL when BOARDS_UI_DOMAIN is configured."""
        now = datetime.now(UTC)
        game = Game(
            id=GameID(),
            account_id=AccountID(),
            name="Test Game",
            slug="my-awesome-game",
            created_at=now,
            updated_at=now,
        )
        response = GameResponse.from_domain(game)

        # Patch settings to have BOARDS_UI_DOMAIN set
        with patch("leadr.games.api.game_schemas.settings") as mock_settings:
            mock_settings.BOARDS_UI_DOMAIN = "https://boards.example.com"
            assert response.url == "https://boards.example.com/games/my-awesome-game"

    def test_url_included_in_model_dump(self):
        """Test that url field is included in serialized response."""
        now = datetime.now(UTC)
        game = Game(
            id=GameID(),
            account_id=AccountID(),
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        response = GameResponse.from_domain(game)
        data = response.model_dump()

        assert "url" in data

    def test_url_included_in_json_serialization(self):
        """Test that url field is included in JSON output."""
        now = datetime.now(UTC)
        game = Game(
            id=GameID(),
            account_id=AccountID(),
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        response = GameResponse.from_domain(game)
        json_data = response.model_dump_json()

        assert '"url":' in json_data
