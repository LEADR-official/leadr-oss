"""Tests for anti-cheat repository services."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.auth.adapters.orm import IdentityORM
from leadr.auth.domain.identity import IdentityKind
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.cursor import Cursor, PaginationDirection
from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    GameID,
    IdentityID,
    ScoreEventID,
    ScoreFlagID,
    ScoreSubmissionMetaID,
    UserID,
)
from leadr.scores.domain.anti_cheat.enums import FlagConfidence, FlagType, ScoreFlagStatus
from leadr.scores.domain.anti_cheat.models import ScoreFlag, ScoreSubmissionMeta
from leadr.scores.services.anti_cheat_repositories import (
    ScoreFlagRepository,
    ScoreSubmissionMetaRepository,
)


@pytest.mark.asyncio
class TestScoreSubmissionMetaRepository:
    """Test suite for ScoreSubmissionMeta repository."""

    async def test_create_submission_meta(
        self, db_session: AsyncSession, score_event_orm, identity_orm
    ):
        """Test creating a submission meta via repository."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)

        meta = ScoreSubmissionMeta(
            score_event_id=ScoreEventID(score_event_orm.id),
            identity_id=IdentityID(identity_orm.id),
            board_id=BoardID(score_event_orm.board_id),
            submission_count=1,
            last_submission_at=now,
        )

        created = await repo.create(meta)

        assert created.id == meta.id
        assert created.score_event_id == ScoreEventID(score_event_orm.id)
        assert created.identity_id == IdentityID(identity_orm.id)
        assert created.board_id == BoardID(score_event_orm.board_id)
        assert created.submission_count == 1
        assert created.last_submission_at == now

    async def test_get_submission_meta_by_id(
        self, db_session: AsyncSession, score_event_orm, identity_orm
    ):
        """Test retrieving a submission meta by ID."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)

        meta = ScoreSubmissionMeta(
            score_event_id=ScoreEventID(score_event_orm.id),
            identity_id=IdentityID(identity_orm.id),
            board_id=BoardID(score_event_orm.board_id),
            submission_count=5,
            last_submission_at=now,
        )
        await repo.create(meta)

        retrieved = await repo.get_by_id(meta.id)

        assert retrieved is not None
        assert retrieved.id == meta.id
        assert retrieved.submission_count == 5

    async def test_get_submission_meta_by_id_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent submission meta returns None."""
        repo = ScoreSubmissionMetaRepository(db_session)

        non_existent_id = ScoreSubmissionMetaID(uuid4())

        result = await repo.get_by_id(non_existent_id)

        assert result is None

    async def test_update_submission_meta(
        self, db_session: AsyncSession, score_event_orm, identity_orm
    ):
        """Test updating a submission meta."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)

        meta = ScoreSubmissionMeta(
            score_event_id=ScoreEventID(score_event_orm.id),
            identity_id=IdentityID(identity_orm.id),
            board_id=BoardID(score_event_orm.board_id),
            submission_count=1,
            last_submission_at=now,
        )
        await repo.create(meta)

        # Update it
        new_time = datetime.now(UTC)
        meta.submission_count = 10
        meta.last_submission_at = new_time
        updated = await repo.update(meta)

        assert updated.submission_count == 10
        assert updated.last_submission_at == new_time

    async def test_get_by_identity_and_board(
        self, db_session: AsyncSession, score_event_orm, identity_orm
    ):
        """Test retrieving submission meta by identity and board IDs."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)
        board_id = BoardID(score_event_orm.board_id)

        meta = ScoreSubmissionMeta(
            score_event_id=ScoreEventID(score_event_orm.id),
            identity_id=IdentityID(identity_orm.id),
            board_id=board_id,
            submission_count=3,
            last_submission_at=now,
        )
        await repo.create(meta)

        retrieved = await repo.get_by_identity_and_board(IdentityID(identity_orm.id), board_id)

        assert retrieved is not None
        assert retrieved.identity_id == IdentityID(identity_orm.id)
        assert retrieved.board_id == board_id
        assert retrieved.submission_count == 3

    async def test_get_by_identity_and_board_not_found(self, db_session: AsyncSession):
        """Test that get_by_identity_and_board returns None when not found."""
        repo = ScoreSubmissionMetaRepository(db_session)

        result = await repo.get_by_identity_and_board(IdentityID(uuid4()), BoardID(uuid4()))

        assert result is None


