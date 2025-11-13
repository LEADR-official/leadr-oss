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
