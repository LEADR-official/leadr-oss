"""Tests for Board ORM model."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.adapters.orm import AccountORM
from leadr.boards.adapters.orm import BoardORM
from leadr.common.domain.ids import AccountID, BoardTemplateID, GameID
from leadr.games.adapters.orm import GameORM


@pytest.mark.asyncio
class TestBoardORM:
    """Test suite for Board ORM model."""

    async def test_create_board_with_all_fields(self, db_session: AsyncSession):
        """Test creating a board with all fields in the database."""
        # Create account first
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
            status="active",
        )
        db_session.add(account)
        await db_session.commit()

        # Create game
        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create board with all fields
        template_id = BoardTemplateID(uuid4())
        starts_at = datetime(2025, 1, 1, tzinfo=UTC)
        ends_at = datetime(2025, 12, 31, tzinfo=UTC)

        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction="ASCENDING",
            keep_strategy="BEST_ONLY",
            template_id=template_id,
            template_name="Speed Run Template",
            starts_at=starts_at,
            ends_at=ends_at,
            tags=["speedrun", "no-damage"],
        )

        db_session.add(board)
        await db_session.commit()
        await db_session.refresh(board)

        assert board.id is not None
        assert board.account_id == account.id
        assert board.game_id == game.id
        assert board.name == "Speed Run Board"  # type: ignore[comparison-overlap]
        assert board.icon == "trophy"  # type: ignore[comparison-overlap]
        assert board.short_code == "SR2025"  # type: ignore[comparison-overlap]
        assert board.unit == "seconds"  # type: ignore[comparison-overlap]
        assert board.is_active is True
        assert board.sort_direction == "ASCENDING"  # type: ignore[comparison-overlap]
        assert board.keep_strategy == "BEST_ONLY"  # type: ignore[comparison-overlap]
        assert board.template_id == template_id
        assert board.template_name == "Speed Run Template"  # type: ignore[comparison-overlap]
        assert board.starts_at == starts_at
        assert board.ends_at == ends_at
        assert board.tags == ["speedrun", "no-damage"]
        assert board.created_at is not None
        assert board.updated_at is not None

    async def test_create_board_with_required_fields_only(self, db_session: AsyncSession):
        """Test creating a board with only required fields."""
        # Create account
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
            status="active",
        )
        db_session.add(account)
        await db_session.commit()

        # Create game
        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create board with required fields only
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Simple Board",
            icon="star",
            short_code="SB001",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="ALL",
        )

        db_session.add(board)
        await db_session.commit()
        await db_session.refresh(board)

        assert board.id is not None
        assert board.account_id == account.id
        assert board.game_id == game.id
        assert board.template_id is None
        assert board.template_name is None
        assert board.starts_at is None
        assert board.ends_at is None
        assert board.tags == []

    async def test_board_short_code_unique(self, db_session: AsyncSession):
        """Test that board short_code must be globally unique."""
        # Create accounts
        account1 = AccountORM(id=uuid4(), name="Account 1", slug="account-1", status="active")
        account2 = AccountORM(id=uuid4(), name="Account 2", slug="account-2", status="active")
        db_session.add_all([account1, account2])
        await db_session.commit()

        # Create games for different accounts
        game1 = GameORM(id=uuid4(), account_id=account1.id, name="Game 1")
        game2 = GameORM(id=uuid4(), account_id=account2.id, name="Game 2")
        db_session.add_all([game1, game2])
        await db_session.commit()

        # Create first board
        board1 = BoardORM(
            id=uuid4(),
            account_id=account1.id,
            game_id=game1.id,
            name="Board 1",
            icon="star",
            short_code="GLOBAL01",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="ALL",
        )
        db_session.add(board1)
        await db_session.commit()

        # Try to create second board with same short_code (different account)
        board2 = BoardORM(
            id=uuid4(),
            account_id=account2.id,
            game_id=game2.id,
            name="Board 2",
            icon="trophy",
            short_code="GLOBAL01",  # Duplicate short_code
            unit="seconds",
            is_active=True,
            sort_direction="ASCENDING",
            keep_strategy="BEST_ONLY",
        )
        db_session.add(board2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_board_foreign_key_to_account(self, db_session: AsyncSession):
        """Test that board has foreign key constraint to account."""
        # Create game without account (for testing)
        game_id = GameID(uuid4())

        # Try to create board without valid account
        board = BoardORM(
            id=uuid4(),
            account_id=AccountID(uuid4()),  # Non-existent account
            game_id=game_id,
            name="Board Without Account",
            icon="star",
            short_code="BWA01",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="ALL",
        )

        db_session.add(board)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_board_foreign_key_to_game(self, db_session: AsyncSession):
        """Test that board has foreign key constraint to game."""
        # Create account
        account = AccountORM(id=uuid4(), name="Test Account", slug="test-account", status="active")
        db_session.add(account)
        await db_session.commit()

        # Try to create board without valid game
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=GameID(uuid4()),  # Non-existent game
            name="Board Without Game",
            icon="star",
            short_code="BWG01",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="ALL",
        )

        db_session.add(board)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_board_cascade_delete_with_account(self, db_session: AsyncSession):
        """Test that boards are deleted when account is deleted."""
        # Create account
        account = AccountORM(id=uuid4(), name="Test Account", slug="test-account", status="active")
        db_session.add(account)
        await db_session.commit()

        # Create game
        game = GameORM(id=uuid4(), account_id=account.id, name="Test Game")
        db_session.add(game)
        await db_session.commit()

        # Create board
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="star",
            short_code="TB001",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="ALL",
        )
        db_session.add(board)
        await db_session.commit()

        board_id = board.id

        # Delete account
        await db_session.delete(account)
        await db_session.commit()

        # Verify board is also deleted
        result = await db_session.execute(select(BoardORM).where(BoardORM.id == board_id))  # type: ignore[arg-type]
        deleted_board = result.scalar_one_or_none()

        assert deleted_board is None

    async def test_board_cascade_delete_with_game(self, db_session: AsyncSession):
        """Test that boards are deleted when game is deleted."""
        # Create account
        account = AccountORM(id=uuid4(), name="Test Account", slug="test-account", status="active")
        db_session.add(account)
        await db_session.commit()

        # Create game
        game = GameORM(id=uuid4(), account_id=account.id, name="Test Game")
        db_session.add(game)
        await db_session.commit()

        # Create board
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="star",
            short_code="TB002",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="ALL",
        )
        db_session.add(board)
        await db_session.commit()

        board_id = board.id

        # Delete game
        await db_session.delete(game)
        await db_session.commit()

        # Verify board is also deleted
        result = await db_session.execute(select(BoardORM).where(BoardORM.id == board_id))  # type: ignore[arg-type]
        deleted_board = result.scalar_one_or_none()

        assert deleted_board is None

    async def test_board_timestamps_auto_managed(self, db_session: AsyncSession):
        """Test that timestamps are automatically managed."""
        # Create account
        account = AccountORM(id=uuid4(), name="Test Account", slug="test-account", status="active")
        db_session.add(account)
        await db_session.commit()

        # Create game
        game = GameORM(id=uuid4(), account_id=account.id, name="Test Game")
        db_session.add(game)
        await db_session.commit()

        before = datetime.now(UTC)

        # Create board
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="star",
            short_code="TB003",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="ALL",
        )

        db_session.add(board)
        await db_session.commit()
        await db_session.refresh(board)

        after = datetime.now(UTC)

        assert before <= board.created_at <= after
        assert before <= board.updated_at <= after
        assert abs((board.created_at - board.updated_at).total_seconds()) < 0.1

    async def test_board_deleted_at_defaults_to_none(self, db_session: AsyncSession):
        """Test that deleted_at defaults to None."""
        # Create account
        account = AccountORM(id=uuid4(), name="Test Account", slug="test-account", status="active")
        db_session.add(account)
        await db_session.commit()

        # Create game
        game = GameORM(id=uuid4(), account_id=account.id, name="Test Game")
        db_session.add(game)
        await db_session.commit()

        # Create board
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="star",
            short_code="TB004",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="ALL",
        )

        db_session.add(board)
        await db_session.commit()
        await db_session.refresh(board)

        assert board.deleted_at is None

    async def test_board_deleted_at_can_be_set(self, db_session: AsyncSession):
        """Test that deleted_at can be set and persisted."""
        # Create account
        account = AccountORM(id=uuid4(), name="Test Account", slug="test-account", status="active")
        db_session.add(account)
        await db_session.commit()

        # Create game
        game = GameORM(id=uuid4(), account_id=account.id, name="Test Game")
        db_session.add(game)
        await db_session.commit()

        # Create board
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="star",
            short_code="TB005",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="ALL",
        )

        db_session.add(board)
        await db_session.commit()
        await db_session.refresh(board)

        # Set deleted_at
        delete_time = datetime.now(UTC)
        board.deleted_at = delete_time
        await db_session.commit()
        await db_session.refresh(board)

        assert board.deleted_at is not None
        assert abs((board.deleted_at - delete_time).total_seconds()) < 1  # type: ignore[operator]

    async def test_board_tags_empty_list_default(self, db_session: AsyncSession):
        """Test that tags defaults to empty list when not provided."""
        # Create account
        account = AccountORM(id=uuid4(), name="Test Account", slug="test-account", status="active")
        db_session.add(account)
        await db_session.commit()

        # Create game
        game = GameORM(id=uuid4(), account_id=account.id, name="Test Game")
        db_session.add(game)
        await db_session.commit()

        # Create board without tags
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="star",
            short_code="TB006",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="ALL",
        )

        db_session.add(board)
        await db_session.commit()
        await db_session.refresh(board)

        assert board.tags == []
        assert isinstance(board.tags, list)

    async def test_board_tags_can_be_stored_and_retrieved(self, db_session: AsyncSession):
        """Test that tags can be stored and retrieved as a list."""
        # Create account
        account = AccountORM(id=uuid4(), name="Test Account", slug="test-account", status="active")
        db_session.add(account)
        await db_session.commit()

        # Create game
        game = GameORM(id=uuid4(), account_id=account.id, name="Test Game")
        db_session.add(game)
        await db_session.commit()

        # Create board with tags
        tags = ["speedrun", "no-damage", "hardcore"]
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="star",
            short_code="TB007",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="ALL",
            tags=tags,
        )

        db_session.add(board)
        await db_session.commit()
        await db_session.refresh(board)

        assert board.tags == tags
        assert len(board.tags) == 3
