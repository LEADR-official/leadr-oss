"""Tests for BoardRatioConfigORM model."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from leadr.accounts.adapters.orm import AccountORM
from leadr.boards.adapters.orm import BoardORM, BoardRatioConfigORM
from leadr.boards.domain.board_ratio_config import (
    RatioDisplay,
    TieBreaker,
    ZeroDenominatorPolicy,
)
from leadr.games.adapters.orm import GameORM


class TestBoardRatioConfigORM:
    """Test cases for BoardRatioConfigORM model."""

    def test_board_ratio_config_orm_tablename(self) -> None:
        """ORM model has correct table name."""
        assert BoardRatioConfigORM.__tablename__ == "board_ratio_configs"

    @pytest.mark.asyncio
    async def test_create_board_ratio_config_with_all_fields(self, db_session) -> None:
        """BoardRatioConfigORM can be created with all fields."""
        # Create required parent entities
        account_id = uuid4()
        game_id = uuid4()
        ratio_board_id = uuid4()
        numerator_board_id = uuid4()
        denominator_board_id = uuid4()
        config_id = uuid4()

        account = AccountORM(id=account_id, name="Test", slug="test")
        db_session.add(account)
        await db_session.flush()

        game = GameORM(id=game_id, account_id=account_id, name="Test Game", slug="test-game")
        db_session.add(game)
        await db_session.flush()

        # Create ratio board
        ratio_board = BoardORM(
            id=ratio_board_id,
            account_id=account_id,
            game_id=game_id,
            name="Win Rate",
            slug="win-rate",
            short_code="RATE01",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add(ratio_board)

        # Create numerator board
        numerator_board = BoardORM(
            id=numerator_board_id,
            account_id=account_id,
            game_id=game_id,
            name="Wins",
            slug="wins",
            short_code="WINS01",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add(numerator_board)

        # Create denominator board
        denominator_board = BoardORM(
            id=denominator_board_id,
            account_id=account_id,
            game_id=game_id,
            name="Total Games",
            slug="total-games",
            short_code="TOTL01",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add(denominator_board)
        await db_session.flush()

        # Create ratio config
        config = BoardRatioConfigORM(
            id=config_id,
            board_id=ratio_board_id,
            numerator_board_id=numerator_board_id,
            denominator_board_id=denominator_board_id,
            zero_denominator_policy=ZeroDenominatorPolicy.NULL.value,
            min_denominator=10.0,
            min_numerator=5.0,
            scale=1_000_000,
            display=RatioDisplay.PERCENT.value,
            decimals=2,
            tie_breaker=TieBreaker.NUMERATOR_DESC_DENOMINATOR_ASC.value,
        )
        db_session.add(config)
        await db_session.commit()

        # Retrieve and verify
        result = await db_session.execute(
            select(BoardRatioConfigORM).where(BoardRatioConfigORM.id == config_id)
        )
        saved_config = result.scalar_one()

        assert saved_config.id == config_id
        assert saved_config.board_id == ratio_board_id
        assert saved_config.numerator_board_id == numerator_board_id
        assert saved_config.denominator_board_id == denominator_board_id
        assert saved_config.zero_denominator_policy == ZeroDenominatorPolicy.NULL.value
        assert saved_config.min_denominator == 10.0
        assert saved_config.min_numerator == 5.0
        assert saved_config.scale == 1_000_000
        assert saved_config.display == RatioDisplay.PERCENT.value
        assert saved_config.decimals == 2
        assert saved_config.tie_breaker == TieBreaker.NUMERATOR_DESC_DENOMINATOR_ASC.value
        assert saved_config.created_at is not None
        assert saved_config.updated_at is not None

    @pytest.mark.asyncio
    async def test_board_ratio_config_cascade_delete_with_board(self, db_session) -> None:
        """BoardRatioConfigORM is deleted when ratio board is deleted."""
        # Create required parent entities
        account_id = uuid4()
        game_id = uuid4()
        ratio_board_id = uuid4()
        numerator_board_id = uuid4()
        denominator_board_id = uuid4()
        config_id = uuid4()

        account = AccountORM(id=account_id, name="Test", slug="test")
        db_session.add(account)
        await db_session.flush()

        game = GameORM(id=game_id, account_id=account_id, name="Test Game", slug="test-game")
        db_session.add(game)
        await db_session.flush()

        # Create boards
        ratio_board = BoardORM(
            id=ratio_board_id,
            account_id=account_id,
            game_id=game_id,
            name="Win Rate",
            slug="win-rate",
            short_code="RATE02",
            is_active=True,
            sort_direction="DESCENDING",
        )
        numerator_board = BoardORM(
            id=numerator_board_id,
            account_id=account_id,
            game_id=game_id,
            name="Wins",
            slug="wins",
            short_code="WINS02",
            is_active=True,
            sort_direction="DESCENDING",
        )
        denominator_board = BoardORM(
            id=denominator_board_id,
            account_id=account_id,
            game_id=game_id,
            name="Total Games",
            slug="total-games",
            short_code="TOTL02",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add_all([ratio_board, numerator_board, denominator_board])
        await db_session.flush()

        # Create ratio config
        config = BoardRatioConfigORM(
            id=config_id,
            board_id=ratio_board_id,
            numerator_board_id=numerator_board_id,
            denominator_board_id=denominator_board_id,
        )
        db_session.add(config)
        await db_session.commit()

        # Delete the ratio board
        await db_session.delete(ratio_board)
        await db_session.commit()

        # Config should be deleted via cascade
        result = await db_session.execute(
            select(BoardRatioConfigORM).where(BoardRatioConfigORM.id == config_id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_board_ratio_config_unique_constraint_board_id(self, db_session) -> None:
        """Only one ratio config per board is allowed."""
        # Create required parent entities
        account_id = uuid4()
        game_id = uuid4()
        ratio_board_id = uuid4()
        numerator_board_id = uuid4()
        denominator_board_id = uuid4()

        account = AccountORM(id=account_id, name="Test", slug="test")
        db_session.add(account)
        await db_session.flush()

        game = GameORM(id=game_id, account_id=account_id, name="Test Game", slug="test-game")
        db_session.add(game)
        await db_session.flush()

        # Create boards
        ratio_board = BoardORM(
            id=ratio_board_id,
            account_id=account_id,
            game_id=game_id,
            name="Win Rate",
            slug="win-rate",
            short_code="RATE03",
            is_active=True,
            sort_direction="DESCENDING",
        )
        numerator_board = BoardORM(
            id=numerator_board_id,
            account_id=account_id,
            game_id=game_id,
            name="Wins",
            slug="wins",
            short_code="WINS03",
            is_active=True,
            sort_direction="DESCENDING",
        )
        denominator_board = BoardORM(
            id=denominator_board_id,
            account_id=account_id,
            game_id=game_id,
            name="Total Games",
            slug="total-games",
            short_code="TOTL03",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add_all([ratio_board, numerator_board, denominator_board])
        await db_session.flush()

        # Create first config
        config1 = BoardRatioConfigORM(
            id=uuid4(),
            board_id=ratio_board_id,
            numerator_board_id=numerator_board_id,
            denominator_board_id=denominator_board_id,
        )
        db_session.add(config1)
        await db_session.commit()

        # Try to create second config for same board
        config2 = BoardRatioConfigORM(
            id=uuid4(),
            board_id=ratio_board_id,  # Same board
            numerator_board_id=numerator_board_id,
            denominator_board_id=denominator_board_id,
        )
        db_session.add(config2)

        with pytest.raises(IntegrityError):
            await db_session.commit()
