"""Tests for Board service."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.services.account_service import AccountService
from leadr.boards.domain.board import KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestBoardService:
    """Test suite for Board service."""

    async def test_create_board(self, db_session: AsyncSession):
        """Test creating a board via service."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        assert board.id is not None
        assert board.account_id == account.id
        assert board.game_id == game.id
        assert board.name == "Speed Run Board"
        assert board.short_code == "SR2025"
        assert board.is_active is True

    async def test_create_board_with_optional_fields(self, db_session: AsyncSession):
        """Test creating a board with optional fields."""
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

        # Create board with optional fields
        board_service = BoardService(db_session)
        template_id = uuid4()

        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            template_id=template_id,
            template_name="Speed Run Template",
            tags=["speedrun", "no-damage"],
        )

        assert board.template_id == template_id
        assert board.template_name == "Speed Run Template"
        assert board.tags == ["speedrun", "no-damage"]

    async def test_create_board_validates_game_belongs_to_account(self, db_session: AsyncSession):
        """Test that create_board validates the game belongs to the account."""
        # Create two accounts
        account_service = AccountService(db_session)
        account1 = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )
        account2 = await account_service.create_account(
            name="Beta Industries",
            slug="beta-industries",
        )

        # Create game for account1
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account1.id,
            name="Account 1 Game",
        )

        # Try to create board for account2 with account1's game
        board_service = BoardService(db_session)

        with pytest.raises(ValueError) as exc_info:
            await board_service.create_board(
                account_id=account2.id,
                game_id=game.id,
                name="Invalid Board",
                icon="star",
                short_code="INVALID",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.ALL,
            )

        assert "does not belong to account" in str(exc_info.value).lower()

    async def test_create_board_raises_error_for_nonexistent_game(self, db_session: AsyncSession):
        """Test that create_board raises error for non-existent game."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Try to create board with non-existent game
        board_service = BoardService(db_session)
        non_existent_game_id = uuid4()

        with pytest.raises(EntityNotFoundError) as exc_info:
            await board_service.create_board(
                account_id=account.id,
                game_id=non_existent_game_id,
                name="Invalid Board",
                icon="star",
                short_code="INVALID",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.ALL,
            )

        assert "Game not found" in str(exc_info.value)

    async def test_get_board(self, db_session: AsyncSession):
        """Test retrieving a board by ID via service."""
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

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Retrieve it
        board = await board_service.get_board(created_board.id)

        assert board is not None
        assert board.id == created_board.id
        assert board.name == "Speed Run Board"

    async def test_get_board_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent board returns None."""
        board_service = BoardService(db_session)
        non_existent_id = uuid4()

        board = await board_service.get_board(non_existent_id)

        assert board is None

    async def test_get_board_by_short_code(self, db_session: AsyncSession):
        """Test retrieving a board by short_code via service."""
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

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Retrieve by short_code
        board = await board_service.get_board_by_short_code("SR2025")

        assert board is not None
        assert board.id == created_board.id
        assert board.short_code == "SR2025"

    async def test_get_board_by_short_code_not_found(self, db_session: AsyncSession):
        """Test retrieving a board by non-existent short_code returns None."""
        board_service = BoardService(db_session)

        board = await board_service.get_board_by_short_code("NONEXISTENT")

        assert board is None

    async def test_list_boards_by_account(self, db_session: AsyncSession):
        """Test listing all boards for an account."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create multiple boards
        board_service = BoardService(db_session)
        await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board One",
            icon="star",
            short_code="B001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )
        await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board Two",
            icon="trophy",
            short_code="B002",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # List them
        boards = await board_service.list_boards_by_account(account.id)

        assert len(boards) == 2
        names = {b.name for b in boards}
        assert "Board One" in names
        assert "Board Two" in names

    async def test_list_boards_filters_by_account(self, db_session: AsyncSession):
        """Test that list_boards_by_account only returns boards for the specified account."""
        # Create two accounts
        account_service = AccountService(db_session)
        account1 = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )
        account2 = await account_service.create_account(
            name="Beta Industries",
            slug="beta-industries",
        )

        # Create games for each account
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account1.id,
            name="Game 1",
        )
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game 2",
        )

        # Create boards for each account
        board_service = BoardService(db_session)
        await board_service.create_board(
            account_id=account1.id,
            game_id=game1.id,
            name="Account 1 Board",
            icon="star",
            short_code="A1B1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )
        await board_service.create_board(
            account_id=account2.id,
            game_id=game2.id,
            name="Account 2 Board",
            icon="trophy",
            short_code="A2B1",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # List boards for account 1
        boards = await board_service.list_boards_by_account(account1.id)

        assert len(boards) == 1
        assert boards[0].name == "Account 1 Board"
        assert boards[0].account_id == account1.id

    async def test_update_board(self, db_session: AsyncSession):
        """Test updating a board via service."""
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

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Update it
        updated_board = await board_service.update_board(
            board_id=created_board.id,
            name="Updated Speed Run Board",
            is_active=False,
        )

        assert updated_board.name == "Updated Speed Run Board"
        assert updated_board.is_active is False
        assert updated_board.icon == "trophy"  # Unchanged

        # Verify in database
        board = await board_service.get_board(created_board.id)
        assert board is not None
        assert board.name == "Updated Speed Run Board"
        assert board.is_active is False

    async def test_update_board_partial_fields(self, db_session: AsyncSession):
        """Test updating only some fields of a board."""
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

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Update only the name
        updated_board = await board_service.update_board(
            board_id=created_board.id,
            name="New Name",
        )

        assert updated_board.name == "New Name"
        assert updated_board.is_active is True  # Unchanged
        assert updated_board.sort_direction == SortDirection.ASCENDING  # Unchanged

    async def test_update_board_not_found(self, db_session: AsyncSession):
        """Test that updating a non-existent board raises an error."""
        board_service = BoardService(db_session)
        non_existent_id = uuid4()

        with pytest.raises(EntityNotFoundError) as exc_info:
            await board_service.update_board(
                board_id=non_existent_id,
                name="New Name",
            )

        assert "Board not found" in str(exc_info.value)

    async def test_soft_delete_board(self, db_session: AsyncSession):
        """Test soft-deleting a board via service."""
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

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Soft-delete it (returns entity before deletion)
        deleted_board = await board_service.soft_delete(created_board.id)

        assert deleted_board.id == created_board.id
        assert deleted_board.is_deleted is False  # Returns entity before deletion

        # Verify it's not returned by get
        board = await board_service.get_board(created_board.id)
        assert board is None

    async def test_list_boards_excludes_deleted(self, db_session: AsyncSession):
        """Test that list_boards_by_account excludes soft-deleted boards."""
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

        # Create boards
        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board One",
            icon="star",
            short_code="B001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )
        await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board Two",
            icon="trophy",
            short_code="B002",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Soft-delete one
        await board_service.soft_delete(board1.id)

        # List should only return non-deleted
        boards = await board_service.list_boards_by_account(account.id)

        assert len(boards) == 1
        assert boards[0].name == "Board Two"

    async def test_soft_delete_board_not_found(self, db_session: AsyncSession):
        """Test that soft-deleting a non-existent board raises an error."""
        board_service = BoardService(db_session)
        non_existent_id = uuid4()

        with pytest.raises(EntityNotFoundError) as exc_info:
            await board_service.soft_delete(non_existent_id)

        assert "Board not found" in str(exc_info.value)

    async def test_update_board_icon(self, db_session: AsyncSession):
        """Test updating board icon."""
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

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Update icon
        updated_board = await board_service.update_board(
            board_id=created_board.id,
            icon="star",
        )

        assert updated_board.icon == "star"
        assert updated_board.name == "Speed Run Board"  # Unchanged

    async def test_update_board_short_code(self, db_session: AsyncSession):
        """Test updating board short_code."""
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

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Update short_code
        updated_board = await board_service.update_board(
            board_id=created_board.id,
            short_code="SR2026",
        )

        assert updated_board.short_code == "SR2026"
        assert updated_board.name == "Speed Run Board"  # Unchanged

    async def test_update_board_unit(self, db_session: AsyncSession):
        """Test updating board unit."""
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

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Update unit
        updated_board = await board_service.update_board(
            board_id=created_board.id,
            unit="milliseconds",
        )

        assert updated_board.unit == "milliseconds"
        assert updated_board.name == "Speed Run Board"  # Unchanged

    async def test_update_board_sort_direction(self, db_session: AsyncSession):
        """Test updating board sort_direction."""
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

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Update sort_direction
        updated_board = await board_service.update_board(
            board_id=created_board.id,
            sort_direction=SortDirection.DESCENDING,
        )

        assert updated_board.sort_direction == SortDirection.DESCENDING
        assert updated_board.name == "Speed Run Board"  # Unchanged

    async def test_update_board_keep_strategy(self, db_session: AsyncSession):
        """Test updating board keep_strategy."""
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

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Update keep_strategy
        updated_board = await board_service.update_board(
            board_id=created_board.id,
            keep_strategy=KeepStrategy.ALL,
        )

        assert updated_board.keep_strategy == KeepStrategy.ALL
        assert updated_board.name == "Speed Run Board"  # Unchanged

    async def test_update_board_template_id(self, db_session: AsyncSession):
        """Test updating board template_id."""
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

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Update template_id
        new_template_id = uuid4()
        updated_board = await board_service.update_board(
            board_id=created_board.id,
            template_id=new_template_id,
        )

        assert updated_board.template_id == new_template_id
        assert updated_board.name == "Speed Run Board"  # Unchanged

    async def test_update_board_template_name(self, db_session: AsyncSession):
        """Test updating board template_name."""
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

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Update template_name
        updated_board = await board_service.update_board(
            board_id=created_board.id,
            template_name="New Template",
        )

        assert updated_board.template_name == "New Template"
        assert updated_board.name == "Speed Run Board"  # Unchanged

    async def test_update_board_starts_at(self, db_session: AsyncSession):
        """Test updating board starts_at."""
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

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Update starts_at
        from datetime import datetime

        new_starts_at = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        updated_board = await board_service.update_board(
            board_id=created_board.id,
            starts_at=new_starts_at,
        )

        assert updated_board.starts_at == new_starts_at
        assert updated_board.name == "Speed Run Board"  # Unchanged

    async def test_update_board_ends_at(self, db_session: AsyncSession):
        """Test updating board ends_at."""
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

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Update ends_at
        from datetime import datetime

        new_ends_at = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)
        updated_board = await board_service.update_board(
            board_id=created_board.id,
            ends_at=new_ends_at,
        )

        assert updated_board.ends_at == new_ends_at
        assert updated_board.name == "Speed Run Board"  # Unchanged

    async def test_update_board_tags(self, db_session: AsyncSession):
        """Test updating board tags."""
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

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Update tags
        updated_board = await board_service.update_board(
            board_id=created_board.id,
            tags=["speedrun", "glitchless"],
        )

        assert updated_board.tags == ["speedrun", "glitchless"]
        assert updated_board.name == "Speed Run Board"  # Unchanged

    async def test_create_board_from_template(self, db_session: AsyncSession):
        """Test creating a board from a template."""
        from datetime import timedelta

        from leadr.boards.services.board_template_service import BoardTemplateService

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

        # Create a board template
        template_service = BoardTemplateService(db_session)
        next_run = datetime.now(UTC) + timedelta(days=1)
        template = await template_service.create_board_template(
            account_id=account.id,
            game_id=game.id,
            name="Weekly Challenge",
            repeat_interval="7 days",
            next_run_at=next_run,
            is_active=True,
            config={
                "icon": "star",
                "unit": "points",
                "is_active": True,
                "sort_direction": "desc",
                "keep_strategy": "best",
                "tags": ["weekly", "challenge"],
            },
        )

        # Create board from template
        board_service = BoardService(db_session)
        board = await board_service.create_board_from_template(template)

        # Assertions
        assert board.id is not None
        assert board.name == "Weekly Challenge"
        assert board.account_id == account.id
        assert board.game_id == game.id
        assert board.icon == "star"
        assert board.unit == "points"
        assert board.is_active is True
        assert board.sort_direction == SortDirection.DESCENDING
        assert board.keep_strategy == KeepStrategy.BEST_ONLY
        assert board.template_id == template.id
        assert board.template_name == "Weekly Challenge"
        assert board.starts_at == next_run
        assert board.ends_at == next_run + timedelta(days=7)
        assert board.tags == ["weekly", "challenge"]
        assert board.short_code is not None  # Should be auto-generated
        assert len(board.short_code) == 8  # Default short code length

    async def test_create_board_from_template_with_defaults(self, db_session: AsyncSession):
        """Test creating a board from a template with default config values."""
        from datetime import timedelta

        from leadr.boards.services.board_template_service import BoardTemplateService

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

        # Create a board template with minimal config (use defaults)
        template_service = BoardTemplateService(db_session)
        next_run = datetime.now(UTC) + timedelta(hours=1)
        template = await template_service.create_board_template(
            account_id=account.id,
            game_id=game.id,
            name="Hourly Event",
            repeat_interval="1 hour",
            next_run_at=next_run,
            is_active=True,
            config={},  # Empty config - should use defaults
        )

        # Create board from template
        board_service = BoardService(db_session)
        board = await board_service.create_board_from_template(template)

        # Assertions - check defaults are applied
        assert board.icon == "trophy"  # Default
        assert board.unit == "points"  # Default
        assert board.is_active is True  # Default
        assert board.sort_direction == SortDirection.DESCENDING  # Default "desc"
        assert board.keep_strategy == KeepStrategy.BEST_ONLY  # Default "best"
        assert board.tags == []  # Default empty list
        assert board.starts_at == next_run
        assert board.ends_at == next_run + timedelta(hours=1)
