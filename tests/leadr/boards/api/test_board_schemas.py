"""Tests for Board API schemas."""

import warnings
from datetime import UTC, datetime
from unittest.mock import patch

from leadr.boards.api.board_schemas import BoardResponse, BoardUpdateRequest
from leadr.boards.domain.board import Board, BoardType, KeepStrategy, SortDirection
from leadr.common.domain.ids import AccountID, BoardID, GameID


class TestBoardUpdateRequest:
    """Tests for BoardUpdateRequest validation."""

    def test_accepts_board_type(self):
        """Test that BoardUpdateRequest accepts board_type (validated at route level)."""
        request = BoardUpdateRequest(board_type=BoardType.RUN_RUNS)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert request.board_type == BoardType.RUN_RUNS

    def test_accepts_board_type_with_other_fields(self):
        """Test that BoardUpdateRequest accepts board_type with other fields."""
        request = BoardUpdateRequest(name="New Name", board_type=BoardType.RUN_IDENTITY)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert request.name == "New Name"
            assert request.board_type == BoardType.RUN_IDENTITY

    def test_allows_other_fields_without_board_type(self):
        """Test that BoardUpdateRequest accepts valid fields without board_type."""
        request = BoardUpdateRequest(name="New Name", keep_strategy=KeepStrategy.BEST)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert request.name == "New Name"
            assert request.keep_strategy == KeepStrategy.BEST
            assert request.board_type is None

    def test_allows_empty_update(self):
        """Test that BoardUpdateRequest accepts empty update (no fields set)."""
        request = BoardUpdateRequest()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert request.name is None
            assert request.board_type is None


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
            keep_strategy=KeepStrategy.BEST,
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
            keep_strategy=KeepStrategy.BEST,
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
            keep_strategy=KeepStrategy.BEST,
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
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )
        response = BoardResponse.from_domain(board)
        json_data = response.model_dump_json()

        assert '"url_short":' in json_data

    def test_url_short_is_none_when_board_is_not_published(self):
        """Test that url_short is None when board is not published."""
        now = datetime.now(UTC)
        board = Board(
            id=BoardID(),
            account_id=AccountID(),
            game_id=GameID(),
            name="Unpublished Board",
            slug="unpublished-board",
            short_code="ABC123",
            is_active=True,
            is_published=False,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )
        response = BoardResponse.from_domain(board)

        # Even if BOARDS_UI_DOMAIN is set, url_short should be None
        with patch("leadr.boards.api.board_schemas.settings") as mock_settings:
            mock_settings.BOARDS_UI_DOMAIN = "https://boards.example.com"
            assert response.url_short is None
