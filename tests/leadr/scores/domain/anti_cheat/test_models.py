"""Tests for anti-cheat domain entities."""

from datetime import UTC, datetime
from uuid import uuid4

from leadr.scores.domain.anti_cheat.enums import FlagConfidence, FlagType
from leadr.scores.domain.anti_cheat.models import ScoreFlag, ScoreSubmissionMeta


class TestScoreSubmissionMeta:
    """Tests for ScoreSubmissionMeta entity."""

    def test_create_submission_meta(self):
        """Test creating a ScoreSubmissionMeta entity."""
        score_id = uuid4()
        device_id = uuid4()
        board_id = uuid4()
        now = datetime.now(UTC)

        meta = ScoreSubmissionMeta(
            score_id=score_id,
            device_id=device_id,
            board_id=board_id,
            submission_count=1,
            last_submission_at=now,
        )

        assert meta.score_id == score_id
        assert meta.device_id == device_id
        assert meta.board_id == board_id
        assert meta.submission_count == 1
        assert meta.last_submission_at == now
        assert meta.id is not None  # Auto-generated
        assert meta.created_at is not None  # Auto-generated
        assert meta.updated_at is not None  # Auto-generated

    def test_submission_count_default(self):
        """Test that submission_count defaults to 1."""
        meta = ScoreSubmissionMeta(
            score_id=uuid4(),
            device_id=uuid4(),
            board_id=uuid4(),
            last_submission_at=datetime.now(UTC),
        )

        assert meta.submission_count == 1

    def test_update_submission_count(self):
        """Test updating submission count."""
        meta = ScoreSubmissionMeta(
            score_id=uuid4(),
            device_id=uuid4(),
            board_id=uuid4(),
            submission_count=1,
            last_submission_at=datetime.now(UTC),
        )

        # Increment count
        meta.submission_count = 2
        assert meta.submission_count == 2

    def test_update_last_submission_at(self):
        """Test updating last submission timestamp."""
        old_time = datetime.now(UTC)
        meta = ScoreSubmissionMeta(
            score_id=uuid4(),
            device_id=uuid4(),
            board_id=uuid4(),
            last_submission_at=old_time,
        )

        new_time = datetime.now(UTC)
        meta.last_submission_at = new_time
        assert meta.last_submission_at == new_time
        assert meta.last_submission_at != old_time


class TestScoreFlag:
    """Tests for ScoreFlag entity."""

    def test_create_score_flag(self):
        """Test creating a ScoreFlag entity."""
        score_id = uuid4()

        flag = ScoreFlag(
            score_id=score_id,
            flag_type=FlagType.RATE_LIMIT,
            confidence=FlagConfidence.HIGH,
            metadata={"submissions_count": 101, "limit": 100},
        )

        assert flag.score_id == score_id
        assert flag.flag_type == FlagType.RATE_LIMIT
        assert flag.confidence == FlagConfidence.HIGH
        assert flag.metadata == {"submissions_count": 101, "limit": 100}
        assert flag.status == "PENDING"  # Default
        assert flag.reviewed_at is None
        assert flag.reviewer_id is None
        assert flag.reviewer_decision is None
        assert flag.id is not None  # Auto-generated
        assert flag.created_at is not None  # Auto-generated

    def test_flag_metadata_defaults_to_empty_dict(self):
        """Test that metadata defaults to empty dict."""
        flag = ScoreFlag(
            score_id=uuid4(),
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.MEDIUM,
        )

        assert flag.metadata == {}

    def test_flag_status_default(self):
        """Test that status defaults to PENDING."""
        flag = ScoreFlag(
            score_id=uuid4(),
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
        )

        assert flag.status == "PENDING"

    def test_flag_with_review_data(self):
        """Test creating a flag with review information."""
        score_id = uuid4()
        reviewer_id = uuid4()
        reviewed_at = datetime.now(UTC)

        flag = ScoreFlag(
            score_id=score_id,
            flag_type=FlagType.OUTLIER,
            confidence=FlagConfidence.MEDIUM,
            metadata={"z_score": 4.5},
            status="FALSE_POSITIVE",
            reviewed_at=reviewed_at,
            reviewer_id=reviewer_id,
            reviewer_decision="Score was legitimate, player is exceptionally skilled",
        )

        assert flag.status == "FALSE_POSITIVE"
        assert flag.reviewed_at == reviewed_at
        assert flag.reviewer_id == reviewer_id
        assert flag.reviewer_decision == "Score was legitimate, player is exceptionally skilled"

    def test_flag_types_coverage(self):
        """Test creating flags with different types."""
        score_id = uuid4()

        # Test each flag type
        for flag_type in [
            FlagType.RATE_LIMIT,
            FlagType.DUPLICATE,
            FlagType.VELOCITY,
            FlagType.OUTLIER,
            FlagType.IMPOSSIBLE_VALUE,
            FlagType.PATTERN,
            FlagType.PROGRESSION,
            FlagType.CLUSTER,
        ]:
            flag = ScoreFlag(
                score_id=score_id,
                flag_type=flag_type,
                confidence=FlagConfidence.MEDIUM,
            )
            assert flag.flag_type == flag_type

    def test_flag_confidence_levels(self):
        """Test creating flags with different confidence levels."""
        score_id = uuid4()

        # Test each confidence level
        for confidence in [FlagConfidence.LOW, FlagConfidence.MEDIUM, FlagConfidence.HIGH]:
            flag = ScoreFlag(
                score_id=score_id,
                flag_type=FlagType.DUPLICATE,
                confidence=confidence,
            )
            assert flag.confidence == confidence
