"""API request and response models for board templates."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from leadr.boards.domain.board_template import BoardTemplate
from leadr.common.domain.ids import AccountID, BoardTemplateID, GameID


class BoardTemplateCreateRequest(BaseModel):
    """Request model for creating a board template."""

    account_id: AccountID = Field(description="ID of the account this template belongs to")
    game_id: GameID = Field(description="ID of the game this template belongs to")
    name: str = Field(description="Name of the template")
    repeat_interval: str = Field(
        description="PostgreSQL interval syntax for repeat frequency (e.g., '7 days', '1 month')"
    )
    next_run_at: datetime = Field(
        description="Next scheduled time to create a board from this template (UTC)"
    )
    is_active: bool = Field(description="Whether the template is currently active")
    name_template: str | None = Field(
        default=None, description="Optional template string for generating board names"
    )
    counter: str | None = Field(
        default=None, description="Optional counter identifier for sequential board naming"
    )
    config: dict[str, Any] | None = Field(
        default=None, description="Optional configuration for boards created from this template"
    )
    config_template: dict[str, Any] | None = Field(
        default=None, description="Optional template configuration for random generation"
    )


class BoardTemplateUpdateRequest(BaseModel):
    """Request model for updating a board template."""

    name: str | None = Field(default=None, description="Updated template name")
    name_template: str | None = Field(default=None, description="Updated name template")
    counter: str | None = Field(default=None, description="Updated counter identifier")
    repeat_interval: str | None = Field(default=None, description="Updated repeat interval")
    config: dict[str, Any] | None = Field(default=None, description="Updated config")
    config_template: dict[str, Any] | None = Field(
        default=None, description="Updated config template"
    )
    next_run_at: datetime | None = Field(default=None, description="Updated next run time")
    is_active: bool | None = Field(default=None, description="Updated active status")
    deleted: bool | None = Field(
        default=None, description="Set to true to soft delete the template"
    )


class BoardTemplateResponse(BaseModel):
    """Response model for a board template."""

    id: BoardTemplateID = Field(description="Unique identifier for the template")
    account_id: AccountID = Field(description="ID of the account this template belongs to")
    game_id: GameID = Field(description="ID of the game this template belongs to")
    name: str = Field(description="Name of the template")
    name_template: str | None = Field(
        default=None, description="Template string for generating board names, or null"
    )
    counter: str | None = Field(
        default=None, description="Counter identifier for sequential board naming, or null"
    )
    repeat_interval: str = Field(description="Repeat frequency in PostgreSQL interval syntax")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Configuration for boards created from this template"
    )
    config_template: dict[str, Any] = Field(
        default_factory=dict, description="Template configuration for random generation"
    )
    next_run_at: datetime = Field(description="Next scheduled run time (UTC)")
    is_active: bool = Field(description="Whether the template is currently active")
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
            name_template=template.name_template,
            counter=template.counter,
            repeat_interval=template.repeat_interval,
            config=template.config,
            config_template=template.config_template,
            next_run_at=template.next_run_at,
            is_active=template.is_active,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )
