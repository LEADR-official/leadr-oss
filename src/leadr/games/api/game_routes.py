"""Game API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from leadr.auth.dependencies import AdminAuthContextDep, AdminAuthContextWithAccountIDDep
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, GameID
from leadr.games.api.game_schemas import (
    GameCreateRequest,
    GameResponse,
    GameUpdateRequest,
)
from leadr.games.services.dependencies import GameServiceDep

router = APIRouter()


@router.post("/games", status_code=status.HTTP_201_CREATED, response_model=GameResponse)
async def create_game(
    request: GameCreateRequest, service: GameServiceDep, auth: AdminAuthContextDep
) -> GameResponse:
    """Create a new game.

    Creates a new game associated with an existing account. Games can optionally
    be configured with Steam integration and a default leaderboard.

    For regular users, account_id must match their API key's account.
    For superadmins, any account_id is accepted.

    Args:
        request: Game creation details including account_id, name, and optional settings.
        service: Injected game service dependency.
        auth: Authentication context with user info.

    Returns:
        GameResponse with the created game including auto-generated ID and timestamps.

    Raises:
        403: User does not have access to the specified account.
        404: Account not found.
    """
    try:
        game = await service.create_game(
            account_id=request.account_id,
            name=request.name,
            steam_app_id=request.steam_app_id,
            default_board_id=request.default_board_id,
            anti_cheat_enabled=request.anti_cheat_enabled,
        )
    except IntegrityError:
        raise HTTPException(status_code=404, detail="Account not found") from None

    return GameResponse.from_domain(game)


@router.get("/games/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: GameID, service: GameServiceDep, auth: AdminAuthContextDep
) -> GameResponse:
    """Get a game by ID.

    Args:
        game_id: Unique identifier for the game.
        service: Injected game service dependency.
        auth: Authentication context with user info.

    Returns:
        GameResponse with full game details.

    Raises:
        403: User does not have access to this game's account.
        404: Game not found.
    """
    game = await service.get_by_id_or_raise(game_id)

    # Check authorization
    if not auth.has_access_to_account(game.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this game's account",
        )

    return GameResponse.from_domain(game)


@router.get("/games", response_model=PaginatedResponse[GameResponse])
async def list_games(
    auth: AdminAuthContextWithAccountIDDep,
    service: GameServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: Annotated[AccountID | None, Query(description="Account ID filter")] = None,
) -> PaginatedResponse[GameResponse]:
    """List all games for an account with pagination.

    Returns paginated games for the specified account. Supports cursor-based
    pagination with bidirectional navigation and custom sorting.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id must be explicitly provided as a query parameter.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=name:asc,created_at:desc
    - Valid sort fields: id, name, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/games?account_id=acc_123&limit=50&sort=name:asc

    Args:
        auth: Authentication context with user info.
        service: Injected game service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account_id query parameter (required for superadmins).

    Returns:
        PaginatedResponse with games and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
    """
    try:
        result = await service.list_games(account_id or auth.account_id, pagination=pagination)
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return PaginatedResponse.from_paginated_result(
        result=result,
        pagination=pagination,
        filters={},
        response_model=GameResponse,
    )


@router.patch("/games/{game_id}", response_model=GameResponse)
async def update_game(
    game_id: GameID, request: GameUpdateRequest, service: GameServiceDep, auth: AdminAuthContextDep
) -> GameResponse:
    """Update a game.

    Supports updating name, Steam App ID, default board ID, or soft-deleting the game.

    Args:
        game_id: Unique identifier for the game.
        request: Game update details (all fields optional).
        service: Injected game service dependency.
        auth: Authentication context with user info.

    Returns:
        GameResponse with the updated game details.

    Raises:
        403: User does not have access to this game's account.
        404: Game not found.
    """
    # Fetch game to check authorization
    game = await service.get_by_id_or_raise(game_id)

    # Check authorization
    if not auth.has_access_to_account(game.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this game's account",
        )

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
        anti_cheat_enabled=request.anti_cheat_enabled,
    )

    return GameResponse.from_domain(game)
