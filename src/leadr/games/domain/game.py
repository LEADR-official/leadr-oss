"""Game domain model."""

from uuid import UUID

from pydantic import Field, field_validator

from leadr.common.domain.models import Entity


class Game(Entity):
    """Game domain entity.

    Represents a game that belongs to an account. Games can have optional
    Steam integration via steam_app_id and can reference a default leaderboard.
    """

    account_id: UUID = Field(frozen=True)
    name: str
    steam_app_id: str | None = None
    default_board_id: UUID | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate game name is not empty."""
        if not value or not value.strip():
            raise ValueError("Game name cannot be empty")
        return value.strip()
