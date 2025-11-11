"""Tests for Board domain model."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.boards.domain.board import Board, KeepStrategy, SortDirection


class TestSortDirection:
    """Test suite for SortDirection enum."""

    def test_sort_direction_ascending(self):
        """Test ASCENDING enum value."""
        assert SortDirection.ASCENDING.value == "ASCENDING"

    def test_sort_direction_descending(self):
        """Test DESCENDING enum value."""
        assert SortDirection.DESCENDING.value == "DESCENDING"


class TestKeepStrategy:
    """Test suite for KeepStrategy enum."""

    def test_keep_strategy_best_only(self):
        """Test BEST_ONLY enum value."""
        assert KeepStrategy.BEST_ONLY.value == "BEST_ONLY"

    def test_keep_strategy_latest_only(self):
        """Test LATEST_ONLY enum value."""
        assert KeepStrategy.LATEST_ONLY.value == "LATEST_ONLY"

    def test_keep_strategy_all(self):
        """Test ALL enum value."""
        assert KeepStrategy.ALL.value == "ALL"


class TestBoard:
    """Test suite for Board domain model."""

    def test_create_board_with_all_fields(self):
        """Test creating a board with all fields including optional ones."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        template_id = uuid4()
        now = datetime.now(UTC)
        starts_at = datetime(2025, 1, 1, tzinfo=UTC)
        ends_at = datetime(2025, 12, 31, tzinfo=UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            template_id=template_id,
            template_name="Speed Run Template",
            starts_at=starts_at,
            ends_at=ends_at,
            tags=["speedrun", "no-damage"],
            created_at=now,
            updated_at=now,
        )

        assert board.id == board_id
        assert board.account_id == account_id
        assert board.game_id == game_id
        assert board.name == "Speed Run Board"
        assert board.icon == "trophy"
        assert board.short_code == "SR2025"
        assert board.unit == "seconds"
        assert board.is_active is True
        assert board.sort_direction == SortDirection.ASCENDING
        assert board.keep_strategy == KeepStrategy.BEST_ONLY
        assert board.template_id == template_id
        assert board.template_name == "Speed Run Template"
        assert board.starts_at == starts_at
        assert board.ends_at == ends_at
        assert board.tags == ["speedrun", "no-damage"]
        assert board.created_at == now
        assert board.updated_at == now

    def test_create_board_with_required_fields_only(self):
        """Test creating a board with only required fields."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Simple Board",
            icon="star",
            short_code="SB001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )

        assert board.id == board_id
        assert board.account_id == account_id
        assert board.game_id == game_id
        assert board.name == "Simple Board"
        assert board.icon == "star"
        assert board.short_code == "SB001"
        assert board.unit == "points"
        assert board.is_active is True
        assert board.sort_direction == SortDirection.DESCENDING
        assert board.keep_strategy == KeepStrategy.ALL
        assert board.template_id is None
        assert board.template_name is None
        assert board.starts_at is None
        assert board.ends_at is None
        assert board.tags == []
        assert board.created_at == now
        assert board.updated_at == now

    def test_board_name_required(self):
        """Test that board name is required."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Board(  # type: ignore[call-arg]
                id=board_id,
                account_id=account_id,
                game_id=game_id,
                icon="star",
                short_code="SB001",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.ALL,
                created_at=now,
                updated_at=now,
            )

        assert "name" in str(exc_info.value)

    def test_board_account_id_required(self):
        """Test that account_id is required."""
        board_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Board(  # type: ignore[call-arg]
                id=board_id,
                game_id=game_id,
                name="Board Without Account",
                icon="star",
                short_code="SB001",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.ALL,
                created_at=now,
                updated_at=now,
            )

        assert "account_id" in str(exc_info.value)

    def test_board_game_id_required(self):
        """Test that game_id is required."""
        board_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Board(  # type: ignore[call-arg]
                id=board_id,
                account_id=account_id,
                name="Board Without Game",
                icon="star",
                short_code="SB001",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.ALL,
                created_at=now,
                updated_at=now,
            )

        assert "game_id" in str(exc_info.value)

    def test_board_name_cannot_be_empty(self):
        """Test that board name cannot be empty or whitespace only."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Board(
                id=board_id,
                account_id=account_id,
                game_id=game_id,
                name="",
                icon="star",
                short_code="SB001",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.ALL,
                created_at=now,
                updated_at=now,
            )

        assert "name cannot be empty" in str(exc_info.value).lower()

    def test_board_name_cannot_be_whitespace_only(self):
        """Test that board name cannot be whitespace only."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Board(
                id=board_id,
                account_id=account_id,
                game_id=game_id,
                name="   ",
                icon="star",
                short_code="SB001",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.ALL,
                created_at=now,
                updated_at=now,
            )

        assert "name cannot be empty" in str(exc_info.value).lower()

    def test_board_name_strips_whitespace(self):
        """Test that board name strips leading and trailing whitespace."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="  Padded Board Name  ",
            icon="star",
            short_code="SB001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )

        assert board.name == "Padded Board Name"

    def test_board_short_code_cannot_be_empty(self):
        """Test that short_code cannot be empty."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Board(
                id=board_id,
                account_id=account_id,
                game_id=game_id,
                name="Test Board",
                icon="star",
                short_code="",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.ALL,
                created_at=now,
                updated_at=now,
            )

        assert "short_code cannot be empty" in str(exc_info.value).lower()

    def test_board_short_code_strips_whitespace(self):
        """Test that short_code strips leading and trailing whitespace."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            icon="star",
            short_code="  CODE123  ",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )

        assert board.short_code == "CODE123"

    def test_board_tags_defaults_to_empty_list(self):
        """Test that tags defaults to empty list when not provided."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            icon="star",
            short_code="TB001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )

        assert board.tags == []
        assert isinstance(board.tags, list)

    def test_board_equality_based_on_id(self):
        """Test that board equality is based on ID."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        board1 = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Board One",
            icon="star",
            short_code="B001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )

        board2 = Board(
            id=board_id,
            account_id=uuid4(),
            game_id=uuid4(),
            name="Board Two",
            icon="trophy",
            short_code="B002",
            unit="seconds",
            is_active=False,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )

        assert board1 == board2

    def test_board_inequality_different_ids(self):
        """Test that boards with different IDs are not equal."""
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        board1 = Board(
            id=uuid4(),
            account_id=account_id,
            game_id=game_id,
            name="Board One",
            icon="star",
            short_code="B001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )

        board2 = Board(
            id=uuid4(),
            account_id=account_id,
            game_id=game_id,
            name="Board One",
            icon="star",
            short_code="B001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )

        assert board1 != board2

    def test_board_is_hashable(self):
        """Test that board can be used in sets and as dict keys."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Hashable Board",
            icon="star",
            short_code="HB001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )

        # Should be hashable
        board_set = {board}  # type: ignore[var-annotated]
        assert board in board_set

        # Should work as dict key
        board_dict = {board: "value"}  # type: ignore[dict-item]
        assert board_dict[board] == "value"

    def test_board_immutability_of_id(self):
        """Test that board ID cannot be changed after creation."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Immutable ID Board",
            icon="star",
            short_code="IB001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )

        new_id = uuid4()

        with pytest.raises(ValidationError):
            board.id = new_id

    def test_board_immutability_of_account_id(self):
        """Test that account_id cannot be changed after creation."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Immutable Account Board",
            icon="star",
            short_code="IAB01",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )

        new_account_id = uuid4()

        with pytest.raises(ValidationError):
            board.account_id = new_account_id

    def test_board_immutability_of_game_id(self):
        """Test that game_id cannot be changed after creation."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Immutable Game Board",
            icon="star",
            short_code="IGB01",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )

        new_game_id = uuid4()

        with pytest.raises(ValidationError):
            board.game_id = new_game_id

    def test_board_soft_delete(self):
        """Test that board can be soft-deleted."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Deletable Board",
            icon="star",
            short_code="DB001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )

        assert board.is_deleted is False
        assert board.deleted_at is None

        board.soft_delete()

        assert board.is_deleted is True
        assert board.deleted_at is not None

    def test_board_restore(self):
        """Test that soft-deleted board can be restored."""
        board_id = uuid4()
        account_id = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Restorable Board",
            icon="star",
            short_code="RB001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )

        board.soft_delete()
        assert board.is_deleted is True

        board.restore()
        assert board.is_deleted is False
        assert board.deleted_at is None
