"""Shared fixtures for score API route tests."""

from unittest.mock import AsyncMock

import pytest

from leadr.auth.dependencies import (
    require_admin_auth,
    require_admin_auth_with_account_id,
    require_client_auth,
    require_client_auth_with_nonce,
)
from leadr.auth.domain.identity import Identity, IdentityKind
from leadr.auth.services.dependencies import get_identity_service
from leadr.auth.services.identity_service import IdentityService
from leadr.boards.domain.board import Board, BoardType, KeepStrategy, SortDirection
from leadr.boards.domain.board_state import BoardState
from leadr.boards.domain.run_entry import RunEntry
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.dependencies import get_board_service
from leadr.common.api.hooks import (
    get_post_create_score_hook,
    get_pre_create_score_hook,
    noop_post_create_score,
    noop_pre_create_score,
)
from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    BoardStateID,
    GameID,
    IdentityID,
    RunEntryID,
    ScoreEventID,
)
from leadr.common.domain.pagination import CursorPosition
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.scores.domain.anti_cheat.enums import FlagAction
from leadr.scores.domain.anti_cheat.models import AntiCheatResult
from leadr.scores.domain.score_event import ScoreEvent
from leadr.scores.services.dependencies import (
    get_score_event_service,
    get_score_flag_service,
    get_score_service,
    get_score_submission_meta_service,
)
from leadr.scores.services.score_event_service import ScoreEventService
from leadr.scores.services.score_flag_service import ScoreFlagService
from leadr.scores.services.score_service import ScoreService
from leadr.scores.services.score_submission_meta_service import ScoreSubmissionMetaService
from tests.conftest import make_admin_auth, make_client_auth


@pytest.fixture
def admin_auth(test_app):
    """Admin auth context fixture.

    Overrides admin auth dependencies to return a superadmin context.
    """
    auth = make_admin_auth()
    test_app.dependency_overrides[require_admin_auth] = lambda: auth
    test_app.dependency_overrides[require_admin_auth_with_account_id] = lambda: auth
    return auth


@pytest.fixture
def client_auth(test_app):
    """Client auth context fixture.

    Overrides client auth dependencies to return a client context.
    """
    auth = make_client_auth()
    test_app.dependency_overrides[require_client_auth] = lambda: auth
    test_app.dependency_overrides[require_client_auth_with_nonce] = lambda: auth
    return auth


@pytest.fixture
def mock_score_service(test_app):
    """Mock ScoreService dependency."""
    svc = AsyncMock(spec=ScoreService)
    test_app.dependency_overrides[get_score_service] = lambda: svc
    return svc


@pytest.fixture
def mock_score_event_service(test_app):
    """Mock ScoreEventService dependency."""
    svc = AsyncMock(spec=ScoreEventService)
    test_app.dependency_overrides[get_score_event_service] = lambda: svc
    return svc


@pytest.fixture
def mock_score_flag_service(test_app):
    """Mock ScoreFlagService dependency."""
    svc = AsyncMock(spec=ScoreFlagService)
    test_app.dependency_overrides[get_score_flag_service] = lambda: svc
    return svc


@pytest.fixture
def mock_score_submission_meta_service(test_app):
    """Mock ScoreSubmissionMetaService dependency."""
    svc = AsyncMock(spec=ScoreSubmissionMetaService)
    test_app.dependency_overrides[get_score_submission_meta_service] = lambda: svc
    return svc


@pytest.fixture
def mock_board_service(test_app):
    """Mock BoardService dependency."""
    svc = AsyncMock(spec=BoardService)
    test_app.dependency_overrides[get_board_service] = lambda: svc
    return svc


@pytest.fixture
def mock_identity_service(test_app):
    """Mock IdentityService dependency."""
    svc = AsyncMock(spec=IdentityService)
    test_app.dependency_overrides[get_identity_service] = lambda: svc
    return svc


@pytest.fixture
def mock_hooks(test_app):
    """Mock score creation hooks (no-op by default).

    Returns tuple of (pre_create_hook, post_create_hook) for assertion in tests.
    """
    pre_hook = AsyncMock(side_effect=noop_pre_create_score)
    post_hook = AsyncMock(side_effect=noop_post_create_score)
    test_app.dependency_overrides[get_pre_create_score_hook] = lambda: pre_hook
    test_app.dependency_overrides[get_post_create_score_hook] = lambda: post_hook
    return pre_hook, post_hook


# ---------------------------------------------------------------------------
# Domain object factories for test data
# ---------------------------------------------------------------------------


def make_board(
    account_id: AccountID | None = None,
    game_id: GameID | None = None,
    board_type: BoardType = BoardType.RUN_IDENTITY,
    keep_strategy: KeepStrategy = KeepStrategy.BEST,
    sort_direction: SortDirection = SortDirection.DESCENDING,
    **kwargs,
) -> Board:
    """Factory for creating Board domain objects.

    Args:
        account_id: Account ID (auto-generated if not provided).
        game_id: Game ID (auto-generated if not provided).
        board_type: Board type (default: RUN_IDENTITY).
        keep_strategy: Keep strategy (default: BEST).
        sort_direction: Sort direction (default: DESCENDING).
        **kwargs: Additional keyword arguments for Board.

    Returns:
        Board domain object.
    """
    return Board(
        id=kwargs.get("id", BoardID()),
        account_id=account_id or AccountID(),
        game_id=game_id or GameID(),
        name=kwargs.get("name", "Test Board"),
        slug=kwargs.get("slug", "test-board"),
        short_code=kwargs.get("short_code", "TEST01"),
        sort_direction=sort_direction,
        board_type=board_type,
        keep_strategy=keep_strategy,
        **{k: v for k, v in kwargs.items() if k not in ("id", "name", "slug", "short_code")},
    )


