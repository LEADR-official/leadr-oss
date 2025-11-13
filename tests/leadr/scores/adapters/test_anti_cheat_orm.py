"""Tests for anti-cheat ORM models."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from leadr.common.domain.ids import DeviceID
from leadr.scores.adapters.orm import ScoreFlagORM, ScoreSubmissionMetaORM
from leadr.scores.domain.anti_cheat.enums import FlagConfidence, FlagType, ScoreFlagStatus
from leadr.scores.domain.anti_cheat.models import ScoreFlag, ScoreSubmissionMeta


@pytest.mark.asyncio
class TestScoreSubmissionMetaORM:
    """Tests for ScoreSubmissionMetaORM model."""

    async def test_create_submission_meta_orm(self, db_session, test_score):
        """Test creating a ScoreSubmissionMetaORM instance."""
        now = datetime.now(UTC)
        device_id = DeviceID(uuid4())

        orm = ScoreSubmissionMetaORM(
            score_id=test_score.id.uuid,
            device_id=device_id,
            board_id=test_score.board_id.uuid,
            submission_count=1,
            last_submission_at=now,
        )

        db_session.add(orm)
        await db_session.commit()

        assert orm.id is not None
        assert orm.score_id == test_score.id.uuid
        assert orm.device_id == device_id
        assert orm.board_id == test_score.board_id.uuid
        assert orm.submission_count == 1
        assert orm.last_submission_at == now

    async def test_submission_meta_to_domain(self, db_session, test_score):
        """Test converting ORM to domain entity."""
        now = datetime.now(UTC)
        device_id = DeviceID(uuid4())

        orm = ScoreSubmissionMetaORM(
            score_id=test_score.id.uuid,
            device_id=device_id,
            board_id=test_score.board_id.uuid,
            submission_count=5,
            last_submission_at=now,
        )

        db_session.add(orm)
        await db_session.commit()

        domain = orm.to_domain()

        assert isinstance(domain, ScoreSubmissionMeta)
        assert domain.id == orm.id
        assert domain.score_id == test_score.id
        assert domain.device_id == device_id
        assert domain.board_id == test_score.board_id
        assert domain.submission_count == 5
        assert domain.last_submission_at == now
        assert domain.created_at == orm.created_at
        assert domain.updated_at == orm.updated_at

    async def test_submission_meta_from_domain(self, db_session, test_score):
        """Test converting domain entity to ORM."""
        now = datetime.now(UTC)
        device_id = DeviceID(uuid4())

        domain = ScoreSubmissionMeta(
            score_id=test_score.id,
            device_id=device_id,
            board_id=test_score.board_id,
            submission_count=3,
            last_submission_at=now,
        )

        orm = ScoreSubmissionMetaORM.from_domain(domain)

        assert orm.id == domain.id
        assert orm.score_id == test_score.id.uuid
        assert orm.device_id == device_id
        assert orm.board_id == test_score.board_id.uuid
        assert orm.submission_count == 3
        assert orm.last_submission_at == now
        assert orm.created_at == domain.created_at
        assert orm.updated_at == domain.updated_at


@pytest.mark.asyncio
class TestScoreFlagORM:
    """Tests for ScoreFlagORM model."""

    async def test_create_score_flag_orm(self, db_session, test_score):
        """Test creating a ScoreFlagORM instance."""
        orm = ScoreFlagORM(
            score_id=test_score.id.uuid,
            flag_type=FlagType.RATE_LIMIT.value,
            confidence=FlagConfidence.HIGH.value,
            flag_metadata={"submissions_count": 101, "limit": 100},
            status="PENDING",
        )

        db_session.add(orm)
        await db_session.commit()

        assert orm.id is not None
        assert orm.score_id == test_score.id.uuid
        assert orm.flag_type == "RATE_LIMIT"
        assert orm.confidence == "HIGH"
        assert orm.flag_metadata == {"submissions_count": 101, "limit": 100}
        assert orm.status == "PENDING"
        assert orm.reviewed_at is None
        assert orm.reviewer_id is None
        assert orm.reviewer_decision is None

    async def test_score_flag_to_domain(self, db_session, test_score):
        """Test converting ORM to domain entity."""
        orm = ScoreFlagORM(
            score_id=test_score.id.uuid,
            flag_type=FlagType.DUPLICATE.value,
            confidence=FlagConfidence.MEDIUM.value,
            flag_metadata={"duplicate_count": 3},
            status="PENDING",
        )

        db_session.add(orm)
        await db_session.commit()

        domain = orm.to_domain()

        assert isinstance(domain, ScoreFlag)
        assert domain.id == orm.id
        assert domain.score_id == test_score.id
        assert domain.flag_type == FlagType.DUPLICATE
        assert domain.confidence == FlagConfidence.MEDIUM
        assert domain.metadata == {"duplicate_count": 3}
        assert domain.status == "PENDING"
        assert domain.created_at == orm.created_at

    async def test_score_flag_from_domain(self, db_session, test_score):
        """Test converting domain entity to ORM."""
        domain = ScoreFlag(
            score_id=test_score.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"time_delta_seconds": 0.5},
            status=ScoreFlagStatus.PENDING,
        )

        orm = ScoreFlagORM.from_domain(domain)

        assert orm.id == domain.id
        assert orm.score_id == test_score.id.uuid
        assert orm.flag_type == "VELOCITY"
        assert orm.confidence == "HIGH"
        assert orm.flag_metadata == {"time_delta_seconds": 0.5}
        assert orm.status == "PENDING"
        assert orm.created_at == domain.created_at

    async def test_score_flag_with_review_data(self, db_session, test_score, test_user):
        """Test flag with review information."""
        reviewed_at = datetime.now(UTC)

        orm = ScoreFlagORM(
            score_id=test_score.id.uuid,
            flag_type=FlagType.OUTLIER.value,
            confidence=FlagConfidence.MEDIUM.value,
            flag_metadata={"z_score": 4.5},
            status="FALSE_POSITIVE",
            reviewed_at=reviewed_at,
            reviewer_id=test_user.id.uuid,
            reviewer_decision="Legitimate exceptional performance",
        )

        db_session.add(orm)
        await db_session.commit()

        domain = orm.to_domain()

        assert domain.status == "FALSE_POSITIVE"
        assert domain.reviewed_at == reviewed_at
        assert domain.reviewer_id is not None
        assert domain.reviewer_id.uuid == test_user.id.uuid
        assert domain.reviewer_decision == "Legitimate exceptional performance"

    async def test_metadata_persistence(self, db_session, test_score):
        """Test that complex metadata persists correctly."""
        complex_metadata = {
            "score_value": 999999.0,
            "board_stats": {"mean": 1000.0, "stddev": 500.0, "count": 150},
            "z_score": 4.2,
            "threshold": 3.0,
            "values": [1, 2, 3, 4, 5],
        }

        orm = ScoreFlagORM(
            score_id=test_score.id.uuid,
            flag_type=FlagType.OUTLIER.value,
            confidence=FlagConfidence.MEDIUM.value,
            flag_metadata=complex_metadata,
        )

        db_session.add(orm)
        await db_session.commit()
        await db_session.refresh(orm)

        assert orm.flag_metadata == complex_metadata
        assert orm.flag_metadata["board_stats"]["mean"] == 1000.0
        assert orm.flag_metadata["values"] == [1, 2, 3, 4, 5]
