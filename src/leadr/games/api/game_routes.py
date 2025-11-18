"""Game API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from leadr.auth.dependencies import (
    AuthContextDep,
    QueryAccountIDDep,
    validate_body_account_id,
)
from leadr.common.api.pagination import PaginatedResponse, PaginationMeta, PaginationParams
from leadr.common.domain.cursor import Cursor, CursorValidationError
from leadr.common.domain.ids import GameID
from leadr.common.domain.pagination import PaginationDirection
from leadr.games.api.game_schemas import (
    GameCreateRequest,
    GameResponse,
    GameUpdateRequest,
)
from leadr.games.services.dependencies import GameServiceDep

router = APIRouter()


@router.post("/games", status_code=status.HTTP_201_CREATED, response_model=GameResponse)
async def create_game(
    request: GameCreateRequest, service: GameServiceDep, auth: AuthContextDep
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
    validate_body_account_id(auth, request.account_id)

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
async def get_game(game_id: GameID, service: GameServiceDep, auth: AuthContextDep) -> GameResponse:
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
    account_id: QueryAccountIDDep,
    service: GameServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
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
        account_id: Account ID (auto-resolved for regular users, required for superadmins).
        service: Injected game service dependency.
        pagination: Pagination parameters (cursor, limit, sort).

    Returns:
        PaginatedResponse with games and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
        403: User does not have access to the specified account.
    """
    try:
        result = await service.list_games(account_id, pagination=pagination)
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Build filter dict for cursors (no active filters for games currently)
    filters_dict = {}

    # Build cursors from result positions
    next_cursor_str = None
    prev_cursor_str = None

    if result.next_position is not None:
        next_cursor = Cursor(
            position=result.next_position,
            sort_fields=pagination.sort_spec,
            filters=filters_dict,
            direction=PaginationDirection.FORWARD,
        )
        next_cursor_str = next_cursor.encode()

    if result.prev_position is not None:
        prev_cursor = Cursor(
            position=result.prev_position,
            sort_fields=pagination.sort_spec,
            filters=filters_dict,
            direction=PaginationDirection.BACKWARD,
        )
        prev_cursor_str = prev_cursor.encode()

    # Convert domain entities to response models
    response_items = [GameResponse.from_domain(game) for game in result.items]

    # Build paginated response
    return PaginatedResponse(
        data=response_items,
        pagination=PaginationMeta(
            next_cursor=next_cursor_str,
            prev_cursor=prev_cursor_str,
            has_next=result.has_next,
            has_prev=result.has_prev,
            count=result.count,
        ),
    )


@router.patch("/games/{game_id}", response_model=GameResponse)
async def update_game(
    game_id: GameID, request: GameUpdateRequest, service: GameServiceDep, auth: AuthContextDep
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
