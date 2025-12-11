"""Game domain model."""

import re

from pydantic import Field, field_validator

from leadr.common.domain.ids import AccountID, BoardID, GameID
from leadr.common.domain.models import Entity


class Game(Entity):
    """Game domain entity.

    Represents a game that belongs to an account. Games can have optional
    Steam integration via steam_app_id and can reference a default leaderboard.

    Each game belongs to exactly one account and cannot be transferred. Games
    can be configured with Steam integration for syncing achievements or other
    Steam platform features.
    """

    id: GameID = Field(
        frozen=True,
        default_factory=GameID,
        description="Unique game identifier",
    )
    account_id: AccountID = Field(
        frozen=True, description="ID of the account this game belongs to (immutable)"
    )
    name: str = Field(description="Name of the game")
    slug: str = Field(description="URL-friendly slug for the game (globally unique)")
    steam_app_id: str | None = Field(
        default=None, description="Optional Steam App ID for platform integration"
    )
    default_board_id: BoardID | None = Field(
        default=None, description="Optional default leaderboard ID for this game"
    )
    anti_cheat_enabled: bool = Field(
        default=True,
        description="Whether anti-cheat is enabled for this game (defaults to enabled)",
    )
    description: str | None = Field(default=None, description="Short description of the game")
    tags: list[str] = Field(
        default_factory=list, description="List of tags for categorizing the game"
    )
    page_url: str | None = Field(default=None, description="URL to the game's page or website")

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

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        """Validate slug format (lowercase alphanumeric with hyphens).

        Args:
            value: The slug to validate.

        Returns:
            The validated slug.

        Raises:
            ValueError: If slug format is invalid.
        """
        if not value:
            raise ValueError("Game slug cannot be empty")
        if len(value) < 2:
            raise ValueError("Game slug must be at least 2 characters")
        if len(value) > 50:
            raise ValueError("Game slug must not exceed 50 characters")
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", value):
            raise ValueError(
                "Game slug must be lowercase alphanumeric with hyphens, "
                "and cannot start or end with a hyphen"
            )
        return value
