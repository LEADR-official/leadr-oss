"""Tests for Board service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.boards.domain.board import Board, BoardType, KeepStrategy, SortDirection
from leadr.boards.domain.board_template import BoardTemplate
from leadr.boards.services.board_service import BoardService
from leadr.common.api.pagination import PaginatedResult
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, BoardID, BoardTemplateID, GameID
from leadr.games.domain.game import Game


@pytest.mark.asyncio
class TestBoardService:
    """Test suite for Board service."""

    @pytest.fixture
    def service(self, mock_session):
        """Create BoardService with mock repository."""
        mock_repo = MagicMock()
        mock_repo.session = mock_session
        return BoardService(mock_session, repository=mock_repo)

    @patch("leadr.boards.services.board_service.GameService")
    @patch("leadr.boards.services.board_service.generate_unique_short_code", new_callable=AsyncMock)
    @patch(
        "leadr.boards.services.board_service.generate_unique_slug_with_retry",
        new_callable=AsyncMock,
    )
    async def test_create_board(
        self, mock_slug_gen, mock_short_code_gen, mock_game_service_class, service
    ):
        """Test creating a board via service."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Setup mocks
        mock_game = Game(id=game_id, account_id=account_id, name="Test Game", slug="test-game")
        mock_game_service = mock_game_service_class.return_value
        mock_game_service.get_by_id_or_raise = AsyncMock(return_value=mock_game)
        mock_short_code_gen.return_value = "SR2025"
        mock_slug_gen.return_value = "speed-run-board"
        service.repository.create = AsyncMock(side_effect=lambda entity: entity)

        # Create board
        board = await service.create_board(
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        assert board.id is not None
        assert board.account_id == account_id
        assert board.game_id == game_id
        assert board.name == "Speed Run Board"
        assert board.short_code == "SR2025"
        assert board.is_active is True
        service.repository.create.assert_called_once()

    @patch("leadr.boards.services.board_service.GameService")
    @patch("leadr.boards.services.board_service.generate_unique_short_code", new_callable=AsyncMock)
    @patch(
        "leadr.boards.services.board_service.generate_unique_slug_with_retry",
        new_callable=AsyncMock,
    )
    async def test_create_board_with_optional_fields(
        self, mock_slug_gen, mock_short_code_gen, mock_game_service_class, service
    ):
        """Test creating a board with optional fields."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        template_id = BoardTemplateID(uuid4())

        # Setup mocks
        mock_game = Game(id=game_id, account_id=account_id, name="Test Game", slug="test-game")
        mock_game_service = mock_game_service_class.return_value
        mock_game_service.get_by_id_or_raise = AsyncMock(return_value=mock_game)
        mock_short_code_gen.return_value = "SR2025"
        mock_slug_gen.return_value = "speed-run-board"
        service.repository.create = AsyncMock(side_effect=lambda entity: entity)

        # Create board with optional fields
        board = await service.create_board(
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_from_template_id=BoardTemplateID(template_id),
            template_name="Speed Run Template",
            tags=["speedrun", "no-damage"],
        )

        assert board.created_from_template_id == BoardTemplateID(template_id)
        assert board.template_name == "Speed Run Template"
        assert board.tags == ["speedrun", "no-damage"]
        service.repository.create.assert_called_once()

    @patch("leadr.boards.services.board_service.GameService")
    @patch("leadr.boards.services.board_service.generate_unique_short_code", new_callable=AsyncMock)
    @patch(
        "leadr.boards.services.board_service.generate_unique_slug_with_retry",
        new_callable=AsyncMock,
    )
    async def test_create_board_validates_game_belongs_to_account(
        self, mock_slug_gen, mock_short_code_gen, mock_game_service_class, service
    ):
        """Test that create_board validates the game belongs to the account."""
        account1_id = AccountID(uuid4())
        account2_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Setup mocks - game belongs to account1
        mock_game = Game(id=game_id, account_id=account1_id, name="Test Game", slug="test-game")
        mock_game_service = mock_game_service_class.return_value
        mock_game_service.get_by_id_or_raise = AsyncMock(return_value=mock_game)

        # Try to create board for account2 with account1's game
        with pytest.raises(ValueError) as exc_info:
            await service.create_board(
                account_id=account2_id,
                game_id=game_id,
                name="Invalid Board",
                icon="star",
                short_code="INVALID",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.BEST,
            )

        assert "does not belong to account" in str(exc_info.value).lower()

    @patch("leadr.boards.services.board_service.GameService")
    async def test_create_board_raises_error_for_nonexistent_game(
        self, mock_game_service_class, service
    ):
        """Test that create_board raises error for non-existent game."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Setup mocks - GameService raises EntityNotFoundError
        mock_game_service = mock_game_service_class.return_value
        mock_game_service.get_by_id_or_raise = AsyncMock(
            side_effect=EntityNotFoundError("Game", str(game_id))
        )

        # Try to create board with non-existent game
        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.create_board(
                account_id=account_id,
                game_id=game_id,
                name="Invalid Board",
                icon="star",
                short_code="INVALID",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.BEST,
            )

        assert "Game not found" in str(exc_info.value)

    async def test_get_board(self, service):
        """Test retrieving a board by ID via service."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        mock_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
        )

        # Mock repository method
        service.repository.get_by_id = AsyncMock(return_value=mock_board)

        # Retrieve it
        board = await service.get_board(board_id)

        assert board is not None
        assert board.id == board_id
        assert board.name == "Speed Run Board"
        service.repository.get_by_id.assert_called_once()

    async def test_get_board_not_found(self, service):
        """Test retrieving a non-existent board returns None."""
        non_existent_id = BoardID(uuid4())

        # Mock repository method
        service.repository.get_by_id = AsyncMock(return_value=None)

        board = await service.get_board(non_existent_id)

        assert board is None
        service.repository.get_by_id.assert_called_once()

    async def test_get_board_by_short_code(self, service):
        """Test retrieving a board by short_code via service."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        mock_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
        )

        # Mock repository method
        service.repository.get_by_short_code = AsyncMock(return_value=mock_board)

        # Retrieve by short_code
        board = await service.get_board_by_short_code("SR2025")

        assert board is not None
        assert board.id == board_id
        assert board.short_code == "SR2025"
        service.repository.get_by_short_code.assert_called_once_with("SR2025")

    async def test_get_board_by_short_code_not_found(self, service):
        """Test retrieving a board by non-existent short_code returns None."""
        # Mock repository method
        service.repository.get_by_short_code = AsyncMock(return_value=None)

        board = await service.get_board_by_short_code("NONEXISTENT")

        assert board is None
        service.repository.get_by_short_code.assert_called_once_with("NONEXISTENT")

    async def test_list_boards_by_account(self, service):
        """Test listing all boards for an account."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        board1 = Board(
            id=BoardID(uuid4()),
            account_id=account_id,
            game_id=game_id,
            name="Board One",
            slug="board-one",
            short_code="B001",
        )
        board2 = Board(
            id=BoardID(uuid4()),
            account_id=account_id,
            game_id=game_id,
            name="Board Two",
            slug="board-two",
            short_code="B002",
        )

        # Mock repository method
        mock_result = PaginatedResult(
            items=[board1, board2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_result)

        # List them
        boards = await service.list_boards_by_account(account_id)

        assert len(boards) == 2
        names = {b.name for b in boards}
        assert "Board One" in names
        assert "Board Two" in names
        service.repository.filter.assert_called_once()

    async def test_list_boards_filters_by_account(self, service):
        """Test that list_boards_by_account only returns boards for the specified account."""
        account1_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        board1 = Board(
            id=BoardID(uuid4()),
            account_id=account1_id,
            game_id=game_id,
            name="Account 1 Board",
            slug="account-1-board",
            short_code="A1B1",
        )

        # Mock repository method
        mock_result = PaginatedResult(
            items=[board1],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_result)

        # List boards for account 1
        boards = await service.list_boards_by_account(account1_id)

        assert len(boards) == 1
        assert boards[0].name == "Account 1 Board"
        assert boards[0].account_id == account1_id
        service.repository.filter.assert_called_once()

    async def test_update_board(self, service):
        """Test updating a board via service."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
            icon="trophy",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_board)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update it
        updated_board = await service.update_board(
            board_id=board_id,
            name="Updated Speed Run Board",
            is_active=False,
        )

        assert updated_board.name == "Updated Speed Run Board"
        assert updated_board.is_active is False
        assert updated_board.icon == "trophy"
        service.repository.get_by_id.assert_called_once()
        service.repository.update.assert_called_once()

    async def test_update_board_partial_fields(self, service):
        """Test updating only some fields of a board."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_board)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update only the name
        updated_board = await service.update_board(
            board_id=board_id,
            name="New Name",
        )

        assert updated_board.name == "New Name"
        assert updated_board.is_active is True
        assert updated_board.sort_direction == SortDirection.ASCENDING
        service.repository.get_by_id.assert_called_once()
        service.repository.update.assert_called_once()

    async def test_update_board_not_found(self, service):
        """Test that updating a non-existent board raises an error."""
        non_existent_id = BoardID(uuid4())

        # Mock repository method
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.update_board(
                board_id=non_existent_id,
                name="New Name",
            )

        assert "Board not found" in str(exc_info.value)

    async def test_soft_delete_board(self, service):
        """Test soft-deleting a board via service."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_board)
        service.repository.delete = AsyncMock(return_value=None)

        # Soft-delete it (returns entity before deletion)
        deleted_board = await service.soft_delete(board_id)

        assert deleted_board.id == board_id
        assert deleted_board.is_deleted is False
        service.repository.get_by_id.assert_called_once()
        service.repository.delete.assert_called_once_with(board_id.uuid)

    async def test_list_boards_excludes_deleted(self, service):
        """Test that list_boards_by_account excludes soft-deleted boards."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        board2 = Board(
            id=BoardID(uuid4()),
            account_id=account_id,
            game_id=game_id,
            name="Board Two",
            slug="board-two",
            short_code="B002",
        )

        # Mock repository method - only returns non-deleted board
        mock_result = PaginatedResult(
            items=[board2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_result)

        # List should only return non-deleted
        boards = await service.list_boards_by_account(account_id)

        assert len(boards) == 1
        assert boards[0].name == "Board Two"

    async def test_soft_delete_board_not_found(self, service):
        """Test that soft-deleting a non-existent board raises an error."""
        non_existent_id = BoardID(uuid4())

        # Mock repository method
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.soft_delete(non_existent_id)

        assert "Board not found" in str(exc_info.value)

    async def test_update_board_icon(self, service):
        """Test updating board icon."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
            icon="trophy",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_board)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update icon
        updated_board = await service.update_board(
            board_id=board_id,
            icon="star",
        )

        assert updated_board.icon == "star"
        assert updated_board.name == "Speed Run Board"
        service.repository.update.assert_called_once()

    async def test_update_board_short_code(self, service):
        """Test updating board short_code."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_board)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update short_code
        updated_board = await service.update_board(
            board_id=board_id,
            short_code="SR2026",
        )

        assert updated_board.short_code == "SR2026"
        assert updated_board.name == "Speed Run Board"
        service.repository.update.assert_called_once()

    async def test_update_board_unit(self, service):
        """Test updating board unit."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
            unit="seconds",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_board)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update unit
        updated_board = await service.update_board(
            board_id=board_id,
            unit="milliseconds",
        )

        assert updated_board.unit == "milliseconds"
        assert updated_board.name == "Speed Run Board"
        service.repository.update.assert_called_once()

    async def test_update_board_sort_direction(self, service):
        """Test updating board sort_direction."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
            sort_direction=SortDirection.ASCENDING,
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_board)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update sort_direction
        updated_board = await service.update_board(
            board_id=board_id,
            sort_direction=SortDirection.DESCENDING,
        )

        assert updated_board.sort_direction == SortDirection.DESCENDING
        assert updated_board.name == "Speed Run Board"
        service.repository.update.assert_called_once()

    async def test_update_board_keep_strategy(self, service):
        """Test updating board keep_strategy."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
            keep_strategy=KeepStrategy.BEST,
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_board)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update keep_strategy
        updated_board = await service.update_board(
            board_id=board_id,
            keep_strategy=KeepStrategy.BEST,
        )

        assert updated_board.keep_strategy == KeepStrategy.BEST
        assert updated_board.name == "Speed Run Board"
        service.repository.update.assert_called_once()

    async def test_update_board_type_and_keep_strategy_atomically(self, service):
        """Test updating board_type and keep_strategy together works atomically.

        This tests the fix for cross-field validation when changing board_type
        from RUN_IDENTITY to RUN_RUNS. Both fields must be updated together
        because RUN_RUNS requires keep_strategy=NA while RUN_IDENTITY requires
        keep_strategy to be FIRST/BEST/LATEST.

        Regression test for: ValidationError when updating board_type and keep_strategy
        """
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Start with a RUN_IDENTITY board with BEST keep_strategy
        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_board)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update both board_type and keep_strategy together
        # This previously failed due to sequential setattr triggering validation
        updated_board = await service.update_board(
            board_id=board_id,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        assert updated_board.board_type == BoardType.RUN_RUNS
        assert updated_board.keep_strategy == KeepStrategy.NA
        assert updated_board.name == "Speed Run Board"
        service.repository.update.assert_called_once()

    async def test_update_board_template_id(self, service):
        """Test updating board template_id."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_board)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update template_id
        new_template_id = BoardTemplateID(uuid4())
        updated_board = await service.update_board(
            board_id=board_id,
            created_from_template_id=new_template_id,
        )

        assert updated_board.created_from_template_id == new_template_id
        assert updated_board.name == "Speed Run Board"
        service.repository.update.assert_called_once()

    async def test_update_board_template_name(self, service):
        """Test updating board template_name."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_board)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update template_name
        updated_board = await service.update_board(
            board_id=board_id,
            template_name="New Template",
        )

        assert updated_board.template_name == "New Template"
        assert updated_board.name == "Speed Run Board"
        service.repository.update.assert_called_once()

    async def test_update_board_starts_at(self, service):
        """Test updating board starts_at."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_board)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update starts_at
        new_starts_at = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        updated_board = await service.update_board(
            board_id=board_id,
            starts_at=new_starts_at,
        )

        assert updated_board.starts_at == new_starts_at
        assert updated_board.name == "Speed Run Board"
        service.repository.update.assert_called_once()

    async def test_update_board_ends_at(self, service):
        """Test updating board ends_at."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_board)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update ends_at
        new_ends_at = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)
        updated_board = await service.update_board(
            board_id=board_id,
            ends_at=new_ends_at,
        )

        assert updated_board.ends_at == new_ends_at
        assert updated_board.name == "Speed Run Board"
        service.repository.update.assert_called_once()

    async def test_update_board_tags(self, service):
        """Test updating board tags."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SR2025",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_board)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update tags
        updated_board = await service.update_board(
            board_id=board_id,
            tags=["speedrun", "glitchless"],
        )

        assert updated_board.tags == ["speedrun", "glitchless"]
        assert updated_board.name == "Speed Run Board"
        service.repository.update.assert_called_once()

    @patch("leadr.boards.services.board_service.GameService")
    @patch("leadr.boards.services.board_service.generate_unique_short_code", new_callable=AsyncMock)
    async def test_create_board_from_template(
        self, mock_short_code_gen, mock_game_service_class, service
    ):
        """Test creating a board from a template."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        template_id = BoardTemplateID(uuid4())

        # Create template
        next_run = datetime.now(UTC) + timedelta(days=1)
        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Weekly Challenge",
            slug="weekly-challenge",
            repeat_interval="7 days",
            next_run_at=next_run,
            is_active=True,
            icon="star",
            unit="points",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            tags=["weekly", "challenge"],
            config={},
        )

        # Setup mocks
        mock_game = Game(id=game_id, account_id=account_id, name="Test Game", slug="test-game")
        mock_game_service = mock_game_service_class.return_value
        mock_game_service.get_by_id_or_raise = AsyncMock(return_value=mock_game)
        mock_short_code_gen.return_value = "WC123"

        # Mock slug check (slug doesn't exist)
        mock_slug_check_result = PaginatedResult(
            items=[],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_slug_check_result)
        service.repository.create = AsyncMock(side_effect=lambda entity: entity)
        service.repository.count_boards_by_template = AsyncMock(return_value=0)

        # Create board from template
        board = await service.create_board_from_template(template)

        # Assertions
        assert board.id is not None
        assert board.name == "Weekly Challenge"
        assert board.account_id == account_id
        assert board.game_id == game_id
        assert board.icon == "star"
        assert board.unit == "points"
        assert board.is_active is True
        assert board.sort_direction == SortDirection.DESCENDING
        assert board.keep_strategy == KeepStrategy.BEST
        assert board.created_from_template_id == template_id
        assert board.template_name == "Weekly Challenge"
        assert board.starts_at == next_run
        assert board.ends_at == next_run + timedelta(days=7)
        assert board.tags == ["weekly", "challenge"]
        assert board.short_code == "WC123"
        service.repository.create.assert_called_once()

    @patch("leadr.boards.services.board_service.GameService")
    @patch("leadr.boards.services.board_service.generate_unique_short_code", new_callable=AsyncMock)
    async def test_create_board_from_template_with_defaults(
        self, mock_short_code_gen, mock_game_service_class, service
    ):
        """Test creating a board from a template with default config values."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        template_id = BoardTemplateID(uuid4())

        # Create template with minimal config
        next_run = datetime.now(UTC) + timedelta(hours=1)
        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Hourly Event",
            slug="hourly-event",
            repeat_interval="1 hour",
            next_run_at=next_run,
            is_active=True,
            config={},
        )

        # Setup mocks
        mock_game = Game(id=game_id, account_id=account_id, name="Test Game", slug="test-game")
        mock_game_service = mock_game_service_class.return_value
        mock_game_service.get_by_id_or_raise = AsyncMock(return_value=mock_game)
        mock_short_code_gen.return_value = "HE123"

        # Mock slug check (slug doesn't exist)
        mock_slug_check_result = PaginatedResult(
            items=[],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_slug_check_result)
        service.repository.create = AsyncMock(side_effect=lambda entity: entity)
        service.repository.count_boards_by_template = AsyncMock(return_value=0)

        # Create board from template
        board = await service.create_board_from_template(template)

        # Assertions - check template defaults are applied
        assert board.icon == "fa-crown"
        assert board.unit is None
        assert board.is_active is True
        assert board.sort_direction == SortDirection.DESCENDING
        assert board.keep_strategy == KeepStrategy.BEST
        assert board.tags == []
        assert board.starts_at == next_run
        assert board.ends_at == next_run + timedelta(hours=1)
        service.repository.create.assert_called_once()

    @patch("leadr.boards.services.board_service.GameService")
    @patch("leadr.boards.services.board_service.generate_unique_short_code", new_callable=AsyncMock)
    async def test_create_board_from_template_with_series_placeholder(
        self, mock_short_code_gen, mock_game_service_class, service
    ):
        """Test creating a board from a template with {series} placeholder in name_template.

        Regression test: ensures series_value is calculated when name_template contains
        {series} placeholder, regardless of whether template.series field is set.
        """
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        template_id = BoardTemplateID(uuid4())

        # Create template with {series} in name_template but series=None
        next_run = datetime.now(UTC) + timedelta(days=1)
        template = BoardTemplate(
            id=template_id,
            account_id=account_id,
            game_id=game_id,
            name="Weekly Challenge",
            slug="weekly-challenge",
            repeat_interval="7 days",
            next_run_at=next_run,
            is_active=True,
            name_template="Weekly {series}",
            config={},
        )

        # Setup mocks
        mock_game = Game(id=game_id, account_id=account_id, name="Test Game", slug="test-game")
        mock_game_service = mock_game_service_class.return_value
        mock_game_service.get_by_id_or_raise = AsyncMock(return_value=mock_game)
        mock_short_code_gen.return_value = "WC123"

        # Mock slug check (slug doesn't exist)
        mock_slug_check_result = PaginatedResult(
            items=[],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_slug_check_result)
        service.repository.create = AsyncMock(side_effect=lambda entity: entity)
        service.repository.count_boards_by_template = AsyncMock(return_value=0)

        # Create board from template - should succeed and use series_value=1
        board = await service.create_board_from_template(template)

        # Assertions - the key test is that the name uses series_value=1
        assert board.name == "Weekly 1"
        assert board.created_from_template_id == template_id
        service.repository.count_boards_by_template.assert_called_once_with(template_id)

    @patch("leadr.boards.services.board_service.GameService")
    @patch("leadr.boards.services.board_service.generate_unique_short_code", new_callable=AsyncMock)
    @patch(
        "leadr.boards.services.board_service.generate_unique_slug_with_retry",
        new_callable=AsyncMock,
    )
    async def test_create_board_with_description(
        self, mock_slug_gen, mock_short_code_gen, mock_game_service_class, service
    ):
        """Test creating a board with description via service."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Setup mocks
        mock_game = Game(id=game_id, account_id=account_id, name="Test Game", slug="test-game")
        mock_game_service = mock_game_service_class.return_value
        mock_game_service.get_by_id_or_raise = AsyncMock(return_value=mock_game)
        mock_short_code_gen.return_value = "SRDESC"
        mock_slug_gen.return_value = "speed-run-board"
        service.repository.create = AsyncMock(side_effect=lambda entity: entity)

        board = await service.create_board(
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SRDESC",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
            description="Complete the level as fast as possible",
        )

        assert board.id is not None
        assert board.description == "Complete the level as fast as possible"
        service.repository.create.assert_called_once()

    async def test_update_board_description(self, service):
        """Test updating board description."""
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speed Run Board",
            slug="speed-run-board",
            short_code="SRUPD",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_board)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update description
        updated_board = await service.update_board(
            board_id=board_id,
            description="Updated description for the board",
        )

        assert updated_board.description == "Updated description for the board"
        assert updated_board.name == "Speed Run Board"
        service.repository.update.assert_called_once()

    async def test_update_keep_strategy_invalid_for_board_type_raises_validation_error(
        self, service
    ):
        """Test that updating keep_strategy to an invalid value for board_type fails.

        RUN_RUNS boards must have keep_strategy=NA. Attempting to change it to
        BEST/FIRST/LATEST should raise a ValidationError at the service level.
        """
        board_id = BoardID(uuid4())
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())

        # Create a RUN_RUNS board (requires keep_strategy=NA)
        existing_board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="All Runs Board",
            slug="all-runs-board",
            short_code="AR2025",
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        service.repository.get_by_id = AsyncMock(return_value=existing_board)

        # Trying to change keep_strategy to BEST should fail validation
        with pytest.raises(ValidationError, match="keep_strategy=NA"):
            await service.update_board(board_id=board_id, keep_strategy=KeepStrategy.BEST)
