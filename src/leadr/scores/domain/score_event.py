"""ScoreEvent domain model for append-only score event sourcing."""

from typing import Any

from pydantic import Field

from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    GameID,
    IdentityID,
    ScoreEventID,
)
from leadr.common.domain.models import ImmutableEntity


class ScoreEvent(ImmutableEntity):
    """Append-only score event entity.

    ScoreEvent represents an immutable fact about a score submission.
    Unlike regular entities, ScoreEvents:
    - Have no updated_at (immutable after creation)
    - Have no deleted_at (append-only, never soft-deleted)
    - Are the source of truth for score history

    The event_payload contains board-type-specific data:
    - RUN_IDENTITY/RUN_RUNS: {"value": <numeric>}
    - COUNTER: {"delta": <numeric>}
    - RATIO: No direct events (derived from other boards)

    Attributes:
        id: Unique identifier for this event.
        account_id: The account that owns this event.
        game_id: The game this event belongs to.
        board_id: The board this event was submitted to.
        identity_id: The identity that submitted this score.
        event_payload: Board-type-specific payload (value or delta).
        is_test: Whether this is a test submission (excluded from rankings).
        timezone: Timezone extracted from GeoIP lookup.
        country: Country code extracted from GeoIP lookup.
        city: City name extracted from GeoIP lookup.
        created_at: Timestamp when the event was created (UTC).
    """

    id: ScoreEventID = Field(
        frozen=True,
        default_factory=ScoreEventID,
        description="Unique identifier for this event",
    )
    account_id: AccountID = Field(description="Account that owns this event")
    game_id: GameID = Field(description="Game this event belongs to")
    board_id: BoardID = Field(description="Board this event was submitted to")
    identity_id: IdentityID = Field(description="Identity that submitted this score")
    event_payload: dict[str, Any] = Field(
        description="Board-type-specific payload (value for RUN boards, delta for COUNTER)"
    )
    is_test: bool = Field(
        default=False,
        description="Whether this is a test submission",
    )
    timezone: str | None = Field(
        default=None,
        description="Timezone from GeoIP lookup",
    )
    country: str | None = Field(
        default=None,
        description="Country code from GeoIP lookup",
    )
    city: str | None = Field(
        default=None,
        description="City name from GeoIP lookup",
    )
