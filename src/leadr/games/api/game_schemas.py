"""API request and response models for games."""

from datetime import datetime

from pydantic import BaseModel, Field

from leadr.common.domain.ids import AccountID, BoardID, GameID
from leadr.games.domain.game import Game


class GameCreateRequest(BaseModel):
    """Request model for creating a game."""

    account_id: AccountID = Field(description="ID of the account this game belongs to")
    name: str = Field(description="Name of the game")
    slug: str | None = Field(
        default=None,
        description=(
            "Optional URL-friendly slug (globally unique). "
            "If not provided, will be auto-generated from name"
        ),
    )
    steam_app_id: str | None = Field(
        default=None, description="Optional Steam App ID for Steam integration"
    )
    default_board_id: BoardID | None = Field(
        default=None, description="Optional ID of the default leaderboard for this game"
    )
    anti_cheat_enabled: bool = Field(
        default=True, description="Whether anti-cheat is enabled for this game (defaults to True)"
    )
    description: str | None = Field(default=None, description="Optional game description")
    tags: list[str] | None = Field(
        default=None, description="Optional list of tags for categorization"
    )
    page_url: str | None = Field(default=None, description="Optional URL to the game's page")


class GameUpdateRequest(BaseModel):
    """Request model for updating a game."""

    name: str | None = Field(default=None, description="Updated game name")
    steam_app_id: str | None = Field(default=None, description="Updated Steam App ID")
    default_board_id: BoardID | None = Field(
        default=None, description="Updated default leaderboard ID"
    )
    anti_cheat_enabled: bool | None = Field(
        default=None, description="Whether anti-cheat is enabled for this game"
    )
    description: str | None = Field(default=None, description="Updated game description")
    tags: list[str] | None = Field(default=None, description="Updated tags list")
    page_url: str | None = Field(default=None, description="Updated page URL")
    deleted: bool | None = Field(default=None, description="Set to true to soft delete the game")


class GameResponse(BaseModel):
    """Response model for a game."""

    id: GameID = Field(description="Unique identifier for the game")
    account_id: AccountID = Field(description="ID of the account this game belongs to")
    name: str = Field(description="Name of the game")
    slug: str = Field(description="URL-friendly slug for the game (globally unique, immutable)")
    steam_app_id: str | None = Field(
        default=None, description="Steam App ID if Steam integration is configured"
    )
    default_board_id: BoardID | None = Field(
        default=None, description="ID of the default leaderboard, or null if not set"
    )
    anti_cheat_enabled: bool = Field(description="Whether anti-cheat is enabled for this game")
    description: str | None = Field(default=None, description="Game description")
    tags: list[str] = Field(default_factory=list, description="List of tags for categorization")
    page_url: str | None = Field(default=None, description="URL to the game's page")
    created_at: datetime = Field(description="Timestamp when the game was created (UTC)")
    updated_at: datetime = Field(description="Timestamp of last update (UTC)")

    @classmethod
    def from_domain(cls, game: Game) -> "GameResponse":
        """Convert domain entity to response model.

        Args:
            game: The domain Game entity to convert.

        Returns:
            GameResponse with all fields populated from the domain entity.
        """
        return cls(
            id=game.id,
            account_id=game.account_id,
            name=game.name,
            slug=game.slug,
            steam_app_id=game.steam_app_id,
            default_board_id=game.default_board_id,
            anti_cheat_enabled=game.anti_cheat_enabled,
            description=game.description,
            tags=game.tags,
            page_url=game.page_url,
            created_at=game.created_at,
            updated_at=game.updated_at,
        )
