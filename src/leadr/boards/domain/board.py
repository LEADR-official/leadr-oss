"""Board domain model."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field, field_validator

from leadr.common.domain.models import Entity


class SortDirection(str, Enum):
    """Sort direction for board scores."""

    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


class KeepStrategy(str, Enum):
    """Strategy for keeping scores from the same user."""

    BEST_ONLY = "BEST_ONLY"
    LATEST_ONLY = "LATEST_ONLY"
    ALL = "ALL"


class Board(Entity):
    """Board domain entity.

    Represents a leaderboard/board that belongs to a game. Boards define how
    scores are tracked, sorted, and displayed. Each board has a globally unique
    short_code for direct sharing and can be time-bounded with start/end dates.

    Each board belongs to exactly one game and inherits the game's account for
    multi-tenancy. Boards can be created from templates and can have custom
    tags for categorization.
    """

    account_id: UUID = Field(
        frozen=True, description="ID of the account this board belongs to (immutable)"
    )
    game_id: UUID = Field(
        frozen=True, description="ID of the game this board belongs to (immutable)"
    )
    name: str = Field(description="Name of the board")
    icon: str = Field(description="Icon identifier for the board")
    short_code: str = Field(description="Globally unique short code for direct board sharing")
    unit: str = Field(description="Unit of measurement for scores (e.g., 'seconds', 'points')")
    is_active: bool = Field(description="Whether the board is currently active")
    sort_direction: SortDirection = Field(
        description="Direction to sort scores (ascending/descending)"
    )
    keep_strategy: KeepStrategy = Field(
        description="Strategy for keeping multiple scores from the same user"
    )
    template_id: UUID | None = Field(
        default=None, description="Optional template ID this board was created from"
    )
    template_name: str | None = Field(
        default=None, description="Optional name of the template this board was created from"
    )
    starts_at: datetime | None = Field(
        default=None, description="Optional start time for time-bounded boards"
    )
    ends_at: datetime | None = Field(
        default=None, description="Optional end time for time-bounded boards"
    )
    tags: list[str] = Field(
        default_factory=list, description="List of tags for categorizing the board"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate board name is not empty.

        Args:
            value: The board name to validate.

        Returns:
            The validated and trimmed board name.

        Raises:
            ValueError: If board name is empty or whitespace only.
        """
        if not value or not value.strip():
            raise ValueError("Board name cannot be empty")
        return value.strip()

    @field_validator("short_code")
    @classmethod
    def validate_short_code(cls, value: str) -> str:
        """Validate short_code is not empty.

        Args:
            value: The short_code to validate.

        Returns:
            The validated and trimmed short_code.

        Raises:
            ValueError: If short_code is empty or whitespace only.
        """
        if not value or not value.strip():
            raise ValueError("Board short_code cannot be empty")
        return value.strip()
