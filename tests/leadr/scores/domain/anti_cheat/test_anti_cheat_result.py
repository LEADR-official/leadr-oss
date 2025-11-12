"""Tests for AntiCheatResult value object."""

from leadr.scores.domain.anti_cheat.enums import FlagAction, FlagConfidence, FlagType
from leadr.scores.domain.anti_cheat.models import AntiCheatResult


class TestAntiCheatResult:
    """Tests for AntiCheatResult value object."""

    def test_create_accept_result(self):
        """Test creating an ACCEPT result."""
        result = AntiCheatResult(
            action=FlagAction.ACCEPT,
            confidence=None,
            flag_type=None,
            reason=None,
            metadata=None,
        )

        assert result.action == FlagAction.ACCEPT
        assert result.confidence is None
        assert result.flag_type is None
        assert result.reason is None
        assert result.metadata is None

    def test_create_flag_result(self):
        """Test creating a FLAG result with details."""
        result = AntiCheatResult(
            action=FlagAction.FLAG,
            confidence=FlagConfidence.MEDIUM,
            flag_type=FlagType.DUPLICATE,
            reason="Duplicate score detected within 5 minute window",
            metadata={"duplicate_count": 3, "window_seconds": 300},
        )

        assert result.action == FlagAction.FLAG
        assert result.confidence == FlagConfidence.MEDIUM
        assert result.flag_type == FlagType.DUPLICATE
        assert result.reason == "Duplicate score detected within 5 minute window"
        assert result.metadata == {"duplicate_count": 3, "window_seconds": 300}

    def test_create_reject_result(self):
        """Test creating a REJECT result with high confidence."""
        result = AntiCheatResult(
            action=FlagAction.REJECT,
            confidence=FlagConfidence.HIGH,
            flag_type=FlagType.RATE_LIMIT,
            reason="Rate limit exceeded: 101 submissions in last hour (limit: 100)",
            metadata={"submissions_count": 101, "limit": 100, "window_seconds": 3600},
        )

        assert result.action == FlagAction.REJECT
        assert result.confidence == FlagConfidence.HIGH
        assert result.flag_type == FlagType.RATE_LIMIT
        assert "Rate limit exceeded" in result.reason
        assert result.metadata["submissions_count"] == 101

    def test_immutability(self):
        """Test that AntiCheatResult is immutable (frozen)."""
        result = AntiCheatResult(
            action=FlagAction.ACCEPT,
            confidence=None,
            flag_type=None,
            reason=None,
            metadata=None,
        )

        # Should not be able to modify fields
        try:
            result.action = FlagAction.REJECT  # type: ignore[misc]
            assert False, "Should not be able to modify frozen field"
        except (AttributeError, ValueError):
            pass  # Expected

    def test_metadata_can_be_empty_dict(self):
        """Test that metadata can be an empty dictionary."""
        result = AntiCheatResult(
            action=FlagAction.FLAG,
            confidence=FlagConfidence.LOW,
            flag_type=FlagType.PATTERN,
            reason="Suspicious pattern",
            metadata={},
        )

        assert result.metadata == {}

    def test_result_with_complex_metadata(self):
        """Test result with complex nested metadata."""
        result = AntiCheatResult(
            action=FlagAction.FLAG,
            confidence=FlagConfidence.MEDIUM,
            flag_type=FlagType.OUTLIER,
            reason="Score is 4.2 standard deviations from mean",
            metadata={
                "score_value": 999999.0,
                "board_stats": {
                    "mean": 1000.0,
                    "stddev": 500.0,
                    "sample_count": 150,
                },
                "z_score": 4.2,
                "threshold": 3.0,
            },
        )

        assert result.metadata["z_score"] == 4.2
        assert result.metadata["board_stats"]["mean"] == 1000.0
