"""Tests for anti-cheat ORM models."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from leadr.scores.adapters.orm import ScoreFlagORM, ScoreSubmissionMetaORM
from leadr.scores.domain.anti_cheat.enums import FlagConfidence, FlagType
from leadr.scores.domain.anti_cheat.models import ScoreFlag, ScoreSubmissionMeta


@pytest.mark.asyncio
class TestScoreSubmissionMetaORM:
    """Tests for ScoreSubmissionMetaORM model."""

    async def test_create_submission_meta_orm(self, db_session):
        """Test creating a ScoreSubmissionMetaORM instance."""
        score_id = uuid4()
        user_id = uuid4()
        board_id = uuid4()
        now = datetime.now(UTC)

        orm = ScoreSubmissionMetaORM(
            score_id=score_id,
            user_id=user_id,
            board_id=board_id,
            submission_count=1,
            last_submission_at=now,
        )

        db_session.add(orm)
        await db_session.commit()

        assert orm.id is not None
        assert orm.score_id == score_id
        assert orm.user_id == user_id
        assert orm.board_id == board_id
        assert orm.submission_count == 1
        assert orm.last_submission_at == now

    async def test_submission_meta_to_domain(self, db_session):
        """Test converting ORM to domain entity."""
        score_id = uuid4()
        user_id = uuid4()
        board_id = uuid4()
        now = datetime.now(UTC)

        orm = ScoreSubmissionMetaORM(
            score_id=score_id,
            user_id=user_id,
            board_id=board_id,
            submission_count=5,
            last_submission_at=now,
        )

        db_session.add(orm)
        await db_session.commit()

        domain = orm.to_domain()

        assert isinstance(domain, ScoreSubmissionMeta)
        assert domain.id == orm.id
        assert domain.score_id == score_id
        assert domain.user_id == user_id
        assert domain.board_id == board_id
        assert domain.submission_count == 5
        assert domain.last_submission_at == now
        assert domain.created_at == orm.created_at
        assert domain.updated_at == orm.updated_at

    async def test_submission_meta_from_domain(self, db_session):
        """Test converting domain entity to ORM."""
        score_id = uuid4()
        user_id = uuid4()
        board_id = uuid4()
        now = datetime.now(UTC)

        domain = ScoreSubmissionMeta(
            score_id=score_id,
            user_id=user_id,
            board_id=board_id,
            submission_count=3,
            last_submission_at=now,
        )

        orm = ScoreSubmissionMetaORM.from_domain(domain)

        assert orm.id == domain.id
        assert orm.score_id == score_id
        assert orm.user_id == user_id
        assert orm.board_id == board_id
        assert orm.submission_count == 3
        assert orm.last_submission_at == now
        assert orm.created_at == domain.created_at
        assert orm.updated_at == domain.updated_at


@pytest.mark.asyncio
class TestScoreFlagORM:
    """Tests for ScoreFlagORM model."""

    async def test_create_score_flag_orm(self, db_session):
        """Test creating a ScoreFlagORM instance."""
        score_id = uuid4()

        orm = ScoreFlagORM(
            score_id=score_id,
            flag_type=FlagType.RATE_LIMIT.value,
            confidence=FlagConfidence.HIGH.value,
            metadata={"submissions_count": 101, "limit": 100},
            status="PENDING",
        )

        db_session.add(orm)
        await db_session.commit()

        assert orm.id is not None
        assert orm.score_id == score_id
        assert orm.flag_type == "RATE_LIMIT"
        assert orm.confidence == "HIGH"
        assert orm.metadata == {"submissions_count": 101, "limit": 100}
        assert orm.status == "PENDING"
        assert orm.reviewed_at is None
        assert orm.reviewer_id is None
        assert orm.reviewer_decision is None

    async def test_score_flag_to_domain(self, db_session):
        """Test converting ORM to domain entity."""
        score_id = uuid4()

        orm = ScoreFlagORM(
            score_id=score_id,
            flag_type=FlagType.DUPLICATE.value,
            confidence=FlagConfidence.MEDIUM.value,
            metadata={"duplicate_count": 3},
            status="PENDING",
        )

        db_session.add(orm)
        await db_session.commit()

        domain = orm.to_domain()

        assert isinstance(domain, ScoreFlag)
        assert domain.id == orm.id
        assert domain.score_id == score_id
        assert domain.flag_type == FlagType.DUPLICATE
        assert domain.confidence == FlagConfidence.MEDIUM
        assert domain.metadata == {"duplicate_count": 3}
        assert domain.status == "PENDING"
        assert domain.created_at == orm.created_at

    async def test_score_flag_from_domain(self, db_session):
        """Test converting domain entity to ORM."""
        score_id = uuid4()

        domain = ScoreFlag(
            score_id=score_id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"time_delta_seconds": 0.5},
            status="PENDING",
        )

        orm = ScoreFlagORM.from_domain(domain)

        assert orm.id == domain.id
        assert orm.score_id == score_id
        assert orm.flag_type == "VELOCITY"
        assert orm.confidence == "HIGH"
        assert orm.metadata == {"time_delta_seconds": 0.5}
        assert orm.status == "PENDING"
        assert orm.created_at == domain.created_at

    async def test_score_flag_with_review_data(self, db_session):
        """Test flag with review information."""
        score_id = uuid4()
        reviewer_id = uuid4()
        reviewed_at = datetime.now(UTC)

        orm = ScoreFlagORM(
            score_id=score_id,
            flag_type=FlagType.OUTLIER.value,
            confidence=FlagConfidence.MEDIUM.value,
            metadata={"z_score": 4.5},
            status="FALSE_POSITIVE",
            reviewed_at=reviewed_at,
            reviewer_id=reviewer_id,
            reviewer_decision="Legitimate exceptional performance",
        )

        db_session.add(orm)
        await db_session.commit()

        domain = orm.to_domain()

        assert domain.status == "FALSE_POSITIVE"
        assert domain.reviewed_at == reviewed_at
        assert domain.reviewer_id == reviewer_id
        assert domain.reviewer_decision == "Legitimate exceptional performance"

    async def test_metadata_persistence(self, db_session):
        """Test that complex metadata persists correctly."""
        score_id = uuid4()

        complex_metadata = {
            "score_value": 999999.0,
            "board_stats": {"mean": 1000.0, "stddev": 500.0, "count": 150},
            "z_score": 4.2,
            "threshold": 3.0,
            "values": [1, 2, 3, 4, 5],
        }

        orm = ScoreFlagORM(
            score_id=score_id,
            flag_type=FlagType.OUTLIER.value,
            confidence=FlagConfidence.MEDIUM.value,
            metadata=complex_metadata,
        )

        db_session.add(orm)
        await db_session.commit()
        await db_session.refresh(orm)

        assert orm.metadata == complex_metadata
        assert orm.metadata["board_stats"]["mean"] == 1000.0
        assert orm.metadata["values"] == [1, 2, 3, 4, 5]
