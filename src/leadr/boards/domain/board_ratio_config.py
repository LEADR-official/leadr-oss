"""Board ratio config domain model."""

from enum import Enum

from pydantic import Field

from leadr.common.domain.ids import BoardID, BoardRatioConfigID
from leadr.common.domain.models import Entity


class ZeroDenominatorPolicy(str, Enum):
    """Policy for handling zero denominators in ratio calculations.

    Determines what value to use when the denominator is zero:
    - NULL: Return null/not rankable
    - ZERO: Return zero
    - INFINITY: Return infinity (highest rank)
    """

    NULL = "NULL"
    ZERO = "ZERO"
    INFINITY = "INFINITY"


class RatioDisplay(str, Enum):
    """Display format for ratio values.

    - RAW: Display the ratio value as-is (e.g., 0.75)
    - PERCENT: Display as percentage (e.g., 75%)
    """

    RAW = "RAW"
    PERCENT = "PERCENT"


class TieBreaker(str, Enum):
    """Tie-breaking strategy for equal ratios.

    NUMERATOR_DESC_DENOMINATOR_ASC: Higher numerator wins, then lower denominator.
    This favors players who achieved more (higher numerator) with less attempts
    (lower denominator).
    """

    NUMERATOR_DESC_DENOMINATOR_ASC = "NUMERATOR_DESC_DENOMINATOR_ASC"


class BoardRatioConfig(Entity):
    """Configuration for a RATIO board type.

    RATIO boards derive their ranking from two other boards (numerator and denominator).
    The ratio is calculated as: numerator_value / denominator_value * scale

    This is useful for metrics like:
    - Win rate: wins / games_played
    - Kill/Death ratio: kills / deaths
    - Accuracy: hits / shots_fired
    """

    id: BoardRatioConfigID = Field(frozen=True, default_factory=BoardRatioConfigID)

    # The ratio board this config belongs to
    board_id: BoardID = Field(frozen=True)

    # Source boards for ratio calculation
    numerator_board_id: BoardID = Field(frozen=True)
    denominator_board_id: BoardID = Field(frozen=True)

    # Zero denominator handling
    zero_denominator_policy: ZeroDenominatorPolicy = ZeroDenominatorPolicy.NULL

    # Minimum thresholds for ranking eligibility
    min_denominator: float = 0
    min_numerator: float = 0

    # Scaling factor for ratio storage (for integer storage precision)
    scale: int = 1_000_000

    # Display settings
    display: RatioDisplay = RatioDisplay.RAW
    decimals: int = 2

    # Tie-breaking strategy
    tie_breaker: TieBreaker = TieBreaker.NUMERATOR_DESC_DENOMINATOR_ASC
