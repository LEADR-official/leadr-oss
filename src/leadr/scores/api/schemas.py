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
    filter_timezone: str | None = Field(
        default=None, description="Optional timezone filter for categorization"
    )
    filter_country: str | None = Field(
        default=None, description="Optional country filter for categorization"
    )
    filter_city: str | None = Field(
        default=None, description="Optional city filter for categorization"
    )


class ScoreUpdateRequest(BaseModel):
    """Request model for updating a score."""

    player_name: str | None = Field(default=None, description="Updated player name")
    value: float | None = Field(default=None, description="Updated score value")
    value_display: str | None = Field(default=None, description="Updated display string")
    filter_timezone: str | None = Field(default=None, description="Updated timezone filter")
    filter_country: str | None = Field(default=None, description="Updated country filter")
    filter_city: str | None = Field(default=None, description="Updated city filter")
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
    filter_timezone: str | None = Field(
        default=None, description="Timezone filter for categorization, or null"
    )
    filter_country: str | None = Field(
        default=None, description="Country filter for categorization, or null"
    )
    filter_city: str | None = Field(
        default=None, description="City filter for categorization, or null"
    )
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
            filter_timezone=score.filter_timezone,
            filter_country=score.filter_country,
            filter_city=score.filter_city,
            created_at=score.created_at,
            updated_at=score.updated_at,
        )
