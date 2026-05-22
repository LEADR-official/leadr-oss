"""BoardTemplate domain model."""

import re
from datetime import datetime
from typing import Any

from pydantic import Field, field_validator, model_validator

from leadr.boards.domain.board import BoardType, KeepStrategy, SortDirection
from leadr.boards.domain.interval_parser import normalize_interval
from leadr.common.domain.ids import AccountID, BoardTemplateID, GameID
from leadr.common.domain.models import Entity


class BoardTemplate(Entity):
    """BoardTemplate domain entity.

    Represents a template for automatically generating boards at regular intervals.
    Templates belong to a game and define the configuration for boards that will be
    created by the pg_cron scheduler.

    Each template specifies a repeat interval (PostgreSQL interval syntax), configuration
    for boards to be created, and can optionally use template variables in the name
    generation. Templates can be activated/deactivated and track the next scheduled run.
    """

    id: BoardTemplateID = Field(
        frozen=True,
        default_factory=BoardTemplateID,
        description="Unique board template identifier",
    )
    account_id: AccountID = Field(
        frozen=True, description="ID of the account this template belongs to (immutable)"
    )
    game_id: GameID = Field(
        frozen=True, description="ID of the game this template belongs to (immutable)"
    )
    name: str = Field(description="Name of the template")
    slug: str | None = Field(
        default=None, description="URL-friendly slug for boards created from this template"
    )
    name_template: str | None = Field(
        default=None, description="Optional template string for generating board names"
    )
    series: str | None = Field(
        default=None,
        description=(
            "Optional series identifier for sequential board naming (e.g., 'weekly', 'seasonal')"
        ),
    )
    icon: str | None = Field(
        description="Icon identifier for boards created from this template", default="fa-crown"
    )
    unit: str | None = Field(
        description="Unit of measurement for scores (e.g., 'seconds', 'points')", default=None
    )
    sort_direction: SortDirection = Field(
        description="Direction to sort scores (ascending/descending)",
        default=SortDirection.DESCENDING,
    )
    board_type: BoardType = Field(
        description="Type of board to create from this template",
        default=BoardType.RUN_IDENTITY,
    )
    keep_strategy: KeepStrategy = Field(
        description="Strategy for keeping multiple scores from the same user (RUN_IDENTITY only)",
        default=KeepStrategy.BEST,
    )
    starts_at: datetime | None = Field(
        default=None, description="Optional start time for time-bounded boards"
    )
    ends_at: datetime | None = Field(
        default=None, description="Optional end time for time-bounded boards"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="List of tags for categorizing boards created from this template",
    )
    repeat_interval: str = Field(
        description="PostgreSQL interval syntax for repeat frequency (e.g., '7 days', '1 month')"
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Reserved for future procedural generation (bounds, variables, randomization rules)"
        ),
    )
    next_run_at: datetime = Field(
        description="Next scheduled time to create a board from this template"
    )
    is_active: bool = Field(description="Whether the template is currently active")
    is_published: bool = Field(
        description="Whether boards created from this template should be published", default=True
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate template name is not empty.

        Args:
            value: The template name to validate.

        Returns:
            The validated and trimmed template name.

        Raises:
            ValueError: If template name is empty or whitespace only.
        """
        if not value or not value.strip():
            raise ValueError("Template name cannot be empty")
        return value.strip()

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        """Validate slug format (lowercase alphanumeric with hyphens).

        Args:
            value: The slug to validate, or None.

        Returns:
            The validated slug, or None if not provided.

        Raises:
            ValueError: If slug is invalid.
        """
        if value is None:
            return None
        if not value or not value.strip():
            raise ValueError("Template slug cannot be empty")
        if len(value) < 2:
            raise ValueError("Template slug must be at least 2 characters")
        if len(value) > 50:
            raise ValueError("Template slug must not exceed 50 characters")
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", value):
            raise ValueError(
                "Template slug must be lowercase alphanumeric with hyphens, "
                "and cannot start or end with a hyphen"
            )
        return value

    @field_validator("repeat_interval")
    @classmethod
    def validate_repeat_interval(cls, value: str) -> str:
        """Validate repeat_interval uses PostgreSQL interval syntax.

        Delegates to parse_interval() as the single source of truth for interval validation.

        Args:
            value: The interval string to validate.

        Returns:
            The validated interval string.

        Raises:
            ValueError: If interval syntax is invalid.
        """
        if not value or not value.strip():
            raise ValueError("repeat_interval cannot be empty")

        return normalize_interval(value)

    @model_validator(mode="after")
    def validate_board_type_keep_strategy(self) -> "BoardTemplate":
        """Validate board_type and keep_strategy combination.

        - RUN_IDENTITY boards must have a non-NA keep_strategy (FIRST, BEST, LATEST)
        - Non-RUN_IDENTITY boards (RUN_RUNS, COUNTER, RATIO) must have NA keep_strategy

        Returns:
            The validated BoardTemplate instance.

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

    def generate_name(self, timestamp: datetime, series_value: int | None) -> str:
        """Generate a board name using the name template.

        If name_template is None, returns the template's name.
        Otherwise, substitutes placeholders with values derived from the timestamp and series.

        Supported placeholders:
        - {year}: 4-digit year (e.g., 2025)
        - {month}: Full month name (e.g., July)
        - {month_short}: Abbreviated month (e.g., Jul)
        - {week}: ISO week number (e.g., 29)
        - {quarter}: Quarter (e.g., Q1, Q2, Q3, Q4)
        - {date}: ISO date (e.g., 2025-07-15)
        - {series}: Sequential series value

        Args:
            timestamp: The datetime to use for generating time-based placeholders.
            series_value: Optional series value for {series} placeholder.

        Returns:
            The generated board name.

        Raises:
            ValueError: If the name_template contains invalid placeholders or if
                       {series} is used but series_value is None.
        """
        if self.name_template is None:
            return self.name

        # Define valid placeholders
        valid_placeholders = {
            "year",
            "month",
            "month_short",
            "week",
            "quarter",
            "date",
            "series",
        }

        # Extract all placeholders from the template
        placeholder_pattern = r"\{(\w+)\}"
        found_placeholders = set(re.findall(placeholder_pattern, self.name_template))

        # Check for invalid placeholders
        invalid_placeholders = found_placeholders - valid_placeholders
        if invalid_placeholders:
            invalid_str = ", ".join(sorted(invalid_placeholders))
            valid_str = ", ".join(sorted(valid_placeholders))
            raise ValueError(
                f"Invalid placeholder(s) in name_template: {invalid_str}. "
                f"Valid placeholders are: {valid_str}"
            )

        # Check if series is required but not provided
        if "series" in found_placeholders and series_value is None:
            raise ValueError(
                "Template contains {series} placeholder but series_value was not provided"
            )

        # Calculate quarter (Q1, Q2, Q3, Q4)
        quarter = f"Q{(timestamp.month - 1) // 3 + 1}"

        # Build context for string formatting
        context = {
            "year": timestamp.year,
            "month": timestamp.strftime("%B"),  # Full month name
            "month_short": timestamp.strftime("%b"),  # Abbreviated month
            "week": timestamp.isocalendar()[1],  # ISO week number
            "quarter": quarter,
            "date": timestamp.strftime("%Y-%m-%d"),  # ISO date
            "series": series_value,
        }

        # Generate the board name
        return self.name_template.format(**context)
