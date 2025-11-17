"""BoardTemplate domain model."""

import re
from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

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
    name_template: str | None = Field(
        default=None, description="Optional template string for generating board names"
    )
    counter: str | None = Field(
        default=None,
        description=(
            "Optional counter identifier for sequential board naming (e.g., 'weekly', 'seasonal')"
        ),
    )
    repeat_interval: str = Field(
        description="PostgreSQL interval syntax for repeat frequency (e.g., '7 days', '1 month')"
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration object for boards created from this template",
    )
    config_template: dict[str, Any] = Field(
        default_factory=dict,
        description="Template configuration for random generation or variable substitution",
    )
    next_run_at: datetime = Field(
        description="Next scheduled time to create a board from this template"
    )
    is_active: bool = Field(description="Whether the template is currently active")

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

    @field_validator("repeat_interval")
    @classmethod
    def validate_repeat_interval(cls, value: str) -> str:
        """Validate repeat_interval uses PostgreSQL interval syntax.

        Args:
            value: The interval string to validate.

        Returns:
            The validated interval string.

        Raises:
            ValueError: If interval syntax is invalid.
        """
        if not value or not value.strip():
            raise ValueError("repeat_interval cannot be empty")

        # PostgreSQL interval pattern:
        # Supports: "N unit" or "N unit M unit" format
        # Valid units: year(s), month(s), week(s), day(s), hour(s), minute(s), second(s)
        units = (
            r"(year|years|month|months|week|weeks|day|days|"
            r"hour|hours|minute|minutes|second|seconds)"
        )
        pattern = rf"^\d+\s+{units}(\s+\d+\s+{units})?$"

        if not re.match(pattern, value.strip(), re.IGNORECASE):
            raise ValueError(
                f"Invalid repeat_interval syntax: '{value}'. "
                "Expected PostgreSQL interval format (e.g., '7 days', '1 month', '1 day 2 hours')"
            )

        return value.strip()

    def generate_name(self, timestamp: datetime, counter_value: int | None) -> str:
        """Generate a board name using the name template.

        If name_template is None, returns the template's name.
        Otherwise, substitutes placeholders with values derived from the timestamp and counter.

        Supported placeholders:
        - {year}: 4-digit year (e.g., 2025)
        - {month}: Full month name (e.g., July)
        - {month_short}: Abbreviated month (e.g., Jul)
        - {week}: ISO week number (e.g., 29)
        - {quarter}: Quarter (e.g., Q1, Q2, Q3, Q4)
        - {date}: ISO date (e.g., 2025-07-15)
        - {counter}: Sequential counter value

        Args:
            timestamp: The datetime to use for generating time-based placeholders.
            counter_value: Optional counter value for {counter} placeholder.

        Returns:
            The generated board name.

        Raises:
            ValueError: If the name_template contains invalid placeholders or if
                       {counter} is used but counter_value is None.
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
            "counter",
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

        # Check if counter is required but not provided
        if "counter" in found_placeholders and counter_value is None:
            raise ValueError(
                "Template contains {counter} placeholder but counter_value was not provided"
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
            "counter": counter_value,
        }

        # Generate the board name
        return self.name_template.format(**context)
