"""Tests for anti-cheat integration with event-sourced score submission.

These tests verify that the anti-cheat system works correctly with:
- ScoreEvent instead of Score
- IdentityID instead of DeviceID
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.services.account_service import AccountService
from leadr.auth.domain.identity import IdentityKind
from leadr.auth.services.identity_service import IdentityService
from leadr.boards.domain.board import BoardType, KeepStrategy
from leadr.boards.services.board_service import BoardService
from leadr.common.domain.ids import IdentityID, ScoreEventID
from leadr.games.services.game_service import GameService
from leadr.scores.domain.anti_cheat.enums import (
    FlagAction,
    FlagConfidence,
    FlagType,
    ScoreFlagStatus,
)
from leadr.scores.domain.anti_cheat.models import (
    ScoreFlag,
    ScoreSubmissionMeta,
)
from leadr.scores.domain.score_event import ScoreEvent


@pytest.mark.asyncio
class TestScoreSubmissionMetaWithIdentity:
    """Tests for ScoreSubmissionMeta domain model with identity support."""

    async def test_score_submission_meta_uses_identity_id(self):
        """ScoreSubmissionMeta should use identity_id instead of device_id."""
        identity_id = IdentityID()
        score_event_id = ScoreEventID()
        from leadr.common.domain.ids import BoardID

        meta = ScoreSubmissionMeta(
            score_event_id=score_event_id,
            identity_id=identity_id,
            board_id=BoardID(),
            submission_count=1,
            last_submission_at=datetime.now(UTC),
            last_score_value=100.0,
        )

        assert meta.identity_id == identity_id
        assert meta.score_event_id == score_event_id
        # device_id should no longer exist
        assert not hasattr(meta, "device_id") or getattr(meta, "device_id", None) is None

    async def test_score_submission_meta_has_required_fields(self):
        """ScoreSubmissionMeta should have all required fields."""
        identity_id = IdentityID()
        score_event_id = ScoreEventID()
        from leadr.common.domain.ids import BoardID

        board_id = BoardID()
        now = datetime.now(UTC)

        meta = ScoreSubmissionMeta(
            score_event_id=score_event_id,
            identity_id=identity_id,
            board_id=board_id,
            submission_count=5,
            last_submission_at=now,
            last_score_value=250.5,
        )

        assert meta.id is not None
        assert meta.score_event_id == score_event_id
        assert meta.identity_id == identity_id
        assert meta.board_id == board_id
        assert meta.submission_count == 5
        assert meta.last_submission_at == now
        assert meta.last_score_value == 250.5


@pytest.mark.asyncio
class TestScoreFlagWithScoreEvent:
    """Tests for ScoreFlag domain model with score_event_id support."""

    async def test_score_flag_uses_score_event_id(self):
        """ScoreFlag should use score_event_id instead of score_id."""
        score_event_id = ScoreEventID()

        flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"test": "data"},
        )

        assert flag.score_event_id == score_event_id
        # score_id should no longer exist
        assert not hasattr(flag, "score_id") or getattr(flag, "score_id", None) is None

    async def test_score_flag_default_status_is_pending(self):
        """ScoreFlag should default to PENDING status."""
        flag = ScoreFlag(
            score_event_id=ScoreEventID(),
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.MEDIUM,
        )

        assert flag.status == ScoreFlagStatus.PENDING

    async def test_score_flag_has_review_fields(self):
        """ScoreFlag should have review-related fields."""
        from leadr.common.domain.ids import UserID

        reviewer_id = UserID()
        reviewed_at = datetime.now(UTC)

        flag = ScoreFlag(
            score_event_id=ScoreEventID(),
            flag_type=FlagType.RATE_LIMIT,
            confidence=FlagConfidence.HIGH,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
            reviewed_at=reviewed_at,
            reviewer_id=reviewer_id,
            reviewer_decision="Confirmed as automated submission",
        )

        assert flag.status == ScoreFlagStatus.CONFIRMED_CHEAT
        assert flag.reviewed_at == reviewed_at
        assert flag.reviewer_id == reviewer_id
        assert flag.reviewer_decision == "Confirmed as automated submission"


@pytest.mark.asyncio
class TestAntiCheatServiceWithIdentity:
    """Tests for AntiCheatService with identity-based tracking."""

    async def test_anti_cheat_accepts_first_submission(
        self,
        db_session: AsyncSession,
    ):
        """First submission from an identity should be accepted."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Anti-Cheat Test Account",
            slug="anti-cheat-test-1",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Anti-Cheat Test Game",
            anti_cheat_enabled=True,
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Anti-Cheat Board",
            slug="anti-cheat-board-1",
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session)
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="anti-cheat-device-1",
        )

        # Create a score event
        score_event = ScoreEvent(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        # Check anti-cheat
        from leadr.scores.domain.anti_cheat.enums import TrustTier
        from leadr.scores.services.anti_cheat_service import AntiCheatService

        anti_cheat = AntiCheatService(db_session)
        result = await anti_cheat.check_submission_for_event(
            score_event=score_event,
            trust_tier=TrustTier.B,
            identity_id=identity.id,
            board_id=board.id,
        )

        assert result.action == FlagAction.ACCEPT
