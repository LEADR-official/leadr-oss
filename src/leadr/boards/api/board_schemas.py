"""API request and response models for boards."""

from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from leadr.boards.domain.board import Board, BoardType, KeepStrategy, SortDirection
from leadr.boards.domain.board_ratio_config import (
    BoardRatioConfig,
    RatioDisplay,
    TieBreaker,
    ZeroDenominatorPolicy,
)
from leadr.common.domain.ids import AccountID, BoardID, BoardRatioConfigID, BoardTemplateID, GameID
from leadr.config import settings


class BoardRatioConfigRequest(BaseModel):
    """Request model for ratio config when creating/updating a RATIO board."""

    numerator_board_id: BoardID = Field(description="ID of the numerator board")
    denominator_board_id: BoardID = Field(description="ID of the denominator board")
    zero_denominator_policy: ZeroDenominatorPolicy = Field(
        default=ZeroDenominatorPolicy.NULL,
        description="How to handle zero denominators",
    )
    min_denominator: float = Field(
        default=0,
        description="Minimum denominator value for ranking eligibility",
    )
    min_numerator: float = Field(
        default=0,
        description="Minimum numerator value for ranking eligibility",
    )
    scale: int = Field(
        default=1_000_000,
        description="Scaling factor for ratio storage precision",
    )
    display: RatioDisplay = Field(
        default=RatioDisplay.RAW,
        description="Display format for ratio values",
    )
    decimals: int = Field(
        default=2,
        description="Number of decimal places for display",
    )
    tie_breaker: TieBreaker = Field(
        default=TieBreaker.NUMERATOR_DESC_DENOMINATOR_ASC,
        description="Strategy for breaking ties",
    )


class BoardRatioConfigResponse(BaseModel):
    """Response model for ratio config."""

    id: BoardRatioConfigID = Field(description="Unique identifier for the ratio config")
    numerator_board_id: BoardID = Field(description="ID of the numerator board")
    denominator_board_id: BoardID = Field(description="ID of the denominator board")
    zero_denominator_policy: ZeroDenominatorPolicy = Field(
        description="How zero denominators are handled"
    )
    min_denominator: float = Field(description="Minimum denominator for ranking eligibility")
    min_numerator: float = Field(description="Minimum numerator for ranking eligibility")
    scale: int = Field(description="Scaling factor for ratio storage")
    display: RatioDisplay = Field(description="Display format for ratio values")
    decimals: int = Field(description="Number of decimal places for display")
    tie_breaker: TieBreaker = Field(description="Strategy for breaking ties")
    created_at: datetime = Field(description="Timestamp when the config was created (UTC)")
    updated_at: datetime = Field(description="Timestamp of last update (UTC)")

    @classmethod
    def from_domain(cls, config: BoardRatioConfig) -> "BoardRatioConfigResponse":
        """Convert domain entity to response model."""
        return cls(
            id=config.id,
            numerator_board_id=config.numerator_board_id,
            denominator_board_id=config.denominator_board_id,
            zero_denominator_policy=config.zero_denominator_policy,
            min_denominator=config.min_denominator,
            min_numerator=config.min_numerator,
            scale=config.scale,
            display=config.display,
            decimals=config.decimals,
            tie_breaker=config.tie_breaker,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )


class BoardCreateRequest(BaseModel):
    """Request model for creating a board."""

    account_id: AccountID = Field(description="ID of the account this board belongs to")
    game_id: GameID = Field(description="ID of the game this board belongs to")
    name: str = Field(description="Name of the board")
    slug: str | None = Field(
        default=None,
        description="Optional URL-friendly slug. If not provided, will be auto-generated from name",
    )
    icon: str | None = Field(
        default="fa-crown", description="Icon identifier for the board. Defaults to 'fa-crown'"
    )
    short_code: str | None = Field(
        default=None,
        description="Globally unique short code for direct sharing. Auto-generated if not provided",
    )
    unit: str | None = Field(
        default=None,
        description="Unit of measurement for scores (e.g., 'seconds', 'points'). Optional",
    )
    is_active: bool = Field(default=True, description="Whether the board is currently active")
    is_published: bool = Field(
        default=True, description="Whether the board is published and visible on public web views"
    )
    unique_player_names: bool = Field(
        default=False,
        description="Whether player names must be unique on this board (case-insensitive)",
    )
    sort_direction: SortDirection = Field(
        default=SortDirection.DESCENDING, description="Direction to sort scores"
    )
    board_type: BoardType = Field(
        default=BoardType.RUN_IDENTITY,
        description="Type of board determining score behavior",
    )
    keep_strategy: KeepStrategy | None = Field(
        default=None,
        description="Strategy for keeping scores (RUN_IDENTITY boards only). "
        "Defaults to BEST for RUN_IDENTITY, ignored for other board types.",
    )
    created_from_template_id: BoardTemplateID | None = Field(
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
    tags: list[str] | None = Field(
        default=None, description="Optional list of tags for categorization"
    )
    description: str | None = Field(
        default=None, description="Optional short description of the board"
    )
    ratio_config: BoardRatioConfigRequest | None = Field(
        default=None,
        description="Ratio config (required when board_type is RATIO)",
    )


class BoardUpdateRequest(BaseModel):
    """Request model for updating a board."""

    name: str | None = Field(default=None, description="Updated board name")
    icon: str | None = Field(default=None, description="Updated icon identifier")
    short_code: str | None = Field(default=None, description="Updated short code")
    unit: str | None = Field(default=None, description="Updated unit of measurement")
    is_active: bool | None = Field(default=None, description="Updated active status")
    is_published: bool | None = Field(default=None, description="Updated published status")
    unique_player_names: bool | None = Field(
        default=None,
        description="Whether player names must be unique on this board (case-insensitive)",
    )
    sort_direction: SortDirection | None = Field(default=None, description="Updated sort direction")
    board_type: BoardType | None = Field(
        default=None,
        description="DEPRECATED: board_type cannot be changed after creation",
        deprecated=True,
    )
    keep_strategy: KeepStrategy | None = Field(default=None, description="Updated keep strategy")
    created_from_template_id: BoardTemplateID | None = Field(
        default=None, description="Updated template ID"
    )
    template_name: str | None = Field(default=None, description="Updated template name")
    starts_at: datetime | None = Field(default=None, description="Updated start time")
    ends_at: datetime | None = Field(default=None, description="Updated end time")
    tags: list[str] | None = Field(default=None, description="Updated tags list")
    description: str | None = Field(default=None, description="Updated board description")
    deleted: bool | None = Field(default=None, description="Set to true to soft delete the board")
    ratio_config: BoardRatioConfigRequest | None = Field(
        default=None,
        description="Updated ratio config (for RATIO boards only)",
    )

    # NOTE: board_type validation happens at route level to allow old clients
    # that always send the current board_type to continue working. Only actual
    # changes to board_type are rejected.


class BoardResponse(BaseModel):
    """Response model for a board."""

    id: BoardID = Field(description="Unique identifier for the board")
    account_id: AccountID = Field(description="ID of the account this board belongs to")
    game_id: GameID = Field(description="ID of the game this board belongs to")
    name: str = Field(description="Name of the board")
    slug: str = Field(description="URL-friendly slug for the board (auto-generated, read-only)")
    icon: str | None = Field(description="Icon identifier for the board, or null")
    short_code: str = Field(description="Globally unique short code for direct sharing")
    unit: str | None = Field(description="Unit of measurement for scores, or null")
    is_active: bool = Field(description="Whether the board is currently active")
    is_published: bool = Field(
        description="Whether the board is published and visible on public web views"
    )
    unique_player_names: bool = Field(
        default=False,
        description="Whether player names must be unique on this board (case-insensitive)",
    )
    sort_direction: SortDirection = Field(description="Direction to sort scores")
    board_type: BoardType = Field(description="Type of board determining score behavior")
    keep_strategy: KeepStrategy = Field(
        description="Strategy for keeping scores (RUN_IDENTITY only)"
    )
    created_from_template_id: BoardTemplateID | None = Field(
        default=None, description="Template ID this board was created from, or null"
    )
    template_name: str | None = Field(
        default=None, description="Template name this board was created from, or null"
    )
    starts_at: datetime | None = Field(
        default=None, description="Start time for time-bounded boards (UTC)"
    )
    ends_at: datetime | None = Field(
        default=None, description="End time for time-bounded boards (UTC)"
    )
    tags: list[str] = Field(default_factory=list, description="List of tags for categorization")
    description: str | None = Field(default=None, description="Short description of the board")
    ratio_config: BoardRatioConfigResponse | None = Field(
        default=None,
        description="Ratio config (present only for RATIO boards)",
    )
    created_at: datetime = Field(description="Timestamp when the board was created (UTC)")
    updated_at: datetime = Field(description="Timestamp of last update (UTC)")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url_short(self) -> str | None:
        """Short URL for direct board access via short_code.

        Returns the URL if BOARDS_UI_DOMAIN is configured and the board is published,
        otherwise None.
        """
        if not settings.BOARDS_UI_DOMAIN or not self.is_published:
            return None
        return f"{settings.BOARDS_UI_DOMAIN}/b/{self.short_code}"

    @classmethod
    def from_domain(
        cls,
        board: Board,
        ratio_config: BoardRatioConfig | None = None,
    ) -> "BoardResponse":
        """Convert domain entity to response model.

        Args:
            board: The domain Board entity to convert.
            ratio_config: Optional ratio config for RATIO boards.

        Returns:
            BoardResponse with all fields populated from the domain entity.
        """
        return cls(
            id=board.id,
            account_id=board.account_id,
            game_id=board.game_id,
            name=board.name,
            slug=board.slug,
            icon=board.icon,
            short_code=board.short_code,
            unit=board.unit,
            is_active=board.is_active,
            is_published=board.is_published,
            unique_player_names=board.unique_player_names,
            sort_direction=board.sort_direction,
            board_type=board.board_type,
            keep_strategy=board.keep_strategy,
            created_from_template_id=board.created_from_template_id,
            template_name=board.template_name,
            starts_at=board.starts_at,
            ends_at=board.ends_at,
            tags=board.tags,
            description=board.description,
            ratio_config=BoardRatioConfigResponse.from_domain(ratio_config)
            if ratio_config
            else None,
            created_at=board.created_at,
            updated_at=board.updated_at,
        )