def make_board_state(
    board_id: BoardID | None = None,
    identity_id: IdentityID | None = None,
    primary_value: float = 100.0,
    player_name: str = "Player1",
    rank: int = 0,
    **kwargs,
) -> BoardState:
    """Factory for creating BoardState domain objects.

    Args:
        board_id: Board ID (auto-generated if not provided).
        identity_id: Identity ID (auto-generated if not provided).
        primary_value: Primary value for ranking.
        player_name: Player display name.
        rank: Transient rank field.
        **kwargs: Additional keyword arguments for BoardState.

    Returns:
        BoardState domain object.
    """
    state = BoardState(
        id=kwargs.get("id", BoardStateID()),
        board_id=board_id or BoardID(),
        identity_id=identity_id or IdentityID(),
        primary_value=primary_value,
        player_name=player_name,
        **{k: v for k, v in kwargs.items() if k not in ("id",)},
    )
    # Set transient rank field
    state.rank = rank
    return state


def make_run_entry(
    board_id: BoardID | None = None,
    identity_id: IdentityID | None = None,
    score_event_id: ScoreEventID | None = None,
    primary_value: float = 100.0,
    player_name: str = "Runner1",
    rank: int = 0,
    **kwargs,
) -> RunEntry:
    """Factory for creating RunEntry domain objects.

    Args:
        board_id: Board ID (auto-generated if not provided).
        identity_id: Identity ID (auto-generated if not provided).
        score_event_id: Score event ID (auto-generated if not provided).
        primary_value: Primary value for ranking.
        player_name: Player display name.
        rank: Transient rank field.
        **kwargs: Additional keyword arguments for RunEntry.

    Returns:
        RunEntry domain object.
    """
    entry = RunEntry(
        id=kwargs.get("id", RunEntryID()),
        board_id=board_id or BoardID(),
        identity_id=identity_id or IdentityID(),
        score_event_id=score_event_id or ScoreEventID(),
        primary_value=primary_value,
        player_name=player_name,
        **{k: v for k, v in kwargs.items() if k not in ("id",)},
    )
    # Set transient rank field
    entry.rank = rank
    return entry


def make_score_event(
    account_id: AccountID | None = None,
    game_id: GameID | None = None,
    board_id: BoardID | None = None,
    identity_id: IdentityID | None = None,
    value: float | None = None,
    delta: float | None = None,
    **kwargs,
) -> ScoreEvent:
    """Factory for creating ScoreEvent domain objects.

    Args:
        account_id: Account ID (auto-generated if not provided).
        game_id: Game ID (auto-generated if not provided).
        board_id: Board ID (auto-generated if not provided).
        identity_id: Identity ID (auto-generated if not provided).
        value: Score value for RUN boards.
        delta: Delta value for COUNTER boards.
        **kwargs: Additional keyword arguments for ScoreEvent.

    Returns:
        ScoreEvent domain object.
    """
    # Build event_payload based on value/delta
    payload = {}
    if value is not None:
        payload["value"] = value
    if delta is not None:
        payload["delta"] = delta

    return ScoreEvent(
        id=kwargs.get("id", ScoreEventID()),
        account_id=account_id or AccountID(),
        game_id=game_id or GameID(),
        board_id=board_id or BoardID(),
        identity_id=identity_id or IdentityID(),
        event_payload=payload,
        **{k: v for k, v in kwargs.items() if k not in ("id", "event_payload")},
    )


def make_identity(
    account_id: AccountID | None = None,
    game_id: GameID | None = None,
    kind: IdentityKind = IdentityKind.DEVICE,
    external_key: str = "test-device-key",
    display_name: str | None = "TestPlayer",
    **kwargs,
) -> Identity:
    """Factory for creating Identity domain objects.

    Args:
        account_id: Account ID (auto-generated if not provided).
        game_id: Game ID (auto-generated if not provided).
        kind: Identity kind (default: DEVICE).
        external_key: External key for the identity.
        display_name: Player display name.
        **kwargs: Additional keyword arguments for Identity.

    Returns:
        Identity domain object.
    """
    return Identity(
        id=kwargs.get("id", IdentityID()),
        account_id=account_id or AccountID(),
        game_id=game_id or GameID(),
        kind=kind,
        external_key=external_key,
        display_name=display_name,
        **{k: v for k, v in kwargs.items() if k not in ("id",)},
    )


def make_paginated_result(
    items: list,
    has_next: bool = False,
    has_prev: bool = False,
    next_position: CursorPosition | None = None,
    prev_position: CursorPosition | None = None,
):
    """Factory for creating PaginatedResult objects.

    Args:
        items: List of items in the page.
        has_next: Whether there are more results after this page.
        has_prev: Whether there are results before this page.
        next_position: Position for next page cursor.
        prev_position: Position for previous page cursor.

    Returns:
        PaginatedResult instance.
    """
    return PaginatedResult(
        items=items,
        has_next=has_next,
        has_prev=has_prev,
        next_position=next_position,
        prev_position=prev_position,
    )


def make_anti_cheat_result(
    action: FlagAction = FlagAction.ACCEPT,
    reason: str | None = None,
) -> AntiCheatResult:
    """Factory for creating AntiCheatResult objects.

    Args:
        action: Action to take (ACCEPT/FLAG/REJECT).
        reason: Human-readable reason for the action.

    Returns:
        AntiCheatResult instance.
    """
    return AntiCheatResult(
        action=action,
        confidence=None,
        flag_type=None,
        reason=reason,
        metadata=None,
    )
