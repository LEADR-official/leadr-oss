"""Shared test fixtures for ORM models.

These fixtures provide ORM instances (not domain entities) for unit tests,
particularly useful for testing ORM adapters and repositories directly.

Key principles:
- ORM models use raw UUIDs, not typed IDs (AccountID, GameID, etc.)
- IDs are auto-generated via default=uuid4 in Base class
- Fixtures create and persist objects to get auto-generated fields
- Use these for ORM-level tests; use domain fixtures from conftest for integration tests
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.adapters.orm import AccountORM, AccountStatusEnum, UserORM
from leadr.auth.adapters.orm import (
    APIKeyORM,
    APIKeyStatusEnum,
    DeviceORM,
    DeviceStatusEnum,
    IdentityKindEnum,
    IdentityORM,
    NonceORM,
    NonceStatusEnum,
)
from leadr.boards.adapters.orm import (
    BoardORM,
    BoardTemplateORM,
    BoardTypeEnum,
    KeepStrategyEnum,
)
from leadr.boards.domain.board import SortDirection
from leadr.games.adapters.orm import GameORM
from leadr.scores.adapters.orm import (
    ScoreEventORM,
    ScoreFlagORM,
    ScoreSubmissionMetaORM,
)
from leadr.scores.domain.anti_cheat.enums import FlagConfidence, FlagType, ScoreFlagStatus


@pytest_asyncio.fixture
async def account_orm(db_session: AsyncSession) -> AccountORM:
    """Create and persist a test AccountORM with auto-generated ID.

    Returns:
        AccountORM instance with all fields populated including auto-generated id.
    """
    account = AccountORM(
        name="Test Account",
        slug="test-account",
        status=AccountStatusEnum.ACTIVE,
    )
    db_session.add(account)
    await db_session.flush()
    return account


@pytest_asyncio.fixture
async def user_orm(db_session: AsyncSession, account_orm: AccountORM) -> UserORM:
    """Create and persist a test UserORM linked to account_orm.

    Args:
        account_orm: Parent account (auto-injected fixture).

    Returns:
        UserORM instance with auto-generated id.
    """
    user = UserORM(
        account_id=account_orm.id,  # Raw UUID from ORM
        email="test@example.com",
        display_name="Test User",
        super_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def game_orm(db_session: AsyncSession, account_orm: AccountORM) -> GameORM:
    """Create and persist a test GameORM linked to account_orm.

    Args:
        account_orm: Parent account (auto-injected fixture).

    Returns:
        GameORM instance with auto-generated id.
    """
    game = GameORM(
        account_id=account_orm.id,  # Raw UUID
        name="Test Game",
        slug="test-game",
        steam_app_id=None,
        default_board_id=None,
        anti_cheat_enabled=False,
    )
    db_session.add(game)
    await db_session.flush()
    return game


@pytest_asyncio.fixture
async def board_template_orm(
    db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
) -> BoardTemplateORM:
    """Create and persist a test BoardTemplateORM.

    Args:
        account_orm: Parent account (auto-injected fixture).
        game_orm: Parent game (auto-injected fixture).

    Returns:
        BoardTemplateORM instance with auto-generated id.
    """
    template = BoardTemplateORM(
        account_id=account_orm.id,  # Raw UUID
        game_id=game_orm.id,  # Raw UUID
        name="Test Template",
        name_template=None,
        repeat_interval="1 week",
        config={},
        config_template={},
        next_run_at=datetime.now(UTC) + timedelta(days=7),
        is_active=True,
    )
    db_session.add(template)
    await db_session.flush()
    return template


@pytest_asyncio.fixture
async def board_orm(
    db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
) -> BoardORM:
    """Create and persist a test BoardORM linked to account and game.

    Args:
        account_orm: Parent account (auto-injected fixture).
        game_orm: Parent game (auto-injected fixture).

    Returns:
        BoardORM instance with auto-generated id.
    """
    board = BoardORM(
        account_id=account_orm.id,  # Raw UUID
        game_id=game_orm.id,  # Raw UUID
        name="Test Board",
        slug="test-board",
        icon="trophy",
        short_code="TEST01",
        unit="points",
        is_active=True,
        sort_direction=SortDirection.DESCENDING.value,  # Use string value for sort_direction
        board_type=BoardTypeEnum.RUN_IDENTITY,  # Use ORM enum
        keep_strategy=KeepStrategyEnum.BEST,  # Use ORM enum
        created_from_template_id=None,
        tags=[],
    )
    db_session.add(board)
    await db_session.flush()
    return board


@pytest_asyncio.fixture
async def device_orm(
    db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
) -> DeviceORM:
    """Create and persist a test DeviceORM linked to account and game.

    Args:
        account_orm: Parent account (auto-injected fixture).
        game_orm: Parent game (auto-injected fixture).

    Returns:
        DeviceORM instance with auto-generated id.
    """
    now = datetime.now(UTC)
    device = DeviceORM(
        account_id=account_orm.id,  # Raw UUID
        game_id=game_orm.id,  # Raw UUID
        client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        status=DeviceStatusEnum.ACTIVE,
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(device)
    await db_session.flush()
    return device


@pytest_asyncio.fixture
async def identity_orm(
    db_session: AsyncSession, account_orm: AccountORM, game_orm: GameORM
) -> IdentityORM:
    """Create and persist a test IdentityORM linked to account and game.

    Args:
        account_orm: Parent account (auto-injected fixture).
        game_orm: Parent game (auto-injected fixture).

    Returns:
        IdentityORM instance with auto-generated id.
    """
    identity = IdentityORM(
        account_id=account_orm.id,  # Raw UUID
        game_id=game_orm.id,  # Raw UUID
        kind=IdentityKindEnum.DEVICE,
        external_key=f"dev_{uuid4()}",  # Device ID format
        display_name="Test Player",
    )
    db_session.add(identity)
    await db_session.flush()
    return identity


@pytest_asyncio.fixture
async def api_key_orm(
    db_session: AsyncSession, account_orm: AccountORM, user_orm: UserORM
) -> APIKeyORM:
    """Create and persist a test APIKeyORM linked to account and user.

    Args:
        account_orm: Parent account (auto-injected fixture).
        user_orm: Owner user (auto-injected fixture).

    Returns:
        APIKeyORM instance with auto-generated id.
    """
    api_key = APIKeyORM(
        account_id=account_orm.id,  # Raw UUID
        user_id=user_orm.id,  # Raw UUID
        name="Test API Key",
        key_hash="dummy_hash_for_testing",
        key_prefix="ldr_test",
        status=APIKeyStatusEnum.ACTIVE,
        expires_at=None,
    )
    db_session.add(api_key)
    await db_session.flush()
    return api_key


@pytest_asyncio.fixture
async def nonce_orm(db_session: AsyncSession, identity_orm: IdentityORM) -> NonceORM:
    """Create and persist a test NonceORM linked to identity.

    Args:
        identity_orm: Parent identity (auto-injected fixture).

    Returns:
        NonceORM instance with auto-generated id.
    """
    now = datetime.now(UTC)
    nonce = NonceORM(
        identity_id=identity_orm.id,  # Raw UUID
        nonce_value=str(uuid4()),
        status=NonceStatusEnum.PENDING,
        expires_at=now + timedelta(seconds=60),
    )
    db_session.add(nonce)
    await db_session.flush()
    return nonce


@pytest_asyncio.fixture
async def score_event_orm(
    db_session: AsyncSession,
    account_orm: AccountORM,
    game_orm: GameORM,
    board_orm: BoardORM,
    identity_orm: IdentityORM,
) -> ScoreEventORM:
    """Create and persist a test ScoreEventORM linked to account, game, board, and identity.

    Args:
        account_orm: Parent account (auto-injected fixture).
        game_orm: Parent game (auto-injected fixture).
        board_orm: Parent board (auto-injected fixture).
        identity_orm: Source identity (auto-injected fixture).

    Returns:
        ScoreEventORM instance with auto-generated id.
    """
    score_event = ScoreEventORM(
        account_id=account_orm.id,  # Raw UUID
        game_id=game_orm.id,  # Raw UUID
        board_id=board_orm.id,  # Raw UUID
        identity_id=identity_orm.id,  # Raw UUID
        event_payload={"value": 1000.0},
        is_test=False,
        timezone=None,
        country=None,
        city=None,
    )
    db_session.add(score_event)
    await db_session.flush()
    return score_event


@pytest_asyncio.fixture
async def score_flag_orm(db_session: AsyncSession, score_event_orm: ScoreEventORM) -> ScoreFlagORM:
    """Create and persist a test ScoreFlagORM linked to score event.

    Args:
        score_event_orm: Parent score event (auto-injected fixture).

    Returns:
        ScoreFlagORM instance with auto-generated id.
    """
    flag = ScoreFlagORM(
        score_event_id=score_event_orm.id,  # Raw UUID
        flag_type=FlagType.VELOCITY.value,
        confidence=FlagConfidence.MEDIUM.value,
        flag_metadata={"reason": "test"},
        status=ScoreFlagStatus.PENDING.value,
        reviewed_at=None,
        reviewer_id=None,
        reviewer_decision=None,
    )
    db_session.add(flag)
    await db_session.flush()
    return flag


@pytest_asyncio.fixture
async def score_submission_meta_orm(
    db_session: AsyncSession,
    score_event_orm: ScoreEventORM,
    identity_orm: IdentityORM,
    board_orm: BoardORM,
) -> ScoreSubmissionMetaORM:
    """Create and persist a test ScoreSubmissionMetaORM.

    Args:
        score_event_orm: Related score event (auto-injected fixture).
        identity_orm: Source identity (auto-injected fixture).
        board_orm: Target board (auto-injected fixture).

    Returns:
        ScoreSubmissionMetaORM instance with auto-generated id.
    """
    now = datetime.now(UTC)
    meta = ScoreSubmissionMetaORM(
        score_event_id=score_event_orm.id,  # Raw UUID
        identity_id=identity_orm.id,  # Raw UUID
        board_id=board_orm.id,  # Raw UUID
        submission_count=1,
        last_submission_at=now,
        last_score_value=1000.0,
    )
    db_session.add(meta)
    await db_session.flush()
    return meta
