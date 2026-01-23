"""API response models for score events."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from leadr.common.domain.ids import AccountID, BoardID, GameID, IdentityID, ScoreEventID
from leadr.scores.domain.score_event import ScoreEvent


class ScoreEventResponse(BaseModel):
    """Response model for a score event (admin only).

    Score events are immutable facts about score submissions.
    They are append-only and cannot be updated or deleted.
    """

    id: ScoreEventID = Field(description="Unique identifier for the score event")
    account_id: AccountID = Field(description="ID of the account this event belongs to")
    game_id: GameID = Field(description="ID of the game this event belongs to")
    board_id: BoardID = Field(description="ID of the board this event was submitted to")
    identity_id: IdentityID = Field(description="ID of the identity that submitted this score")
    event_payload: dict[str, Any] = Field(
        description="Board-type-specific payload (value for RUN boards, delta for COUNTER)"
    )
    is_test: bool = Field(description="True if this was a test submission")
    timezone: str | None = Field(default=None, description="Timezone from GeoIP lookup")
    country: str | None = Field(default=None, description="Country code from GeoIP lookup")
    city: str | None = Field(default=None, description="City name from GeoIP lookup")
    created_at: datetime = Field(description="Timestamp when the event was created (UTC)")

    @classmethod
    def from_domain(cls, event: ScoreEvent) -> "ScoreEventResponse":
        """Convert domain entity to response model.

        Args:
            event: The domain ScoreEvent entity to convert.

        Returns:
            ScoreEventResponse with all fields populated from the domain entity.
        """
        return cls(
            id=event.id,
            account_id=event.account_id,
            game_id=event.game_id,
            board_id=event.board_id,
            identity_id=event.identity_id,
            event_payload=event.event_payload,
            is_test=event.is_test,
            timezone=event.timezone,
            country=event.country,
            city=event.city,
            created_at=event.created_at,
        )