@pytest.mark.asyncio
class TestScoreFlagRepository:
    """Test suite for ScoreFlag repository."""

    async def test_create_flag(self, db_session: AsyncSession, score_event_orm):
        """Test creating a flag via repository."""
        repo = ScoreFlagRepository(db_session)

        flag = ScoreFlag(
            score_event_id=ScoreEventID(score_event_orm.id),
            flag_type=FlagType.RATE_LIMIT,
            confidence=FlagConfidence.HIGH,
            metadata={"submissions_count": 101, "limit": 100},
            status=ScoreFlagStatus.PENDING,
        )

        created = await repo.create(flag)

        assert created.id == flag.id
        assert created.score_event_id == ScoreEventID(score_event_orm.id)
        assert created.flag_type == FlagType.RATE_LIMIT
        assert created.confidence == FlagConfidence.HIGH
        assert created.metadata == {"submissions_count": 101, "limit": 100}
        assert created.status == "pending"

    async def test_get_flag_by_id(self, db_session: AsyncSession, score_event_orm):
        """Test retrieving a flag by ID."""
        repo = ScoreFlagRepository(db_session)

        flag = ScoreFlag(
            score_event_id=ScoreEventID(score_event_orm.id),
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.MEDIUM,
            metadata={"duplicate_count": 3},
            status=ScoreFlagStatus.PENDING,
        )
        await repo.create(flag)

        retrieved = await repo.get_by_id(flag.id)

        assert retrieved is not None
        assert retrieved.id == flag.id
        assert retrieved.flag_type == FlagType.DUPLICATE
        assert retrieved.confidence == FlagConfidence.MEDIUM

    async def test_get_flag_by_id_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent flag returns None."""
        repo = ScoreFlagRepository(db_session)
        non_existent_id = ScoreFlagID(uuid4())

        result = await repo.get_by_id(non_existent_id)

        assert result is None

    async def test_update_flag(self, db_session: AsyncSession, score_event_orm):
        """Test updating a flag."""
        repo = ScoreFlagRepository(db_session)

        flag = ScoreFlag(
            score_event_id=ScoreEventID(score_event_orm.id),
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"time_delta_seconds": 0.5},
            status=ScoreFlagStatus.PENDING,
        )
        await repo.create(flag)

        # Update it
        reviewed_at = datetime.now(UTC)
        reviewer_id = UserID(uuid4())
        flag.status = ScoreFlagStatus.FALSE_POSITIVE
        flag.reviewed_at = reviewed_at
        flag.reviewer_id = reviewer_id  # type: ignore[misc]
        flag.reviewer_decision = "Legitimate speed"
        updated = await repo.update(flag)

        assert updated.status == "false_positive"
        assert updated.reviewed_at == reviewed_at
        assert updated.reviewer_id == reviewer_id
        assert updated.reviewer_decision == "Legitimate speed"

    async def test_get_flags_by_score_event_id(self, db_session: AsyncSession, score_event_orm):
        """Test retrieving all flags for a score event."""
        repo = ScoreFlagRepository(db_session)
        score_event_id = ScoreEventID(score_event_orm.id)

        # Create multiple flags for the same score event
        flag1 = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.RATE_LIMIT,
            confidence=FlagConfidence.HIGH,
            metadata={"count": 100},
        )
        flag2 = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.MEDIUM,
            metadata={"dup": True},
        )

        await repo.create(flag1)
        await repo.create(flag2)

        # Retrieve all flags for this score event
        flags = await repo.get_flags_by_score_event_id(score_event_id)

        assert len(flags) == 2
        flag_types = {f.flag_type for f in flags}
        assert FlagType.RATE_LIMIT in flag_types
        assert FlagType.DUPLICATE in flag_types

    async def test_get_pending_flags(self, db_session: AsyncSession, score_event_orm):
        """Test retrieving only pending flags."""
        repo = ScoreFlagRepository(db_session)
        score_event_id = ScoreEventID(score_event_orm.id)

        # Create flags with different statuses
        pending_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.RATE_LIMIT,
            confidence=FlagConfidence.HIGH,
            status=ScoreFlagStatus.PENDING,
        )
        reviewed_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.MEDIUM,
            status=ScoreFlagStatus.FALSE_POSITIVE,
        )

        await repo.create(pending_flag)
        await repo.create(reviewed_flag)

        # Retrieve pending flags
        pending_flags = await repo.get_pending_flags()

        # Should only return pending flags
        assert len(pending_flags) >= 1
        assert all(f.status == "pending" for f in pending_flags)
        assert any(f.id == pending_flag.id for f in pending_flags)

    async def test_filter_basic_pagination(self, db_session: AsyncSession, score_event_orm):
        """Test basic pagination in filter."""
        repo = ScoreFlagRepository(db_session)
        score_event_id = ScoreEventID(score_event_orm.id)

        # Create several flags
        for i in range(5):
            flag = ScoreFlag(
                score_event_id=score_event_id,
                flag_type=FlagType.RATE_LIMIT,
                confidence=FlagConfidence.HIGH,
                metadata={"index": i},
            )
            await repo.create(flag)

        # Basic filter with pagination
        pagination = PaginationParams(cursor=None, limit=3, sort=None)
        result = await repo.filter(pagination=pagination)

        assert len(result.items) == 3
        assert result.has_next is True

    async def test_filter_by_status(self, db_session: AsyncSession, score_event_orm):
        """Test filtering flags by status."""
        repo = ScoreFlagRepository(db_session)
        score_event_id = ScoreEventID(score_event_orm.id)

        # Create flags with different statuses
        pending = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.RATE_LIMIT,
            confidence=FlagConfidence.HIGH,
            status=ScoreFlagStatus.PENDING,
        )
        confirmed = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.MEDIUM,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )
        await repo.create(pending)
        await repo.create(confirmed)

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repo.filter(status="pending", pagination=pagination)

        # Should find only pending flags
        pending_ids = {f.id for f in result.items if f.status == "pending"}
        assert pending.id in pending_ids

    async def test_filter_by_flag_type(self, db_session: AsyncSession, score_event_orm):
        """Test filtering flags by flag type."""
        repo = ScoreFlagRepository(db_session)
        score_event_id = ScoreEventID(score_event_orm.id)

        # Create flags with different types
        rate_limit_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.RATE_LIMIT,
            confidence=FlagConfidence.HIGH,
        )
        duplicate_flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.MEDIUM,
        )
        await repo.create(rate_limit_flag)
        await repo.create(duplicate_flag)

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repo.filter(flag_type="rate_limit", pagination=pagination)

        # Should find only rate_limit flags
        rate_limit_ids = {f.id for f in result.items if f.flag_type == FlagType.RATE_LIMIT}
        assert rate_limit_flag.id in rate_limit_ids

    async def test_filter_by_account_id(
        self, db_session: AsyncSession, score_event_orm, account_orm
    ):
        """Test filtering flags by account_id (via score_event join)."""
        repo = ScoreFlagRepository(db_session)
        score_event_id = ScoreEventID(score_event_orm.id)
        account_id = AccountID(account_orm.id)

        flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.RATE_LIMIT,
            confidence=FlagConfidence.HIGH,
        )
        await repo.create(flag)

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repo.filter(account_id=account_id, pagination=pagination)

        # Should find the flag since the score event belongs to this account
        assert any(f.id == flag.id for f in result.items)

    async def test_filter_by_board_id(self, db_session: AsyncSession, score_event_orm, board_orm):
        """Test filtering flags by board_id (via score_event join)."""
        repo = ScoreFlagRepository(db_session)
        score_event_id = ScoreEventID(score_event_orm.id)
        board_id = BoardID(board_orm.id)

        flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.MEDIUM,
        )
        await repo.create(flag)

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repo.filter(board_id=board_id, pagination=pagination)

        # Should find the flag since the score event is for this board
        assert any(f.id == flag.id for f in result.items)

    async def test_filter_by_game_id(self, db_session: AsyncSession, score_event_orm, game_orm):
        """Test filtering flags by game_id (via score_event join)."""
        repo = ScoreFlagRepository(db_session)
        score_event_id = ScoreEventID(score_event_orm.id)
        game_id = GameID(game_orm.id)

        flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.LOW,
        )
        await repo.create(flag)

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repo.filter(game_id=game_id, pagination=pagination)

        # Should find the flag since the score event is for this game
        assert any(f.id == flag.id for f in result.items)

    async def test_filter_invalid_sort_field(self, db_session: AsyncSession):
        """Test that filter raises ValueError for invalid sort field."""
        repo = ScoreFlagRepository(db_session)

        pagination = PaginationParams(cursor=None, limit=10, sort="invalid_field:asc")

        with pytest.raises(ValueError, match="Unknown sort field"):
            await repo.filter(pagination=pagination)

    async def test_filter_with_valid_sort(self, db_session: AsyncSession, score_event_orm):
        """Test filtering with valid sort field."""
        repo = ScoreFlagRepository(db_session)
        score_event_id = ScoreEventID(score_event_orm.id)

        # Create flags
        flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=FlagType.RATE_LIMIT,
            confidence=FlagConfidence.HIGH,
        )
        await repo.create(flag)

        # Sort by confidence
        pagination = PaginationParams(cursor=None, limit=10, sort="confidence:desc")
        result = await repo.filter(pagination=pagination)

        # Should not raise, just verify we get results
        assert result.items is not None

    async def test_filter_with_cursor_pagination(self, db_session: AsyncSession, score_event_orm):
        """Test filtering with cursor pagination."""
        repo = ScoreFlagRepository(db_session)
        score_event_id = ScoreEventID(score_event_orm.id)

        # Create several flags
        for i in range(5):
            flag = ScoreFlag(
                score_event_id=score_event_id,
                flag_type=FlagType.RATE_LIMIT,
                confidence=FlagConfidence.HIGH,
                metadata={"index": i},
            )
            await repo.create(flag)

        # First page
        pagination1 = PaginationParams(cursor=None, limit=2, sort=None)
        result1 = await repo.filter(pagination=pagination1)
        assert len(result1.items) == 2
        assert result1.has_next is True
        assert result1.next_position is not None

        # Build cursor for next page

        cursor = Cursor(
            position=result1.next_position,
            sort_fields=pagination1.sort_spec,
            filters={},
            direction=PaginationDirection.FORWARD,
        )
        cursor_str = cursor.encode()

        # Second page with cursor
        pagination2 = PaginationParams(cursor=cursor_str, limit=2, sort=None)
        result2 = await repo.filter(pagination=pagination2)

        # Should get different items
        assert len(result2.items) == 2
        first_page_ids = {f.id for f in result1.items}
        second_page_ids = {f.id for f in result2.items}
        assert first_page_ids.isdisjoint(second_page_ids)


@pytest.mark.asyncio
class TestScoreSubmissionMetaRepositoryFilter:
    """Test suite for ScoreSubmissionMetaRepository filter method."""

    async def test_filter_basic_pagination(
        self, db_session: AsyncSession, score_event_orm, identity_orm
    ):
        """Test basic pagination in filter."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)

        # Create several submission metas
        for i in range(5):
            # Need unique identities for each meta since (identity_id, board_id) is unique

            identity = IdentityORM(
                id=uuid4(),
                account_id=identity_orm.account_id,
                game_id=identity_orm.game_id,
                kind=IdentityKind.DEVICE.value,
                external_key=f"filter_test_{i}_{uuid4()}",
                display_name=f"FilterPlayer{i}",
                created_at=now,
                updated_at=now,
            )
            db_session.add(identity)
            await db_session.flush()

            meta = ScoreSubmissionMeta(
                score_event_id=ScoreEventID(score_event_orm.id),
                identity_id=IdentityID(identity.id),
                board_id=BoardID(score_event_orm.board_id),
                submission_count=i + 1,
                last_submission_at=now,
            )
            await repo.create(meta)

        # Basic filter with pagination
        pagination = PaginationParams(cursor=None, limit=3, sort=None)
        result = await repo.filter(pagination=pagination)

        assert len(result.items) == 3
        assert result.has_next is True

    async def test_filter_by_account_id(
        self, db_session: AsyncSession, score_event_orm, identity_orm, account_orm
    ):
        """Test filtering submission meta by account_id (via score_event join)."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)
        account_id = AccountID(account_orm.id)

        meta = ScoreSubmissionMeta(
            score_event_id=ScoreEventID(score_event_orm.id),
            identity_id=IdentityID(identity_orm.id),
            board_id=BoardID(score_event_orm.board_id),
            submission_count=1,
            last_submission_at=now,
        )
        await repo.create(meta)

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repo.filter(account_id=account_id, pagination=pagination)

        # Should find the meta since the score event belongs to this account
        assert any(m.id == meta.id for m in result.items)

    async def test_filter_by_board_id(
        self, db_session: AsyncSession, score_event_orm, identity_orm
    ):
        """Test filtering submission meta by board_id."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)
        board_id = BoardID(score_event_orm.board_id)

        meta = ScoreSubmissionMeta(
            score_event_id=ScoreEventID(score_event_orm.id),
            identity_id=IdentityID(identity_orm.id),
            board_id=board_id,
            submission_count=1,
            last_submission_at=now,
        )
        await repo.create(meta)

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repo.filter(board_id=board_id, pagination=pagination)

        # Should find the meta with matching board_id
        assert any(m.id == meta.id for m in result.items)

    async def test_filter_by_identity_id(
        self, db_session: AsyncSession, score_event_orm, identity_orm
    ):
        """Test filtering submission meta by identity_id."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)
        identity_id = IdentityID(identity_orm.id)

        meta = ScoreSubmissionMeta(
            score_event_id=ScoreEventID(score_event_orm.id),
            identity_id=identity_id,
            board_id=BoardID(score_event_orm.board_id),
            submission_count=1,
            last_submission_at=now,
        )
        await repo.create(meta)

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repo.filter(identity_id=identity_id, pagination=pagination)

        # Should find the meta with matching identity_id
        assert any(m.id == meta.id for m in result.items)

    async def test_filter_invalid_sort_field(self, db_session: AsyncSession):
        """Test that filter raises ValueError for invalid sort field."""
        repo = ScoreSubmissionMetaRepository(db_session)

        pagination = PaginationParams(cursor=None, limit=10, sort="nonexistent_field:asc")

        with pytest.raises(ValueError, match="Unknown sort field"):
            await repo.filter(pagination=pagination)

    async def test_filter_with_valid_sort(
        self, db_session: AsyncSession, score_event_orm, identity_orm
    ):
        """Test filtering with valid sort field."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)

        meta = ScoreSubmissionMeta(
            score_event_id=ScoreEventID(score_event_orm.id),
            identity_id=IdentityID(identity_orm.id),
            board_id=BoardID(score_event_orm.board_id),
            submission_count=1,
            last_submission_at=now,
        )
        await repo.create(meta)

        # Sort by submission_count
        pagination = PaginationParams(cursor=None, limit=10, sort="submission_count:desc")
        result = await repo.filter(pagination=pagination)

        # Should not raise, just verify we get results
        assert result.items is not None

    async def test_filter_with_cursor_pagination(
        self, db_session: AsyncSession, score_event_orm, identity_orm
    ):
        """Test filtering with cursor pagination."""
        repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)

        # Create several submission metas with unique identities

        for i in range(5):
            identity = IdentityORM(
                id=uuid4(),
                account_id=identity_orm.account_id,
                game_id=identity_orm.game_id,
                kind=IdentityKind.DEVICE.value,
                external_key=f"cursor_test_{i}_{uuid4()}",
                display_name=f"CursorPlayer{i}",
                created_at=now,
                updated_at=now,
            )
            db_session.add(identity)
            await db_session.flush()

            meta = ScoreSubmissionMeta(
                score_event_id=ScoreEventID(score_event_orm.id),
                identity_id=IdentityID(identity.id),
                board_id=BoardID(score_event_orm.board_id),
                submission_count=i + 1,
                last_submission_at=now,
            )
            await repo.create(meta)

        # First page
        pagination1 = PaginationParams(cursor=None, limit=2, sort=None)
        result1 = await repo.filter(pagination=pagination1)
        assert len(result1.items) == 2
        assert result1.has_next is True
        assert result1.next_position is not None

        # Build cursor for next page

        cursor = Cursor(
            position=result1.next_position,
            sort_fields=pagination1.sort_spec,
            filters={},
            direction=PaginationDirection.FORWARD,
        )
        cursor_str = cursor.encode()

        # Second page with cursor
        pagination2 = PaginationParams(cursor=cursor_str, limit=2, sort=None)
        result2 = await repo.filter(pagination=pagination2)

        # Should get different items
        assert len(result2.items) == 2
        first_page_ids = {m.id for m in result1.items}
        second_page_ids = {m.id for m in result2.items}
        assert first_page_ids.isdisjoint(second_page_ids)
