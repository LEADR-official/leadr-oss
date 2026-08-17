"""API request and response models for board templates."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from leadr.boards.domain.board import BoardType, KeepStrategy, SortDirection
from leadr.boards.domain.board_template import BoardTemplate
from leadr.common.domain.ids import AccountID, BoardTemplateID, GameID


class BoardTemplateCreateRequest(BaseModel):
    """Request model for creating a board template."""

    account_id: AccountID = Field(description="ID of the account this template belongs to")
    game_id: GameID = Field(description="ID of the game this template belongs to")
    name: str = Field(description="Name of the template")
    slug: str | None = Field(
        default=None, description="URL-friendly slug for boards created from this template"
    )
    repeat_interval: str = Field(
        description="PostgreSQL interval syntax for repeat frequency (e.g., '7 days', '1 month')"
    )
    next_run_at: datetime = Field(
        description="Next scheduled time to create a board from this template (UTC)"
    )
    is_active: bool = Field(description="Whether the template is currently active")
    is_published: bool = Field(
        default=True, description="Whether boards created from this template should be published"
    )
    unique_player_names: bool = Field(
        default=False,
        description="Whether player names must be unique on boards created from this template",
    )
    name_template: str | None = Field(
        default=None, description="Optional template string for generating board names"
    )
    series: str | None = Field(
        default=None, description="Optional series identifier for sequential board naming"
    )
    icon: str | None = Field(
        default="fa-crown",
        description="Icon identifier for boards created from this template",
    )
    unit: str | None = Field(
        default=None,
        description="Unit of measurement for scores (e.g., 'seconds', 'points')",
    )
    sort_direction: SortDirection = Field(
        default=SortDirection.DESCENDING,
        description="Direction to sort scores (ascending/descending)",
    )
    board_type: BoardType = Field(
        default=BoardType.RUN_IDENTITY,
        description="Type of board to create from this template",
    )
    keep_strategy: KeepStrategy | None = Field(
        default=None,
        description="Strategy for keeping multiple scores from the same user (RUN_IDENTITY only)",
    )
    starts_at: datetime | None = Field(
        default=None, description="Optional start time for time-bounded boards"
    )
    ends_at: datetime | None = Field(
        default=None, description="Optional end time for time-bounded boards"
    )
    tags: list[str] | None = Field(
        default=None,
        description="List of tags for categorizing boards created from this template",
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Reserved for future procedural generation (bounds, variables, randomization rules)"
        ),
    )


class BoardTemplateUpdateRequest(BaseModel):
    """Request model for updating a board template."""

    name: str | None = Field(default=None, description="Updated template name")
    slug: str | None = Field(default=None, description="Updated slug")
    name_template: str | None = Field(default=None, description="Updated name template")
    series: str | None = Field(default=None, description="Updated series identifier")
    icon: str | None = Field(default=None, description="Updated icon identifier")
    unit: str | None = Field(default=None, description="Updated unit of measurement")
    sort_direction: SortDirection | None = Field(default=None, description="Updated sort direction")
    keep_strategy: KeepStrategy | None = Field(default=None, description="Updated keep strategy")
    starts_at: datetime | None = Field(default=None, description="Updated start time")
    ends_at: datetime | None = Field(default=None, description="Updated end time")
    tags: list[str] | None = Field(default=None, description="Updated tags list")
    repeat_interval: str | None = Field(default=None, description="Updated repeat interval")
    config: dict[str, Any] | None = Field(
        default=None,
        description="Updated config (reserved for procedural generation)",
    )
    next_run_at: datetime | None = Field(default=None, description="Updated next run time")
    is_active: bool | None = Field(default=None, description="Updated active status")
    is_published: bool | None = Field(default=None, description="Updated published status")
    unique_player_names: bool | None = Field(
        default=None,
        description="Whether player names must be unique on boards created from this template",
    )
    deleted: bool | None = Field(
        default=None, description="Set to true to soft delete the template"
    )


class BoardTemplateResponse(BaseModel):
    """Response model for a board template."""

    id: BoardTemplateID = Field(description="Unique identifier for the template")
    account_id: AccountID = Field(description="ID of the account this template belongs to")
    game_id: GameID = Field(description="ID of the game this template belongs to")
    name: str = Field(description="Name of the template")
    slug: str | None = Field(
        description="URL-friendly slug for boards created from this template, or null"
    )
    name_template: str | None = Field(
        default=None, description="Template string for generating board names, or null"
    )
    series: str | None = Field(
        default=None, description="Series identifier for sequential board naming, or null"
    )
    icon: str | None = Field(description="Icon identifier for boards created from this template")
    unit: str | None = Field(
        description="Unit of measurement for scores (e.g., 'seconds', 'points')"
    )
    sort_direction: SortDirection = Field(
        description="Direction to sort scores (ascending/descending)"
    )
    board_type: BoardType = Field(description="Type of board to create from this template")
    keep_strategy: KeepStrategy = Field(
        description="Strategy for keeping multiple scores from the same user (RUN_IDENTITY only)"
    )
    starts_at: datetime | None = Field(description="Optional start time for time-bounded boards")
    ends_at: datetime | None = Field(description="Optional end time for time-bounded boards")
    tags: list[str] = Field(
        description="List of tags for categorizing boards created from this template"
    )
    repeat_interval: str = Field(description="Repeat frequency in PostgreSQL interval syntax")
    config: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Reserved for future procedural generation (bounds, variables, randomization rules)"
        ),
    )
    next_run_at: datetime = Field(description="Next scheduled run time (UTC)")
    is_active: bool = Field(description="Whether the template is currently active")
    is_published: bool = Field(
        description="Whether boards created from this template should be published"
    )
    unique_player_names: bool = Field(
        default=False,
        description="Whether player names must be unique on boards created from this template",
    )
    created_at: datetime = Field(description="Timestamp when the template was created (UTC)")
    updated_at: datetime = Field(description="Timestamp of last update (UTC)")

    @classmethod
    def from_domain(cls, template: BoardTemplate) -> "BoardTemplateResponse":
        """Convert domain entity to response model.

        Args:
            template: The domain BoardTemplate entity to convert.

        Returns:
            BoardTemplateResponse with all fields populated from the domain entity.
        """
        return cls(
            id=template.id,
            account_id=template.account_id,
            game_id=template.game_id,
            name=template.name,
            slug=template.slug,
            name_template=template.name_template,
            series=template.series,
            icon=template.icon,
            unit=template.unit,
            sort_direction=template.sort_direction,
            board_type=template.board_type,
            keep_strategy=template.keep_strategy,
            starts_at=template.starts_at,
            ends_at=template.ends_at,
            tags=template.tags,
            repeat_interval=template.repeat_interval,
            config=template.config,
            next_run_at=template.next_run_at,
            is_active=template.is_active,
            is_published=template.is_published,
            unique_player_names=template.unique_player_names,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )
