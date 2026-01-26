"""BoardState domain model for materialized ranking state."""

from typing import Any

from pydantic import Field

from leadr.common.domain.ids import BoardID, BoardStateID, IdentityID
from leadr.common.domain.models import Entity


class BoardState(Entity):
    """Materialized ranking state for a single identity on a single board.

    BoardState represents the current ranking state of an identity on a board.
    It is computed from score events and used for leaderboard queries.

    For RUN_IDENTITY boards: Contains the selected score based on keep_strategy.
    For RUN_RUNS boards: Not used (run_entries table is used instead).
    For COUNTER boards: Contains the accumulated total.
    For RATIO boards: Contains the computed ratio value.

    The aux field contains board-type-specific auxiliary data:
    - RUN_IDENTITY: {"selected_event_id": str, "event_count": int}
    - COUNTER: {"event_count": int, "last_event_id": str}
    - RATIO: {"numerator_value": float, "denominator_value": float}

    Denormalized fields (from Identity and ScoreEvent) are stored for query efficiency:
    - player_name: Display name at submission time
    - is_test: Test mode flag
    - timezone, country, city: Geo data from GeoIP
    - value_display: Formatted display string
    - metadata: Game-specific JSON

    Attributes:
        id: Unique identifier for this board state.
        board_id: The board this state belongs to (immutable).
        identity_id: The identity this state is for (immutable).
        primary_value: The rankable value (NULL = not rankable).
        aux: Board-type-specific auxiliary data.
        player_name: Display name at submission time.
        is_test: Whether this is a test submission.
        timezone: Timezone from GeoIP (optional).
        country: Country code from GeoIP (optional).
        city: City name from GeoIP (optional).
        value_display: Formatted display string (optional).
        metadata: Game-specific JSON metadata (optional).
        created_at: Timestamp when the state was created (UTC).
        updated_at: Timestamp when the state was last updated (UTC).
        deleted_at: Timestamp when the state was soft-deleted, or None.
    """

    id: BoardStateID = Field(
        frozen=True,
        default_factory=BoardStateID,
        description="Unique identifier for this board state",
    )
    board_id: BoardID = Field(
        frozen=True,
        description="Board this state belongs to (immutable)",
    )
    identity_id: IdentityID = Field(
        frozen=True,
        description="Identity this state is for (immutable)",
    )
    primary_value: float | None = Field(
        default=None,
        description="Rankable value (NULL = not rankable)",
    )
    aux: dict[str, Any] | None = Field(
        default=None,
        description="Board-type-specific auxiliary data",
    )
    # Denormalized fields for query efficiency
    player_name: str = Field(
        default="",
        description="Display name at submission time (from Identity)",
    )
    is_test: bool = Field(
        default=False,
        description="Whether this is a test submission (from ScoreEvent)",
    )
    timezone: str | None = Field(
        default=None,
        description="Timezone from GeoIP (from ScoreEvent)",
    )
    country: str | None = Field(
        default=None,
        description="Country code from GeoIP (from ScoreEvent)",
    )
    city: str | None = Field(
        default=None,
        description="City name from GeoIP (from ScoreEvent)",
    )
    value_display: str | None = Field(
        default=None,
        description="Formatted display string",
    )
    metadata: Any | None = Field(
        default=None,
        description="Game-specific JSON metadata",
    )
