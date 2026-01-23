"""Tests for BoardRatioConfig domain model."""

import pytest
from pydantic import ValidationError

from leadr.boards.domain.board_ratio_config import (
    BoardRatioConfig,
    RatioDisplay,
    TieBreaker,
    ZeroDenominatorPolicy,
)
from leadr.common.domain.ids import BoardID, BoardRatioConfigID


class TestZeroDenominatorPolicyEnum:
    """Test cases for ZeroDenominatorPolicy enum."""

    def test_null_value(self) -> None:
        """NULL policy returns null for zero denominator."""
        assert ZeroDenominatorPolicy.NULL == "NULL"

    def test_zero_value(self) -> None:
        """ZERO policy returns zero for zero denominator."""
        assert ZeroDenominatorPolicy.ZERO == "ZERO"

    def test_infinity_value(self) -> None:
        """INFINITY policy returns infinity for zero denominator."""
        assert ZeroDenominatorPolicy.INFINITY == "INFINITY"


class TestRatioDisplayEnum:
    """Test cases for RatioDisplay enum."""

    def test_raw_value(self) -> None:
        """RAW displays the ratio as-is."""
        assert RatioDisplay.RAW == "RAW"

    def test_percent_value(self) -> None:
        """PERCENT displays the ratio as percentage."""
        assert RatioDisplay.PERCENT == "PERCENT"


class TestTieBreakerEnum:
    """Test cases for TieBreaker enum."""

    def test_numerator_desc_denominator_asc_value(self) -> None:
        """Standard tiebreaker sorts by numerator desc then denominator asc."""
        assert TieBreaker.NUMERATOR_DESC_DENOMINATOR_ASC == "NUMERATOR_DESC_DENOMINATOR_ASC"


class TestBoardRatioConfigCreation:
    """Test cases for BoardRatioConfig creation."""

    def test_create_board_ratio_config_with_required_fields(self) -> None:
        """BoardRatioConfig can be created with required board IDs."""
        board_id = BoardID()
        numerator_board_id = BoardID()
        denominator_board_id = BoardID()

        config = BoardRatioConfig(
            board_id=board_id,
            numerator_board_id=numerator_board_id,
            denominator_board_id=denominator_board_id,
        )

        assert config.board_id == board_id
        assert config.numerator_board_id == numerator_board_id
        assert config.denominator_board_id == denominator_board_id

    def test_id_auto_generated(self) -> None:
        """ID is auto-generated with correct prefix."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        assert isinstance(config.id, BoardRatioConfigID)
        assert str(config.id).startswith("brc_")

    def test_default_zero_denominator_policy(self) -> None:
        """Zero denominator policy defaults to NULL."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        assert config.zero_denominator_policy == ZeroDenominatorPolicy.NULL

    def test_default_min_denominator(self) -> None:
        """Min denominator defaults to 0."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        assert config.min_denominator == 0

    def test_default_min_numerator(self) -> None:
        """Min numerator defaults to 0."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        assert config.min_numerator == 0

    def test_default_scale(self) -> None:
        """Scale defaults to 1_000_000."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        assert config.scale == 1_000_000

    def test_default_display(self) -> None:
        """Display defaults to RAW."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        assert config.display == RatioDisplay.RAW

    def test_default_decimals(self) -> None:
        """Decimals defaults to 2."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        assert config.decimals == 2

    def test_default_tie_breaker(self) -> None:
        """Tie breaker defaults to NUMERATOR_DESC_DENOMINATOR_ASC."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        assert config.tie_breaker == TieBreaker.NUMERATOR_DESC_DENOMINATOR_ASC

    def test_create_with_custom_policy(self) -> None:
        """BoardRatioConfig can be created with custom zero denominator policy."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
            zero_denominator_policy=ZeroDenominatorPolicy.ZERO,
        )

        assert config.zero_denominator_policy == ZeroDenominatorPolicy.ZERO

    def test_create_with_custom_display(self) -> None:
        """BoardRatioConfig can be created with PERCENT display."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
            display=RatioDisplay.PERCENT,
        )

        assert config.display == RatioDisplay.PERCENT

    def test_create_with_custom_scale(self) -> None:
        """BoardRatioConfig can use custom scale for precision."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
            scale=100,
        )

        assert config.scale == 100

    def test_create_with_min_denominator(self) -> None:
        """BoardRatioConfig can require minimum denominator for ranking."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
            min_denominator=10,
        )

        assert config.min_denominator == 10


class TestBoardRatioConfigImmutability:
    """Test cases for BoardRatioConfig field immutability."""

    def test_id_is_immutable(self) -> None:
        """ID cannot be changed after creation."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        with pytest.raises(ValidationError):
            config.id = BoardRatioConfigID()

    def test_board_id_is_immutable(self) -> None:
        """Board ID cannot be changed after creation."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        with pytest.raises(ValidationError):
            config.board_id = BoardID()

    def test_numerator_board_id_is_immutable(self) -> None:
        """Numerator board ID cannot be changed after creation."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        with pytest.raises(ValidationError):
            config.numerator_board_id = BoardID()

    def test_denominator_board_id_is_immutable(self) -> None:
        """Denominator board ID cannot be changed after creation."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        with pytest.raises(ValidationError):
            config.denominator_board_id = BoardID()


class TestBoardRatioConfigMutableFields:
    """Test cases for BoardRatioConfig mutable fields."""

    def test_zero_denominator_policy_is_mutable(self) -> None:
        """Zero denominator policy can be changed."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        config.zero_denominator_policy = ZeroDenominatorPolicy.INFINITY

        assert config.zero_denominator_policy == ZeroDenominatorPolicy.INFINITY

    def test_min_denominator_is_mutable(self) -> None:
        """Min denominator can be changed."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        config.min_denominator = 5

        assert config.min_denominator == 5

    def test_display_is_mutable(self) -> None:
        """Display can be changed."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        config.display = RatioDisplay.PERCENT

        assert config.display == RatioDisplay.PERCENT


class TestBoardRatioConfigSoftDelete:
    """Test cases for BoardRatioConfig soft delete."""

    def test_deleted_at_defaults_to_none(self) -> None:
        """deleted_at defaults to None."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        assert config.deleted_at is None

    def test_is_deleted_returns_false_when_not_deleted(self) -> None:
        """is_deleted returns False when deleted_at is None."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        assert config.is_deleted is False

    def test_soft_delete_sets_deleted_at(self) -> None:
        """soft_delete sets deleted_at to current time."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        config.soft_delete()

        assert config.deleted_at is not None
        assert config.is_deleted is True


class TestBoardRatioConfigSerialization:
    """Test cases for BoardRatioConfig serialization."""

    def test_model_dump_includes_all_fields(self) -> None:
        """model_dump() returns all fields."""
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        data = config.model_dump()

        assert "id" in data
        assert "board_id" in data
        assert "numerator_board_id" in data
        assert "denominator_board_id" in data
        assert "zero_denominator_policy" in data
        assert "min_denominator" in data
        assert "min_numerator" in data
        assert "scale" in data
        assert "display" in data
        assert "decimals" in data
        assert "tie_breaker" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "deleted_at" in data
