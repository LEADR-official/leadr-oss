"""Tests for Board API schemas."""

from datetime import UTC, datetime
from unittest.mock import patch

from leadr.boards.api.board_schemas import BoardResponse
from leadr.boards.domain.board import Board, KeepStrategy, SortDirection
from leadr.common.domain.ids import AccountID, BoardID, GameID


class TestBoardResponseUrlShort:
    """Tests for BoardResponse.url_short computed field."""

    def test_url_short_is_none_when_boards_ui_domain_not_set(self):
        """Test that url_short is None when BOARDS_UI_DOMAIN is not configured."""
        now = datetime.now(UTC)
        board = Board(
            id=BoardID(),
            account_id=AccountID(),
            game_id=GameID(),
            name="Test Board",
            slug="test-board",
            short_code="ABC123",
            is_active=True,
            is_published=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )
        response = BoardResponse.from_domain(board)

        # By default BOARDS_UI_DOMAIN is None
        assert response.url_short is None

    def test_url_short_returns_correct_url_when_boards_ui_domain_is_set(self):
        """Test that url_short returns correct URL when BOARDS_UI_DOMAIN is configured."""
        now = datetime.now(UTC)
        board = Board(
            id=BoardID(),
            account_id=AccountID(),
            game_id=GameID(),
            name="Test Board",
            slug="test-board",
            short_code="XYZ789",
            is_active=True,
            is_published=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )
        response = BoardResponse.from_domain(board)

        # Patch settings to have BOARDS_UI_DOMAIN set
        with patch("leadr.boards.api.board_schemas.settings") as mock_settings:
            mock_settings.BOARDS_UI_DOMAIN = "https://boards.example.com"
            assert response.url_short == "https://boards.example.com/b/XYZ789"

    def test_url_short_included_in_model_dump(self):
        """Test that url_short field is included in serialized response."""
        now = datetime.now(UTC)
        board = Board(
            id=BoardID(),
            account_id=AccountID(),
            game_id=GameID(),
            name="Test Board",
            slug="test-board",
            short_code="ABC123",
            is_active=True,
            is_published=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )
        response = BoardResponse.from_domain(board)
        data = response.model_dump()

        assert "url_short" in data

    def test_url_short_included_in_json_serialization(self):
        """Test that url_short field is included in JSON output."""
        now = datetime.now(UTC)
        board = Board(
            id=BoardID(),
            account_id=AccountID(),
            game_id=GameID(),
            name="Test Board",
            slug="test-board",
            short_code="ABC123",
            is_active=True,
            is_published=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )
        response = BoardResponse.from_domain(board)
        json_data = response.model_dump_json()

        assert '"url_short":' in json_data
