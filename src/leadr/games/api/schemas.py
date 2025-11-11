"""API request and response models for games."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from leadr.games.domain.game import Game


class GameCreateRequest(BaseModel):
    """Request model for creating a game."""

    account_id: UUID
    name: str
    steam_app_id: str | None = None
    default_board_id: UUID | None = None


class GameUpdateRequest(BaseModel):
    """Request model for updating a game."""

    name: str | None = None
    steam_app_id: str | None = None
    default_board_id: UUID | None = None
    deleted: bool | None = None


class GameResponse(BaseModel):
    """Response model for a game."""

    id: UUID
    account_id: UUID
    name: str
    steam_app_id: str | None
    default_board_id: UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, game: Game) -> "GameResponse":
        """Convert domain entity to response model."""
        return cls(
            id=game.id,
            account_id=game.account_id,
            name=game.name,
            steam_app_id=game.steam_app_id,
            default_board_id=game.default_board_id,
            created_at=game.created_at,
            updated_at=game.updated_at,
        )
