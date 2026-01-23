"""Board domain model."""

import re
from datetime import datetime
from enum import Enum

from pydantic import Field, field_validator, model_validator

from leadr.common.domain.ids import AccountID, BoardID, BoardTemplateID, GameID
from leadr.common.domain.models import Entity


class SortDirection(str, Enum):
    """Sort direction for board scores."""

    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


class BoardType(str, Enum):
    """Type of board determining score behavior."""

    RUN_IDENTITY = "RUN_IDENTITY"  # One entry per identity, uses keep_strategy
    RUN_RUNS = "RUN_RUNS"  # Every submission is ranked
    COUNTER = "COUNTER"  # Accumulates delta values
    RATIO = "RATIO"  # Derived from two other boards


class KeepStrategy(str, Enum):
    """Strategy for keeping scores from the same user (RUN_IDENTITY boards only)."""

    FIRST = "FIRST"
    BEST = "BEST"
    LATEST = "LATEST"
    NA = "NA"  # For non-RUN_IDENTITY boards


class Board(Entity):
    """Board domain entity.

    Represents a leaderboard/board that belongs to a game. Boards define how
    scores are tracked, sorted, and displayed. Each board has a globally unique
    short_code for direct sharing and can be time-bounded with start/end dates.

    Each board belongs to exactly one game and inherits the game's account for
    multi-tenancy. Boards can be created from templates and can have custom
    tags for categorization.
    """

    id: BoardID = Field(
        frozen=True,
        default_factory=BoardID,
        description="Unique board identifier",
    )
    account_id: AccountID = Field(
        frozen=True, description="ID of the account this board belongs to (immutable)"
    )
    game_id: GameID = Field(
        frozen=True, description="ID of the game this board belongs to (immutable)"
    )
    name: str = Field(description="Name of the board")
    slug: str = Field(description="URL-friendly slug for the board (unique per game when active)")
    short_code: str = Field(description="Globally unique short code for direct board sharing")
    icon: str | None = Field(description="Icon identifier for the board", default="fa-crown")
    unit: str | None = Field(
        description="Unit of measurement for scores (e.g., 'seconds', 'points')", default=None
    )
    is_active: bool = Field(description="Whether the board is currently active", default=True)
    is_published: bool = Field(
        description="Whether the board is published and visible on public web views", default=True
    )
    sort_direction: SortDirection = Field(
        description="Direction to sort scores (ascending/descending)",
        default=SortDirection.DESCENDING,
    )
    board_type: BoardType = Field(
        description="Type of board determining score behavior",
        default=BoardType.RUN_IDENTITY,
    )
    keep_strategy: KeepStrategy = Field(
        description="Strategy for keeping multiple scores from the same user (RUN_IDENTITY only)",
        default=KeepStrategy.BEST,
    )
    created_from_template_id: BoardTemplateID | None = Field(
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
    description: str | None = Field(default=None, description="Short description of the board")

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

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        """Validate slug format (lowercase alphanumeric with hyphens).

        Args:
            value: The slug to validate.

        Returns:
            The validated slug.

        Raises:
            ValueError: If slug is invalid.
        """
        if not value:
            raise ValueError("Board slug cannot be empty")
        if len(value) < 2:
            raise ValueError("Board slug must be at least 2 characters")
        if len(value) > 50:
            raise ValueError("Board slug must not exceed 50 characters")
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", value):
            raise ValueError(
                "Board slug must be lowercase alphanumeric with hyphens, "
                "and cannot start or end with a hyphen"
            )
        return value

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
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_board_type_keep_strategy(self) -> "Board":
        """Validate board_type and keep_strategy combination.

        - RUN_IDENTITY boards must have a non-NA keep_strategy (FIRST, BEST, LATEST)
        - Non-RUN_IDENTITY boards (RUN_RUNS, COUNTER, RATIO) must have NA keep_strategy

        Returns:
            The validated Board instance.

        Raises:
            ValueError: If the board_type/keep_strategy combination is invalid.
        """
        if self.board_type == BoardType.RUN_IDENTITY:
            if self.keep_strategy == KeepStrategy.NA:
                raise ValueError(
                    "RUN_IDENTITY boards must have a keep_strategy of FIRST, BEST, or LATEST"
                )
        else:
            if self.keep_strategy != KeepStrategy.NA:
                raise ValueError(f"{self.board_type.value} boards must have keep_strategy=NA")
        return self
