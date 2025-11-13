"""API request and response models for scores."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from leadr.scores.domain.score import Score


class ScoreCreateRequest(BaseModel):
    """Request model for creating a score."""

    account_id: UUID = Field(description="ID of the account this score belongs to")
    game_id: UUID = Field(description="ID of the game this score belongs to")
    board_id: UUID = Field(description="ID of the board this score belongs to")
    device_id: UUID = Field(description="ID of the device that submitted this score")
    player_name: str = Field(description="Display name of the player")
    value: float = Field(description="Numeric value of the score for sorting/comparison")
    value_display: str | None = Field(
        default=None,
        description="Optional formatted display string (e.g., '1:23.45', '1,234 points')",
    )
    timezone: str | None = Field(default=None, description="Optional timezone for categorization")
    country: str | None = Field(default=None, description="Optional country for categorization")
    city: str | None = Field(default=None, description="Optional city for categorization")


class ScoreUpdateRequest(BaseModel):
    """Request model for updating a score."""

    player_name: str | None = Field(default=None, description="Updated player name")
    value: float | None = Field(default=None, description="Updated score value")
    value_display: str | None = Field(default=None, description="Updated display string")
    timezone: str | None = Field(default=None, description="Updated timezone")
    country: str | None = Field(default=None, description="Updated country")
    city: str | None = Field(default=None, description="Updated city")
    deleted: bool | None = Field(default=None, description="Set to true to soft delete the score")


class ScoreResponse(BaseModel):
    """Response model for a score."""

    id: UUID = Field(description="Unique identifier for the score")
    account_id: UUID = Field(description="ID of the account this score belongs to")
    game_id: UUID = Field(description="ID of the game this score belongs to")
    board_id: UUID = Field(description="ID of the board this score belongs to")
    device_id: UUID = Field(description="ID of the device that submitted this score")
    player_name: str = Field(description="Display name of the player")
    value: float = Field(description="Numeric value of the score")
    value_display: str | None = Field(default=None, description="Formatted display string, or null")
    timezone: str | None = Field(default=None, description="Timezone for categorization, or null")
    country: str | None = Field(default=None, description="Country for categorization, or null")
    city: str | None = Field(default=None, description="City for categorization, or null")
    created_at: datetime = Field(description="Timestamp when the score was created (UTC)")
    updated_at: datetime = Field(description="Timestamp of last update (UTC)")

    @classmethod
    def from_domain(cls, score: Score) -> "ScoreResponse":
        """Convert domain entity to response model.

        Args:
            score: The domain Score entity to convert.

        Returns:
            ScoreResponse with all fields populated from the domain entity.
        """
        return cls(
            id=score.id,
            account_id=score.account_id,
            game_id=score.game_id,
            board_id=score.board_id,
            device_id=score.device_id,
            player_name=score.player_name,
            value=score.value,
            value_display=score.value_display,
            timezone=score.timezone,
            country=score.country,
            city=score.city,
            created_at=score.created_at,
            updated_at=score.updated_at,
        )
