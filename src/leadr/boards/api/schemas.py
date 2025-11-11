"""API request and response models for boards."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from leadr.boards.domain.board import Board, KeepStrategy, SortDirection


class BoardCreateRequest(BaseModel):
    """Request model for creating a board."""

    account_id: UUID = Field(description="ID of the account this board belongs to")
    game_id: UUID = Field(description="ID of the game this board belongs to")
    name: str = Field(description="Name of the board")
    icon: str = Field(description="Icon identifier for the board")
    short_code: str = Field(description="Globally unique short code for direct sharing")
    unit: str = Field(description="Unit of measurement for scores (e.g., 'seconds', 'points')")
    is_active: bool = Field(description="Whether the board is currently active")
    sort_direction: SortDirection = Field(description="Direction to sort scores")
    keep_strategy: KeepStrategy = Field(
        description="Strategy for keeping multiple scores from the same user"
    )
    template_id: UUID | None = Field(
        default=None, description="Optional template ID this board was created from"
    )
    template_name: str | None = Field(
        default=None, description="Optional template name this board was created from"
    )
    starts_at: datetime | None = Field(
        default=None, description="Optional start time for time-bounded boards (UTC)"
    )
    ends_at: datetime | None = Field(
        default=None, description="Optional end time for time-bounded boards (UTC)"
    )
    tags: list[str] | None = Field(default=None, description="Optional list of tags for categorization")


class BoardUpdateRequest(BaseModel):
    """Request model for updating a board."""

    name: str | None = Field(default=None, description="Updated board name")
    icon: str | None = Field(default=None, description="Updated icon identifier")
    short_code: str | None = Field(default=None, description="Updated short code")
    unit: str | None = Field(default=None, description="Updated unit of measurement")
    is_active: bool | None = Field(default=None, description="Updated active status")
    sort_direction: SortDirection | None = Field(default=None, description="Updated sort direction")
    keep_strategy: KeepStrategy | None = Field(default=None, description="Updated keep strategy")
    template_id: UUID | None = Field(default=None, description="Updated template ID")
    template_name: str | None = Field(default=None, description="Updated template name")
    starts_at: datetime | None = Field(default=None, description="Updated start time")
    ends_at: datetime | None = Field(default=None, description="Updated end time")
    tags: list[str] | None = Field(default=None, description="Updated tags list")
    deleted: bool | None = Field(default=None, description="Set to true to soft delete the board")


class BoardResponse(BaseModel):
    """Response model for a board."""

    id: UUID = Field(description="Unique identifier for the board")
    account_id: UUID = Field(description="ID of the account this board belongs to")
    game_id: UUID = Field(description="ID of the game this board belongs to")
    name: str = Field(description="Name of the board")
    icon: str = Field(description="Icon identifier for the board")
    short_code: str = Field(description="Globally unique short code for direct sharing")
    unit: str = Field(description="Unit of measurement for scores")
    is_active: bool = Field(description="Whether the board is currently active")
    sort_direction: SortDirection = Field(description="Direction to sort scores")
    keep_strategy: KeepStrategy = Field(description="Strategy for keeping scores from same user")
    template_id: UUID | None = Field(
        default=None, description="Template ID this board was created from, or null"
    )
    template_name: str | None = Field(
        default=None, description="Template name this board was created from, or null"
    )
    starts_at: datetime | None = Field(default=None, description="Start time for time-bounded boards (UTC)")
    ends_at: datetime | None = Field(default=None, description="End time for time-bounded boards (UTC)")
    tags: list[str] = Field(default_factory=list, description="List of tags for categorization")
    created_at: datetime = Field(description="Timestamp when the board was created (UTC)")
    updated_at: datetime = Field(description="Timestamp of last update (UTC)")

    @classmethod
    def from_domain(cls, board: Board) -> "BoardResponse":
        """Convert domain entity to response model.

        Args:
            board: The domain Board entity to convert.

        Returns:
            BoardResponse with all fields populated from the domain entity.
        """
        return cls(
            id=board.id,
            account_id=board.account_id,
            game_id=board.game_id,
            name=board.name,
            icon=board.icon,
            short_code=board.short_code,
            unit=board.unit,
            is_active=board.is_active,
            sort_direction=board.sort_direction,
            keep_strategy=board.keep_strategy,
            template_id=board.template_id,
            template_name=board.template_name,
            starts_at=board.starts_at,
            ends_at=board.ends_at,
            tags=board.tags,
            created_at=board.created_at,
            updated_at=board.updated_at,
        )
