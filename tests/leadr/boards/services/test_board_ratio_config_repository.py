"""Tests for BoardRatioConfigRepository."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from leadr.boards.adapters.orm import BoardORM, BoardRatioConfigORM
from leadr.boards.domain.board_ratio_config import (
    BoardRatioConfig,
    RatioDisplay,
    TieBreaker,
    ZeroDenominatorPolicy,
)
from leadr.boards.services.repositories import BoardRatioConfigRepository
from leadr.common.domain.ids import BoardID, BoardRatioConfigID


@pytest.mark.asyncio
class TestBoardRatioConfigRepository:
    """Tests for BoardRatioConfigRepository."""

    def test_to_domain_conversion(self, db_session) -> None:
        """Repository correctly converts ORM to domain model."""
        repository = BoardRatioConfigRepository(db_session)

        board_id = uuid4()
        numerator_board_id = uuid4()
        denominator_board_id = uuid4()
        now = datetime.now(UTC)

        orm = BoardRatioConfigORM(
            id=uuid4(),
            board_id=board_id,
            numerator_board_id=numerator_board_id,
            denominator_board_id=denominator_board_id,
            zero_denominator_policy=ZeroDenominatorPolicy.ZERO.value,
            min_denominator=10.0,
            min_numerator=5.0,
            scale=100,
            display=RatioDisplay.PERCENT.value,
            decimals=3,
            tie_breaker=TieBreaker.NUMERATOR_DESC_DENOMINATOR_ASC.value,
            created_at=now,
            updated_at=now,
        )

        domain = repository._to_domain(orm)

        assert isinstance(domain.id, BoardRatioConfigID)
        assert domain.id.uuid == orm.id
        assert domain.board_id.uuid == board_id
        assert domain.numerator_board_id.uuid == numerator_board_id
        assert domain.denominator_board_id.uuid == denominator_board_id
        assert domain.zero_denominator_policy == ZeroDenominatorPolicy.ZERO
        assert domain.min_denominator == 10.0
        assert domain.min_numerator == 5.0
        assert domain.scale == 100
        assert domain.display == RatioDisplay.PERCENT
        assert domain.decimals == 3
        assert domain.tie_breaker == TieBreaker.NUMERATOR_DESC_DENOMINATOR_ASC

    def test_to_orm_conversion(self, db_session) -> None:
        """Repository correctly converts domain model to ORM."""
        repository = BoardRatioConfigRepository(db_session)

        domain = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
            zero_denominator_policy=ZeroDenominatorPolicy.INFINITY,
            min_denominator=20.0,
            min_numerator=10.0,
            scale=1000,
            display=RatioDisplay.RAW,
            decimals=1,
        )

        orm = repository._to_orm(domain)

        assert orm.id == domain.id.uuid
        assert orm.board_id == domain.board_id.uuid
        assert orm.numerator_board_id == domain.numerator_board_id.uuid
        assert orm.denominator_board_id == domain.denominator_board_id.uuid
        assert orm.zero_denominator_policy == ZeroDenominatorPolicy.INFINITY.value
        assert orm.min_denominator == 20.0
        assert orm.min_numerator == 10.0
        assert orm.scale == 1000
        assert orm.display == RatioDisplay.RAW.value
        assert orm.decimals == 1
        assert orm.tie_breaker == TieBreaker.NUMERATOR_DESC_DENOMINATOR_ASC.value

    def test_get_orm_class(self, db_session) -> None:
        """Repository returns correct ORM class."""
        repository = BoardRatioConfigRepository(db_session)
        assert repository._get_orm_class() == BoardRatioConfigORM


@pytest.mark.asyncio
class TestBoardRatioConfigRepositoryCRUD:
    """CRUD tests for BoardRatioConfigRepository."""

    async def test_create_board_ratio_config(self, db_session, account_orm, game_orm) -> None:
        """Creating a board ratio config succeeds."""
        repository = BoardRatioConfigRepository(db_session)

        # Create boards
        ratio_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Win Rate",
            slug="win-rate",
            short_code="WINR01",
            is_active=True,
            sort_direction="DESCENDING",
        )
        numerator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Wins",
            slug="wins",
            short_code="WINS04",
            is_active=True,
            sort_direction="DESCENDING",
        )
        denominator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Total",
            slug="total",
            short_code="TOTL04",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add_all([ratio_board, numerator_board, denominator_board])
        await db_session.flush()

        config = BoardRatioConfig(
            board_id=BoardID(ratio_board.id),
            numerator_board_id=BoardID(numerator_board.id),
            denominator_board_id=BoardID(denominator_board.id),
        )

        created = await repository.create(config)

        assert created.id == config.id
        assert created.board_id == config.board_id
        assert created.numerator_board_id == config.numerator_board_id
        assert created.denominator_board_id == config.denominator_board_id

    async def test_get_by_id(self, db_session, account_orm, game_orm) -> None:
        """Getting a board ratio config by ID succeeds."""
        repository = BoardRatioConfigRepository(db_session)

        # Create boards
        ratio_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Win Rate",
            slug="win-rate",
            short_code="WINR02",
            is_active=True,
            sort_direction="DESCENDING",
        )
        numerator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Wins",
            slug="wins",
            short_code="WINS05",
            is_active=True,
            sort_direction="DESCENDING",
        )
        denominator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Total",
            slug="total",
            short_code="TOTL05",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add_all([ratio_board, numerator_board, denominator_board])
        await db_session.flush()

        config = BoardRatioConfig(
            board_id=BoardID(ratio_board.id),
            numerator_board_id=BoardID(numerator_board.id),
            denominator_board_id=BoardID(denominator_board.id),
        )
        await repository.create(config)

        retrieved = await repository.get_by_id(config.id)

        assert retrieved is not None
        assert retrieved.id == config.id

    async def test_get_by_id_not_found(self, db_session) -> None:
        """Getting a non-existent board ratio config returns None."""
        repository = BoardRatioConfigRepository(db_session)

        result = await repository.get_by_id(BoardRatioConfigID())

        assert result is None

    async def test_get_by_board_id(self, db_session, account_orm, game_orm) -> None:
        """Getting a board ratio config by board ID succeeds."""
        repository = BoardRatioConfigRepository(db_session)

        # Create boards
        ratio_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Win Rate",
            slug="win-rate",
            short_code="WINR03",
            is_active=True,
            sort_direction="DESCENDING",
        )
        numerator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Wins",
            slug="wins",
            short_code="WINS06",
            is_active=True,
            sort_direction="DESCENDING",
        )
        denominator_board = BoardORM(
            id=uuid4(),
            account_id=account_orm.id,
            game_id=game_orm.id,
            name="Total",
            slug="total",
            short_code="TOTL06",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add_all([ratio_board, numerator_board, denominator_board])
        await db_session.flush()

        config = BoardRatioConfig(
            board_id=BoardID(ratio_board.id),
            numerator_board_id=BoardID(numerator_board.id),
            denominator_board_id=BoardID(denominator_board.id),
        )
        await repository.create(config)

        retrieved = await repository.get_by_board_id(BoardID(ratio_board.id))

        assert retrieved is not None
        assert retrieved.board_id == config.board_id

    async def test_get_by_board_id_not_found(self, db_session) -> None:
        """Getting a non-existent board ratio config by board ID returns None."""
        repository = BoardRatioConfigRepository(db_session)

        result = await repository.get_by_board_id(BoardID())

        assert result is None
