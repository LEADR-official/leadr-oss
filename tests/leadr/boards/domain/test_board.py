"""Tests for Board domain model."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.boards.domain.board import Board, BoardType, KeepStrategy, SortDirection
from leadr.common.domain.ids import AccountID, BoardID, BoardTemplateID, GameID


class TestSortDirection:
    """Test suite for SortDirection enum."""

    def test_sort_direction_ascending(self):
        """Test ASCENDING enum value."""
        assert SortDirection.ASCENDING.value == "ASCENDING"

    def test_sort_direction_descending(self):
        """Test DESCENDING enum value."""
        assert SortDirection.DESCENDING.value == "DESCENDING"


class TestBoardType:
    """Test suite for BoardType enum."""

    def test_board_type_run_identity(self):
        """Test RUN_IDENTITY enum value."""
        assert BoardType.RUN_IDENTITY.value == "RUN_IDENTITY"

    def test_board_type_run_runs(self):
        """Test RUN_RUNS enum value."""
        assert BoardType.RUN_RUNS.value == "RUN_RUNS"

    def test_board_type_counter(self):
        """Test COUNTER enum value."""
        assert BoardType.COUNTER.value == "COUNTER"

    def test_board_type_ratio(self):
        """Test RATIO enum value."""
        assert BoardType.RATIO.value == "RATIO"


class TestKeepStrategy:
    """Test suite for KeepStrategy enum."""

    def test_keep_strategy_first(self):
        """Test FIRST enum value."""
        assert KeepStrategy.FIRST.value == "FIRST"

    def test_keep_strategy_best(self):
        """Test BEST enum value."""
        assert KeepStrategy.BEST.value == "BEST"

    def test_keep_strategy_latest(self):
        """Test LATEST enum value."""
        assert KeepStrategy.LATEST.value == "LATEST"

    def test_keep_strategy_na(self):
        """Test NA enum value for non-RUN_IDENTITY boards."""
        assert KeepStrategy.NA.value == "NA"


class TestBoard:
    """Test suite for Board domain model."""

    def test_create_board_with_all_fields(self):
        """Test creating a board with all fields including optional ones."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        template_id = BoardTemplateID(uuid4())
        now = datetime.now(UTC)
        starts_at = datetime(2025, 1, 1, tzinfo=UTC)
        ends_at = datetime(2025, 12, 31, tzinfo=UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_from_template_id=template_id,
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
        assert board.keep_strategy == KeepStrategy.BEST
        assert board.created_from_template_id == template_id
        assert board.template_name == "Speed Run Template"
        assert board.starts_at == starts_at
        assert board.ends_at == ends_at
        assert board.tags == ["speedrun", "no-damage"]
        assert board.created_at == now
        assert board.updated_at == now

    def test_create_board_with_required_fields_only(self):
        """Test creating a board with only required fields."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Simple Board",
            slug="simple-board",
            icon="star",
            short_code="SB001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
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
        assert board.keep_strategy == KeepStrategy.BEST
        assert board.created_from_template_id is None
        assert board.template_name is None
        assert board.starts_at is None
        assert board.ends_at is None
        assert board.tags == []
        assert board.created_at == now
        assert board.updated_at == now

    def test_create_board_with_defaults(self):
        """Test creating a board using default values for optional fields."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Create board with only truly required fields (defaults for icon, unit, etc.)
        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Minimal Board",
            slug="minimal-board",
            short_code="MIN001",
        )

        # Verify required fields
        assert board.id == board_id
        assert board.account_id == account_id
        assert board.game_id == game_id
        assert board.name == "Minimal Board"
        assert board.slug == "minimal-board"
        assert board.short_code == "MIN001"

        # Verify defaults are applied
        assert board.icon == "fa-crown"  # Default icon
        assert board.unit is None  # Default unit
        assert board.is_active is True  # Default active state
        assert board.sort_direction == SortDirection.DESCENDING  # Default sort
        assert board.keep_strategy == KeepStrategy.BEST  # Default strategy

        # Verify optional fields
        assert board.created_from_template_id is None
        assert board.template_name is None
        assert board.starts_at is None
        assert board.ends_at is None
        assert board.tags == []

    def test_board_name_required(self):
        """Test that board name is required."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
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
                keep_strategy=KeepStrategy.BEST,
                created_at=now,
                updated_at=now,
            )

        assert "name" in str(exc_info.value)

    def test_board_account_id_required(self):
        """Test that account_id is required."""
        board_id = BoardID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Board(  # type: ignore[call-arg]
                id=board_id,
                game_id=game_id,
                name="Board Without Account",
                slug="board-without-account",
                icon="star",
                short_code="SB001",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.BEST,
                created_at=now,
                updated_at=now,
            )

        assert "account_id" in str(exc_info.value)

    def test_board_game_id_required(self):
        """Test that game_id is required."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Board(  # type: ignore[call-arg]
                id=board_id,
                account_id=account_id,
                name="Board Without Game",
                slug="board-without-game",
                icon="star",
                short_code="SB001",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.BEST,
                created_at=now,
                updated_at=now,
            )

        assert "game_id" in str(exc_info.value)

    def test_board_name_cannot_be_empty(self):
        """Test that board name cannot be empty or whitespace only."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Board(
                id=board_id,
                account_id=account_id,
                game_id=game_id,
                name="",
                slug="test-slug",
                icon="star",
                short_code="SB001",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.BEST,
                created_at=now,
                updated_at=now,
            )

        assert "name cannot be empty" in str(exc_info.value).lower()

    def test_board_name_cannot_be_whitespace_only(self):
        """Test that board name cannot be whitespace only."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Board(
                id=board_id,
                account_id=account_id,
                game_id=game_id,
                name="   ",
                slug="---",
                icon="star",
                short_code="SB001",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.BEST,
                created_at=now,
                updated_at=now,
            )

        assert "name cannot be empty" in str(exc_info.value).lower()

    def test_board_name_strips_whitespace(self):
        """Test that board name strips leading and trailing whitespace."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="  Padded Board Name  ",
            slug="padded-board-name",
            icon="star",
            short_code="SB001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )

        assert board.name == "Padded Board Name"

    def test_board_short_code_cannot_be_empty(self):
        """Test that short_code cannot be empty."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Board(
                id=board_id,
                account_id=account_id,
                game_id=game_id,
                name="Test Board",
                slug="test-board",
                icon="star",
                short_code="",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.BEST,
                created_at=now,
                updated_at=now,
            )

        assert "short_code cannot be empty" in str(exc_info.value).lower()

    def test_board_short_code_strips_whitespace(self):
        """Test that short_code strips leading and trailing whitespace."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            icon="star",
            short_code="  CODE123  ",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )

        assert board.short_code == "CODE123"

    def test_board_tags_defaults_to_empty_list(self):
        """Test that tags defaults to empty list when not provided."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            icon="star",
            short_code="TB001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )

        assert board.tags == []
        assert isinstance(board.tags, list)

    def test_board_equality_based_on_id(self):
        """Test that board equality is based on ID."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        board1 = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Board One",
            slug="board-one",
            icon="star",
            short_code="B001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )

        board2 = Board(
            id=board_id,
            account_id=AccountID(uuid4()),
            game_id=GameID(uuid4()),
            name="Board Two",
            slug="board-two",
            icon="trophy",
            short_code="B002",
            unit="seconds",
            is_active=False,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )

        assert board1 == board2

    def test_board_inequality_different_ids(self):
        """Test that boards with different IDs are not equal."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        board1 = Board(
            id=BoardID(uuid4()),
            account_id=account_id,
            game_id=game_id,
            name="Board One",
            slug="board-one",
            icon="star",
            short_code="B001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )

        board2 = Board(
            id=BoardID(uuid4()),
            account_id=account_id,
            game_id=game_id,
            name="Board One",
            slug="board-one",
            icon="star",
            short_code="B001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )

        assert board1 != board2

    def test_board_is_hashable(self):
        """Test that board can be used in sets and as dict keys."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Hashable Board",
            slug="hashable-board",
            icon="star",
            short_code="HB001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
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
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Immutable ID Board",
            slug="immutable-id-board",
            icon="star",
            short_code="IB001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )

        new_id = uuid4()

        with pytest.raises(ValidationError):
            board.id = new_id  # type: ignore[misc]

    def test_board_immutability_of_account_id(self):
        """Test that account_id cannot be changed after creation."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Immutable Account Board",
            slug="immutable-account-board",
            icon="star",
            short_code="IAB01",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )

        new_account_id = uuid4()

        with pytest.raises(ValidationError):
            board.account_id = new_account_id  # type: ignore[misc]

    def test_board_immutability_of_game_id(self):
        """Test that game_id cannot be changed after creation."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Immutable Game Board",
            slug="immutable-game-board",
            icon="star",
            short_code="IGB01",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )

        new_game_id = uuid4()

        with pytest.raises(ValidationError):
            board.game_id = new_game_id  # type: ignore[misc]

    def test_board_soft_delete(self):
        """Test that board can be soft-deleted."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Deletable Board",
            slug="deletable-board",
            icon="star",
            short_code="DB001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
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
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Restorable Board",
            slug="restorable-board",
            icon="star",
            short_code="RB001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )

        board.soft_delete()
        assert board.is_deleted is True

        board.restore()
        assert board.is_deleted is False
        assert board.deleted_at is None

    def test_create_board_with_description(self):
        """Test creating a board with description."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            icon="trophy",
            short_code="SR001",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
            description="Complete the level as fast as possible",
            created_at=now,
            updated_at=now,
        )

        assert board.description == "Complete the level as fast as possible"

    def test_board_description_defaults_to_none(self):
        """Test that description defaults to None when not provided."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Simple Board",
            slug="simple-board",
            icon="star",
            short_code="SB001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )

        assert board.description is None


