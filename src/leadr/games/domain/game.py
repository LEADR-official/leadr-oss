"""Game domain model."""

from uuid import UUID

from pydantic import Field, field_validator

from leadr.common.domain.models import Entity


class Game(Entity):
    """Game domain entity.

    Represents a game that belongs to an account. Games can have optional
    Steam integration via steam_app_id and can reference a default leaderboard.

    Each game belongs to exactly one account and cannot be transferred. Games
    can be configured with Steam integration for syncing achievements or other
    Steam platform features.
    """

    account_id: UUID = Field(
        frozen=True, description="ID of the account this game belongs to (immutable)"
    )
    name: str = Field(description="Name of the game")
    steam_app_id: str | None = Field(
        default=None, description="Optional Steam App ID for platform integration"
    )
    default_board_id: UUID | None = Field(
        default=None, description="Optional default leaderboard ID for this game"
    )
    anti_cheat_enabled: bool = Field(
        default=True,
        description="Whether anti-cheat is enabled for this game (defaults to enabled)",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate game name is not empty.

        Args:
            value: The game name to validate.

        Returns:
            The validated and trimmed game name.

        Raises:
            ValueError: If game name is empty or whitespace only.
        """
        if not value or not value.strip():
            raise ValueError("Game name cannot be empty")
        return value.strip()
