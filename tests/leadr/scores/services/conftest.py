"""Shared fixtures for score service tests."""

from unittest.mock import AsyncMock

import pytest

from leadr.boards.domain.board import Board, BoardType, KeepStrategy, SortDirection
from leadr.common.domain.ids import AccountID, BoardID, GameID, IdentityID, ScoreEventID
from leadr.scores.domain.score_event import ScoreEvent
from leadr.scores.services.score_service import ScoreService


@pytest.fixture
def account_id() -> AccountID:
    return AccountID()


@pytest.fixture
def game_id() -> GameID:
    return GameID()


@pytest.fixture
def board_id() -> BoardID:
    return BoardID()


@pytest.fixture
def identity_id() -> IdentityID:
    return IdentityID()


@pytest.fixture
def run_identity_board(account_id: AccountID, game_id: GameID, board_id: BoardID) -> Board:
    return Board(
        id=board_id,
        account_id=account_id,
        game_id=game_id,
        name="High Scores",
        slug="high-scores",
        short_code="ABC123",
        sort_direction=SortDirection.DESCENDING,
        board_type=BoardType.RUN_IDENTITY,
        keep_strategy=KeepStrategy.BEST,
    )


@pytest.fixture
def run_runs_board(account_id: AccountID, game_id: GameID, board_id: BoardID) -> Board:
    return Board(
        id=board_id,
        account_id=account_id,
        game_id=game_id,
        name="Speedruns",
        slug="speedruns",
        short_code="SPD001",
        sort_direction=SortDirection.ASCENDING,
        board_type=BoardType.RUN_RUNS,
        keep_strategy=KeepStrategy.NA,
    )


@pytest.fixture
def counter_board(account_id: AccountID, game_id: GameID, board_id: BoardID) -> Board:
    return Board(
        id=board_id,
        account_id=account_id,
        game_id=game_id,
        name="Kill Count",
        slug="kill-count",
        short_code="KIL001",
        sort_direction=SortDirection.DESCENDING,
        board_type=BoardType.COUNTER,
        keep_strategy=KeepStrategy.NA,
    )


@pytest.fixture
def score_event(
    account_id: AccountID, game_id: GameID, board_id: BoardID, identity_id: IdentityID
) -> ScoreEvent:
    return ScoreEvent(
        id=ScoreEventID(),
        account_id=account_id,
        game_id=game_id,
        board_id=board_id,
        identity_id=identity_id,
        event_payload={"value": 100.0},
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(mock_session: AsyncMock) -> ScoreService:
    return ScoreService(mock_session)
