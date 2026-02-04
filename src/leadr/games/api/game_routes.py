"""Game API routes."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from leadr.auth.dependencies import AdminAuthContextDep
from leadr.common.api.hooks import PostCreateGameHookDep, PreCreateGameHookDep
from leadr.common.api.pagination import PaginatedResponse, PaginationMeta, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, GameID
from leadr.games.api.game_schemas import (
    GameCreateRequest,
    GameResponse,
    GameUpdateRequest,
)
from leadr.games.services.dependencies import GameServiceDep
from leadr.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/games", status_code=status.HTTP_201_CREATED, response_model=GameResponse)
async def create_game(
    request: GameCreateRequest,
    service: GameServiceDep,
    auth: AdminAuthContextDep,
    background_tasks: BackgroundTasks,
    pre_create_hook: PreCreateGameHookDep,
    post_create_hook: PostCreateGameHookDep,
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
        pre_create_hook: Hook called before game creation (for quota checks).
        post_create_hook: Hook called after successful game creation.

    Returns:
        GameResponse with the created game including auto-generated ID and timestamps.

    Raises:
        403: User does not have access to the specified account.
        404: Account not found.
    """
    await pre_create_hook(request, auth, background_tasks)

    try:
        game = await service.create_game(
            account_id=request.account_id,
            name=request.name,
            slug=request.slug,
            steam_app_id=request.steam_app_id,
            default_board_id=request.default_board_id,
            anti_cheat_enabled=request.anti_cheat_enabled,
            description=request.description,
            tags=request.tags,
            page_url=request.page_url,
        )
    except IntegrityError as e:
        logger.warning("IntegrityError creating game", exc_info=e)
        constraint = getattr(e.orig, "constraint_name", None) if e.orig else None
        if constraint == "ix_game_account_name_active":
            raise HTTPException(
                status_code=409,
                detail="A game with this name already exists in this account",
            ) from None
        elif constraint == "uq_game_slug":
            raise HTTPException(
                status_code=409, detail="A game with this slug already exists"
            ) from None
        raise HTTPException(status_code=404, detail="Account not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    await post_create_hook(request, auth, background_tasks)
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
    auth: AdminAuthContextDep,
    service: GameServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: Annotated[AccountID | None, Query(description="Account ID filter")] = None,
    slug: Annotated[str | None, Query(description="Filter by game slug")] = None,
) -> PaginatedResponse[GameResponse]:
    """List all games for an account with pagination and optional filtering.

    Returns paginated games for the specified account. Supports cursor-based
    pagination with bidirectional navigation and custom sorting.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id is optional - if omitted, returns games from all accounts.

    Filtering:
    - Use ?slug={slug} to find a specific game by its globally unique slug

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=name:asc,created_at:desc
    - Valid sort fields: id, name, slug, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/games?slug=my-game
        GET /v1/games?account_id=acc_123&limit=50&sort=name:asc

    Args:
        auth: Authentication context with user info.
        service: Injected game service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account_id query parameter (superadmins can omit to see all).
        slug: Optional slug filter to find a specific game.

    Returns:
        PaginatedResponse with games and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
        403: User does not have access to the specified account.
        404: Game not found when filtering by slug.
    """
    # If slug filter is provided, return that specific game
    if slug is not None:
        game = await service.get_game_by_slug(slug)
        if game is None:
            raise HTTPException(status_code=404, detail=f"Game with slug '{slug}' not found")

        # Check authorization
        if not auth.has_access_to_account(game.account_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this game's account",
            )

        return PaginatedResponse(
            data=[GameResponse.from_domain(game)],
            pagination=PaginationMeta(
                next_cursor=None,
                prev_cursor=None,
                has_next=False,
                has_prev=False,
                count=1,
            ),
        )

    # Superadmin without account_id = None (all accounts)
    # Superadmin with account_id = that specific account
    # Regular user = always their account_id (ignores query param)
    effective_account_id = account_id if auth.is_superadmin else auth.account_id
    try:
        result = await service.list_games(effective_account_id, pagination=pagination)
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

    # Get only fields explicitly provided in request (exclude_unset=True)
    # This allows null values to clear fields vs omitted fields staying unchanged
    update_data = request.model_dump(exclude_unset=True)
    update_data.pop("deleted", None)  # Handled separately above

    if update_data:
        game = await service.update_game(game_id, **update_data)

    return GameResponse.from_domain(game)
