"""Tests for Score ORM model."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.adapters.orm import AccountORM, UserORM
from leadr.boards.adapters.orm import BoardORM
from leadr.games.adapters.orm import GameORM
from leadr.scores.adapters.orm import ScoreORM


@pytest.mark.asyncio
class TestScoreORM:
    """Test suite for Score ORM model."""

    async def test_create_score_with_all_fields(self, db_session: AsyncSession):
        """Test creating a score with all fields in the database."""
        # Create account
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
            status="active",
        )
        db_session.add(account)
        await db_session.commit()

        # Create user
        user = UserORM(
            id=uuid4(),
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
        )
        db_session.add(user)
        await db_session.commit()

        # Create game
        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create board
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="BEST_ONLY",
        )
        db_session.add(board)
        await db_session.commit()

        # Create score with all fields
        score = ScoreORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            user_id=user.id,
            player_name="SpeedRunner99",
            value=123.45,
            value_display="2:03.45",
            filter_timezone="America/New_York",
            filter_country="USA",
            filter_city="New York",
        )

        db_session.add(score)
        await db_session.commit()
        await db_session.refresh(score)

        assert score.id is not None
        assert score.account_id == account.id
        assert score.game_id == game.id
        assert score.board_id == board.id
        assert score.user_id == user.id
        assert score.player_name == "SpeedRunner99"  # type: ignore[comparison-overlap]
        assert score.value == 123.45
        assert score.value_display == "2:03.45"  # type: ignore[comparison-overlap]
        assert score.filter_timezone == "America/New_York"  # type: ignore[comparison-overlap]
        assert score.filter_country == "USA"  # type: ignore[comparison-overlap]
        assert score.filter_city == "New York"  # type: ignore[comparison-overlap]
        assert score.created_at is not None
        assert score.updated_at is not None

    async def test_create_score_with_required_fields_only(self, db_session: AsyncSession):
        """Test creating a score with only required fields."""
        # Create account
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
            status="active",
        )
        db_session.add(account)
        await db_session.commit()

        # Create user
        user = UserORM(
            id=uuid4(),
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
        )
        db_session.add(user)
        await db_session.commit()

        # Create game
        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create board
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="BEST_ONLY",
        )
        db_session.add(board)
        await db_session.commit()

        # Create score with only required fields
        score = ScoreORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            user_id=user.id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        db_session.add(score)
        await db_session.commit()
        await db_session.refresh(score)

        assert score.id is not None
        assert score.player_name == "SpeedRunner99"  # type: ignore[comparison-overlap]
        assert score.value == 123.45
        assert score.value_display is None
        assert score.filter_timezone is None
        assert score.filter_country is None
        assert score.filter_city is None

    async def test_score_requires_account_id(self, db_session: AsyncSession):
        """Test that account_id is required (foreign key constraint)."""
        user_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()

        score = ScoreORM(
            id=uuid4(),
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        db_session.add(score)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_score_requires_game_id(self, db_session: AsyncSession):
        """Test that game_id is required (foreign key constraint)."""
        account_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        score = ScoreORM(
            id=uuid4(),
            account_id=account_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        db_session.add(score)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_score_requires_board_id(self, db_session: AsyncSession):
        """Test that board_id is required (foreign key constraint)."""
        account_id = uuid4()
        game_id = uuid4()
        user_id = uuid4()

        score = ScoreORM(
            id=uuid4(),
            account_id=account_id,
            game_id=game_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        db_session.add(score)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_score_requires_user_id(self, db_session: AsyncSession):
        """Test that user_id is required (foreign key constraint)."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()

        score = ScoreORM(
            id=uuid4(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        db_session.add(score)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_cascade_delete_account(self, db_session: AsyncSession):
        """Test that deleting an account cascades to scores."""
        # Create account
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
            status="active",
        )
        db_session.add(account)
        await db_session.commit()

        # Create user
        user = UserORM(
            id=uuid4(),
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
        )
        db_session.add(user)
        await db_session.commit()

        # Create game
        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create board
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="BEST_ONLY",
        )
        db_session.add(board)
        await db_session.commit()

        # Create score
        score = ScoreORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            user_id=user.id,
            player_name="SpeedRunner99",
            value=123.45,
        )
        db_session.add(score)
        await db_session.commit()

        score_id = score.id

        # Delete account
        await db_session.delete(account)
        await db_session.commit()

        # Verify score is deleted
        result = await db_session.execute(select(ScoreORM).where(ScoreORM.id == score_id))
        deleted_score = result.scalar_one_or_none()
        assert deleted_score is None

    async def test_cascade_delete_game(self, db_session: AsyncSession):
        """Test that deleting a game cascades to scores."""
        # Create account
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
            status="active",
        )
        db_session.add(account)
        await db_session.commit()

        # Create user
        user = UserORM(
            id=uuid4(),
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
        )
        db_session.add(user)
        await db_session.commit()

        # Create game
        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create board
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="BEST_ONLY",
        )
        db_session.add(board)
        await db_session.commit()

        # Create score
        score = ScoreORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            user_id=user.id,
            player_name="SpeedRunner99",
            value=123.45,
        )
        db_session.add(score)
        await db_session.commit()

        score_id = score.id

        # Delete game
        await db_session.delete(game)
        await db_session.commit()

        # Verify score is deleted
        result = await db_session.execute(select(ScoreORM).where(ScoreORM.id == score_id))
        deleted_score = result.scalar_one_or_none()
        assert deleted_score is None

    async def test_cascade_delete_board(self, db_session: AsyncSession):
        """Test that deleting a board cascades to scores."""
        # Create account
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
            status="active",
        )
        db_session.add(account)
        await db_session.commit()

        # Create user
        user = UserORM(
            id=uuid4(),
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
        )
        db_session.add(user)
        await db_session.commit()

        # Create game
        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create board
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="BEST_ONLY",
        )
        db_session.add(board)
        await db_session.commit()

        # Create score
        score = ScoreORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            user_id=user.id,
            player_name="SpeedRunner99",
            value=123.45,
        )
        db_session.add(score)
        await db_session.commit()

        score_id = score.id

        # Delete board
        await db_session.delete(board)
        await db_session.commit()

        # Verify score is deleted
        result = await db_session.execute(select(ScoreORM).where(ScoreORM.id == score_id))
        deleted_score = result.scalar_one_or_none()
        assert deleted_score is None

    async def test_cascade_delete_user(self, db_session: AsyncSession):
        """Test that deleting a user cascades to scores."""
        # Create account
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
            status="active",
        )
        db_session.add(account)
        await db_session.commit()

        # Create user
        user = UserORM(
            id=uuid4(),
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
        )
        db_session.add(user)
        await db_session.commit()

        # Create game
        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create board
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="BEST_ONLY",
        )
        db_session.add(board)
        await db_session.commit()

        # Create score
        score = ScoreORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            user_id=user.id,
            player_name="SpeedRunner99",
            value=123.45,
        )
        db_session.add(score)
        await db_session.commit()

        score_id = score.id

        # Delete user
        await db_session.delete(user)
        await db_session.commit()

        # Verify score is deleted
        result = await db_session.execute(select(ScoreORM).where(ScoreORM.id == score_id))
        deleted_score = result.scalar_one_or_none()
        assert deleted_score is None

    async def test_value_stored_as_float(self, db_session: AsyncSession):
        """Test that value is stored as float and maintains precision."""
        # Create account
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
            status="active",
        )
        db_session.add(account)
        await db_session.commit()

        # Create user
        user = UserORM(
            id=uuid4(),
            account_id=account.id,
            email="player@example.com",
            display_name="Test Player",
        )
        db_session.add(user)
        await db_session.commit()

        # Create game
        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        # Create board
        board = BoardORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction="DESCENDING",
            keep_strategy="BEST_ONLY",
        )
        db_session.add(board)
        await db_session.commit()

        # Create score with float value
        score = ScoreORM(
            id=uuid4(),
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            user_id=user.id,
            player_name="SpeedRunner99",
            value=123.456789,
        )

        db_session.add(score)
        await db_session.commit()
        await db_session.refresh(score)

        # Verify float precision is maintained (within reasonable bounds)
        assert abs(score.value - 123.456789) < 0.0001
        assert isinstance(score.value, float)