class TestBoardTypeField:
    """Test suite for board_type field and validation."""

    def test_board_type_defaults_to_run_identity(self):
        """Test that board_type defaults to RUN_IDENTITY."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Default Type Board",
            slug="default-type-board",
            short_code="DTB01",
        )

        assert board.board_type == BoardType.RUN_IDENTITY

    def test_board_with_run_identity_type(self):
        """Test creating a board with RUN_IDENTITY type."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Run Identity Board",
            slug="run-identity-board",
            short_code="RIB01",
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        assert board.board_type == BoardType.RUN_IDENTITY
        assert board.keep_strategy == KeepStrategy.BEST

    def test_board_with_run_runs_type(self):
        """Test creating a board with RUN_RUNS type."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Run Runs Board",
            slug="run-runs-board",
            short_code="RRB01",
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        assert board.board_type == BoardType.RUN_RUNS
        assert board.keep_strategy == KeepStrategy.NA

    def test_board_with_counter_type(self):
        """Test creating a board with COUNTER type."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Counter Board",
            slug="counter-board",
            short_code="CTB01",
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        assert board.board_type == BoardType.COUNTER
        assert board.keep_strategy == KeepStrategy.NA

    def test_board_with_ratio_type(self):
        """Test creating a board with RATIO type."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Ratio Board",
            slug="ratio-board",
            short_code="RAT01",
            board_type=BoardType.RATIO,
            keep_strategy=KeepStrategy.NA,
        )

        assert board.board_type == BoardType.RATIO
        assert board.keep_strategy == KeepStrategy.NA

    def test_run_identity_requires_non_na_keep_strategy(self):
        """Test that RUN_IDENTITY boards cannot have NA keep_strategy."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        with pytest.raises(ValidationError) as exc_info:
            Board(
                id=board_id,
                account_id=account_id,
                game_id=game_id,
                name="Invalid Board",
                slug="invalid-board",
                short_code="INV01",
                board_type=BoardType.RUN_IDENTITY,
                keep_strategy=KeepStrategy.NA,
            )

        assert "keep_strategy" in str(exc_info.value).lower()

    def test_run_runs_requires_na_keep_strategy(self):
        """Test that RUN_RUNS boards must have NA keep_strategy."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        with pytest.raises(ValidationError) as exc_info:
            Board(
                id=board_id,
                account_id=account_id,
                game_id=game_id,
                name="Invalid Board",
                slug="invalid-board",
                short_code="INV02",
                board_type=BoardType.RUN_RUNS,
                keep_strategy=KeepStrategy.BEST,
            )

        assert "keep_strategy" in str(exc_info.value).lower()

    def test_counter_requires_na_keep_strategy(self):
        """Test that COUNTER boards must have NA keep_strategy."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        with pytest.raises(ValidationError) as exc_info:
            Board(
                id=board_id,
                account_id=account_id,
                game_id=game_id,
                name="Invalid Board",
                slug="invalid-board",
                short_code="INV03",
                board_type=BoardType.COUNTER,
                keep_strategy=KeepStrategy.LATEST,
            )

        assert "keep_strategy" in str(exc_info.value).lower()

    def test_ratio_requires_na_keep_strategy(self):
        """Test that RATIO boards must have NA keep_strategy."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        with pytest.raises(ValidationError) as exc_info:
            Board(
                id=board_id,
                account_id=account_id,
                game_id=game_id,
                name="Invalid Board",
                slug="invalid-board",
                short_code="INV04",
                board_type=BoardType.RATIO,
                keep_strategy=KeepStrategy.FIRST,
            )

        assert "keep_strategy" in str(exc_info.value).lower()

    def test_run_identity_accepts_first_strategy(self):
        """Test that RUN_IDENTITY boards accept FIRST keep_strategy."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="First Strategy Board",
            slug="first-strategy-board",
            short_code="FSB01",
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.FIRST,
        )

        assert board.keep_strategy == KeepStrategy.FIRST

    def test_run_identity_accepts_latest_strategy(self):
        """Test that RUN_IDENTITY boards accept LATEST keep_strategy."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Latest Strategy Board",
            slug="latest-strategy-board",
            short_code="LSB01",
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.LATEST,
        )

        assert board.keep_strategy == KeepStrategy.LATEST
