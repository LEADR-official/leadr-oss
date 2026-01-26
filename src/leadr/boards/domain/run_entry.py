"""RunEntry domain model for RUN_RUNS boards."""

from typing import Any

from pydantic import Field

from leadr.common.domain.ids import BoardID, IdentityID, RunEntryID, ScoreEventID
from leadr.common.domain.models import Entity


class RunEntry(Entity):
    """A single scored run entry for RUN_RUNS boards.

    RunEntry represents an individual submission on a RUN_RUNS board where
    every submission is ranked (as opposed to RUN_IDENTITY boards where
    only one entry per identity is kept based on keep_strategy).

    Each run entry is linked to a score event and is immutable except for
    soft-delete. The primary_value is the rankable value for leaderboard queries.

    Denormalized fields (from Identity and ScoreEvent) are stored for query efficiency:
    - player_name: Display name at submission time
    - is_test: Test mode flag
    - timezone, country, city: Geo data from GeoIP
    - value_display: Formatted display string
    - metadata: Game-specific JSON

    Attributes:
        id: Unique identifier for this run entry.
        board_id: The board this entry belongs to (immutable).
        identity_id: The identity that submitted this entry (immutable).
        score_event_id: The score event that created this entry (immutable).
        primary_value: The rankable value for this submission (immutable).
        player_name: Display name at submission time.
        is_test: Whether this is a test submission.
        timezone: Timezone from GeoIP (optional).
        country: Country code from GeoIP (optional).
        city: City name from GeoIP (optional).
        value_display: Formatted display string (optional).
        metadata: Game-specific JSON metadata (optional).
        created_at: Timestamp when the entry was created (UTC).
        updated_at: Timestamp when the entry was last updated (UTC).
        deleted_at: Timestamp when the entry was soft-deleted, or None.
    """

    id: RunEntryID = Field(
        frozen=True,
        default_factory=RunEntryID,
        description="Unique identifier for this run entry",
    )
    board_id: BoardID = Field(
        frozen=True,
        description="Board this entry belongs to (immutable)",
    )
    identity_id: IdentityID = Field(
        frozen=True,
        description="Identity that submitted this entry (immutable)",
    )
    score_event_id: ScoreEventID = Field(
        frozen=True,
        description="Score event that created this entry (immutable)",
    )
    primary_value: float = Field(
        frozen=True,
        description="Rankable value for this submission (immutable)",
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
    # Transient fields (not persisted in database)
    is_placeholder: bool = Field(
        default=False,
        description="True if this is a synthetic placeholder for around_value queries",
    )
    rank: int = Field(
        default=0,
        description="Computed rank (transient, not persisted)",
    )
