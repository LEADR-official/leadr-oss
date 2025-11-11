"""Score domain entity."""

from uuid import UUID

from pydantic import Field, field_validator

from leadr.common.domain.models import Entity


class Score(Entity):
    """
    Score represents a player's score submission for a board.

    Scores are immutable in terms of their associations (account, game, board, user)
    but mutable in terms of their value and metadata for corrections/updates.
    """

    account_id: UUID = Field(
        frozen=True, description="ID of the account this score belongs to (immutable)"
    )
    game_id: UUID = Field(
        frozen=True, description="ID of the game this score belongs to (immutable)"
    )
    board_id: UUID = Field(
        frozen=True, description="ID of the board this score belongs to (immutable)"
    )
    user_id: UUID = Field(
        frozen=True, description="ID of the user who submitted this score (immutable)"
    )
    player_name: str = Field(description="Display name of the player")
    value: float = Field(description="Numeric value of the score for sorting/comparison")
    value_display: str | None = Field(
        default=None,
        description="Optional formatted display string (e.g., '1:23.45', '1,234 points')",
    )
    filter_timezone: str | None = Field(
        default=None, description="Optional timezone filter for score categorization"
    )
    filter_country: str | None = Field(
        default=None, description="Optional country filter for score categorization"
    )
    filter_city: str | None = Field(
        default=None, description="Optional city filter for score categorization"
    )

    @field_validator("player_name")
    @classmethod
    def validate_player_name(cls, v: str) -> str:
        """Validate that player_name is not empty and strip whitespace.

        Args:
            v: The player_name to validate.

        Returns:
            The validated and trimmed player_name.

        Raises:
            ValueError: If player_name is empty or whitespace only.
        """
        v = v.strip()
        if not v:
            raise ValueError("player_name cannot be empty")
        return v
