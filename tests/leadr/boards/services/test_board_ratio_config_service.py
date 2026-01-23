"""Tests for BoardRatioConfigService."""

from uuid import uuid4

import pytest

from leadr.boards.adapters.orm import BoardORM
from leadr.boards.domain.board_ratio_config import (
    BoardRatioConfig,
    RatioDisplay,
    ZeroDenominatorPolicy,
)
from leadr.boards.services.board_ratio_config_service import BoardRatioConfigService
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import BoardID, BoardRatioConfigID


@pytest.mark.asyncio
class TestBoardRatioConfigService:
    """Test cases for BoardRatioConfigService."""

    async def test_create_ratio_config(self, db_session, account_orm, game_orm) -> None:
        """Creating a ratio config succeeds."""
        service = BoardRatioConfigService(db_session)

        # Create boards
        ratio_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Win Rate",
            slug="win-rate",
            short_code="RCRT01",
            is_active=True,
            sort_direction="DESCENDING",
        )
        numerator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Wins",
            slug="wins",
            short_code="RCWI01",
            is_active=True,
            sort_direction="DESCENDING",
        )
        denominator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Total",
            slug="total",
            short_code="RCTG01",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add_all([ratio_board, numerator_board, denominator_board])
        await db_session.flush()

        config = await service.create_ratio_config(
            board_id=BoardID(ratio_board.id),
            numerator_board_id=BoardID(numerator_board.id),
            denominator_board_id=BoardID(denominator_board.id),
        )

        assert config.board_id.uuid == ratio_board.id
        assert config.numerator_board_id.uuid == numerator_board.id
        assert config.denominator_board_id.uuid == denominator_board.id
        assert config.zero_denominator_policy == ZeroDenominatorPolicy.NULL
        assert config.display == RatioDisplay.RAW

    async def test_create_ratio_config_with_options(
        self, db_session, account_orm, game_orm
    ) -> None:
        """Creating a ratio config with custom options succeeds."""
        service = BoardRatioConfigService(db_session)

        # Create boards
        ratio_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Kill Rate",
            slug="kill-rate",
            short_code="RCRT02",
            is_active=True,
            sort_direction="DESCENDING",
        )
        numerator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Kills",
            slug="kills",
            short_code="RCWI02",
            is_active=True,
            sort_direction="DESCENDING",
        )
        denominator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Deaths",
            slug="deaths",
            short_code="RCTG02",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add_all([ratio_board, numerator_board, denominator_board])
        await db_session.flush()

        config = await service.create_ratio_config(
            board_id=BoardID(ratio_board.id),
            numerator_board_id=BoardID(numerator_board.id),
            denominator_board_id=BoardID(denominator_board.id),
            zero_denominator_policy=ZeroDenominatorPolicy.INFINITY,
            min_denominator=1,
            display=RatioDisplay.PERCENT,
            decimals=1,
        )

        assert config.zero_denominator_policy == ZeroDenominatorPolicy.INFINITY
        assert config.min_denominator == 1
        assert config.display == RatioDisplay.PERCENT
        assert config.decimals == 1

    async def test_get_ratio_config(self, db_session, account_orm, game_orm) -> None:
        """Getting a ratio config by ID succeeds."""
        service = BoardRatioConfigService(db_session)

        # Create boards
        ratio_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Win Rate",
            slug="win-rate",
            short_code="RCRT03",
            is_active=True,
            sort_direction="DESCENDING",
        )
        numerator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Wins",
            slug="wins",
            short_code="RCWI03",
            is_active=True,
            sort_direction="DESCENDING",
        )
        denominator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Total",
            slug="total",
            short_code="RCTG03",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add_all([ratio_board, numerator_board, denominator_board])
        await db_session.flush()

        created = await service.create_ratio_config(
            board_id=BoardID(ratio_board.id),
            numerator_board_id=BoardID(numerator_board.id),
            denominator_board_id=BoardID(denominator_board.id),
        )

        retrieved = await service.get_ratio_config(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    async def test_get_ratio_config_not_found(self, db_session) -> None:
        """Getting a non-existent ratio config returns None."""
        service = BoardRatioConfigService(db_session)

        result = await service.get_ratio_config(BoardRatioConfigID())

        assert result is None

    async def test_get_by_id_or_raise_success(
        self, db_session, account_orm, game_orm
    ) -> None:
        """get_by_id_or_raise returns config when found."""
        service = BoardRatioConfigService(db_session)

        # Create boards
        ratio_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Win Rate",
            slug="win-rate",
            short_code="RCRT04",
            is_active=True,
            sort_direction="DESCENDING",
        )
        numerator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Wins",
            slug="wins",
            short_code="RCWI04",
            is_active=True,
            sort_direction="DESCENDING",
        )
        denominator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Total",
            slug="total",
            short_code="RCTG04",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add_all([ratio_board, numerator_board, denominator_board])
        await db_session.flush()

        created = await service.create_ratio_config(
            board_id=BoardID(ratio_board.id),
            numerator_board_id=BoardID(numerator_board.id),
            denominator_board_id=BoardID(denominator_board.id),
        )

        result = await service.get_by_id_or_raise(created.id)

        assert result.id == created.id

    async def test_get_by_id_or_raise_not_found(self, db_session) -> None:
        """get_by_id_or_raise raises when not found."""
        service = BoardRatioConfigService(db_session)

        with pytest.raises(EntityNotFoundError):
            await service.get_by_id_or_raise(BoardRatioConfigID())

    async def test_get_by_board_id(self, db_session, account_orm, game_orm) -> None:
        """Getting a ratio config by board ID succeeds."""
        service = BoardRatioConfigService(db_session)

        # Create boards
        ratio_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Win Rate",
            slug="win-rate",
            short_code="RCRT05",
            is_active=True,
            sort_direction="DESCENDING",
        )
        numerator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Wins",
            slug="wins",
            short_code="RCWI05",
            is_active=True,
            sort_direction="DESCENDING",
        )
        denominator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Total",
            slug="total",
            short_code="RCTG05",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add_all([ratio_board, numerator_board, denominator_board])
        await db_session.flush()

        created = await service.create_ratio_config(
            board_id=BoardID(ratio_board.id),
            numerator_board_id=BoardID(numerator_board.id),
            denominator_board_id=BoardID(denominator_board.id),
        )

        retrieved = await service.get_by_board_id(BoardID(ratio_board.id))

        assert retrieved is not None
        assert retrieved.id == created.id

    async def test_get_by_board_id_not_found(self, db_session) -> None:
        """Getting ratio config by non-existent board ID returns None."""
        service = BoardRatioConfigService(db_session)

        result = await service.get_by_board_id(BoardID())

        assert result is None

    async def test_update_ratio_config(self, db_session, account_orm, game_orm) -> None:
        """Updating a ratio config succeeds."""
        service = BoardRatioConfigService(db_session)

        # Create boards
        ratio_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Win Rate",
            slug="win-rate",
            short_code="RCRT06",
            is_active=True,
            sort_direction="DESCENDING",
        )
        numerator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Wins",
            slug="wins",
            short_code="RCWI06",
            is_active=True,
            sort_direction="DESCENDING",
        )
        denominator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Total",
            slug="total",
            short_code="RCTG06",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add_all([ratio_board, numerator_board, denominator_board])
        await db_session.flush()

        created = await service.create_ratio_config(
            board_id=BoardID(ratio_board.id),
            numerator_board_id=BoardID(numerator_board.id),
            denominator_board_id=BoardID(denominator_board.id),
        )

        updated = await service.update_ratio_config(
            config_id=created.id,
            min_denominator=10,
            display=RatioDisplay.PERCENT,
        )

        assert updated.min_denominator == 10
        assert updated.display == RatioDisplay.PERCENT

    async def test_soft_delete(self, db_session, account_orm, game_orm) -> None:
        """Soft deleting a ratio config succeeds."""
        service = BoardRatioConfigService(db_session)

        # Create boards
        ratio_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Win Rate",
            slug="win-rate",
            short_code="RCRT07",
            is_active=True,
            sort_direction="DESCENDING",
        )
        numerator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Wins",
            slug="wins",
            short_code="RCWI07",
            is_active=True,
            sort_direction="DESCENDING",
        )
        denominator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Total",
            slug="total",
            short_code="RCTG07",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add_all([ratio_board, numerator_board, denominator_board])
        await db_session.flush()

        created = await service.create_ratio_config(
            board_id=BoardID(ratio_board.id),
            numerator_board_id=BoardID(numerator_board.id),
            denominator_board_id=BoardID(denominator_board.id),
        )

        deleted = await service.soft_delete(created.id)

        assert deleted.id == created.id
        # After soft delete, get should return None
        retrieved = await service.get_ratio_config(created.id)
        assert retrieved is None
