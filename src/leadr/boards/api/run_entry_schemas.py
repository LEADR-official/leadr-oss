"""API response models for run entries."""

from datetime import datetime

from pydantic import BaseModel, Field

from leadr.boards.domain.run_entry import RunEntry
from leadr.common.domain.ids import BoardID, IdentityID, RunEntryID, ScoreEventID


class RunEntryResponse(BaseModel):
    """Response model for a run entry (admin only).

    Run entries represent individual scored submissions for RUN_RUNS boards
    where every submission is ranked.
    """

    id: RunEntryID = Field(description="Unique identifier for the run entry")
    board_id: BoardID = Field(description="ID of the board this entry belongs to")
    identity_id: IdentityID = Field(description="ID of the identity that submitted this entry")
    score_event_id: ScoreEventID = Field(
        description="ID of the score event that created this entry"
    )
    primary_value: float = Field(description="Rankable value for this submission")
    created_at: datetime = Field(description="Timestamp when the entry was created (UTC)")
    updated_at: datetime = Field(description="Timestamp when the entry was last updated (UTC)")

    @classmethod
    def from_domain(cls, entry: RunEntry) -> "RunEntryResponse":
        """Convert domain entity to response model.

        Args:
            entry: The domain RunEntry entity to convert.

        Returns:
            RunEntryResponse with all fields populated from the domain entity.
        """
        return cls(
            id=entry.id,
            board_id=entry.board_id,
            identity_id=entry.identity_id,
            score_event_id=entry.score_event_id,
            primary_value=entry.primary_value,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
