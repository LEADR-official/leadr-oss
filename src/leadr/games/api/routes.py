"""Game API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from leadr.games.api.schemas import (
    GameCreateRequest,
    GameResponse,
    GameUpdateRequest,
)
from leadr.games.services.dependencies import GameServiceDep

router = APIRouter()


@router.post("/games", status_code=status.HTTP_201_CREATED, response_model=GameResponse)
async def create_game(request: GameCreateRequest, service: GameServiceDep) -> GameResponse:
    """Create a new game.

    Raises:
        404: Account not found.
    """
    try:
        game = await service.create_game(
            account_id=request.account_id,
            name=request.name,
            steam_app_id=request.steam_app_id,
            default_board_id=request.default_board_id,
        )
    except IntegrityError:
        raise HTTPException(status_code=404, detail="Account not found") from None

    return GameResponse.from_domain(game)


@router.get("/games/{game_id}", response_model=GameResponse)
async def get_game(game_id: UUID, service: GameServiceDep) -> GameResponse:
    """Get a game by ID."""
    game = await service.get_by_id_or_raise(game_id)
    return GameResponse.from_domain(game)


@router.get("/games", response_model=list[GameResponse])
async def list_games(
    account_id: UUID,
    service: GameServiceDep,
) -> list[GameResponse]:
    """List all games for an account."""
    games = await service.list_games(account_id)
    return [GameResponse.from_domain(game) for game in games]


@router.patch("/games/{game_id}", response_model=GameResponse)
async def update_game(
    game_id: UUID, request: GameUpdateRequest, service: GameServiceDep
) -> GameResponse:
    """Update a game."""
    # Handle soft delete first
    if request.deleted is True:
        game = await service.soft_delete(game_id)
        return GameResponse.from_domain(game)

    # Handle field updates using service method
    game = await service.update_game(
        game_id=game_id,
        name=request.name,
        steam_app_id=request.steam_app_id,
        default_board_id=request.default_board_id,
    )

    return GameResponse.from_domain(game)
