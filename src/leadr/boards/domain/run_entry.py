"""RunEntry domain model for RUN_RUNS boards."""

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

    Attributes:
        id: Unique identifier for this run entry.
        board_id: The board this entry belongs to (immutable).
        identity_id: The identity that submitted this entry (immutable).
        score_event_id: The score event that created this entry (immutable).
        primary_value: The rankable value for this submission (immutable).
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
