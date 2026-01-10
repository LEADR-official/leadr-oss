"""Board API routes."""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from leadr.auth.dependencies import (
    AdminAuthContextDep,
    AuthContext,
    ClientAuthContextDep,
)
from leadr.boards.api.board_schemas import (
    BoardCreateRequest,
    BoardResponse,
    BoardUpdateRequest,
)
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.dependencies import BoardServiceDep
from leadr.common.api.hooks import PostCreateBoardHookDep, PreCreateBoardHookDep
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, BoardID, GameID
from leadr.games.services.dependencies import GameServiceDep
from leadr.games.services.game_service import GameService

logger = logging.getLogger(__name__)

router = APIRouter()
client_router = APIRouter()


@router.post("/boards", status_code=status.HTTP_201_CREATED, response_model=BoardResponse)
async def create_board(
    request: BoardCreateRequest,
    service: BoardServiceDep,
    auth: AdminAuthContextDep,
    pre_create_hook: PreCreateBoardHookDep,
    post_create_hook: PostCreateBoardHookDep,
) -> BoardResponse:
    """Create a new board.

    Creates a new leaderboard associated with an existing game and account.
    The game must belong to the specified account.

    For regular users, account_id must match their API key's account.
    For superadmins, any account_id is accepted.

    Args:
        request: Board creation details including account_id, game_id, name, and settings.
        service: Injected board service dependency.
        auth: Authentication context with user info.
        pre_create_hook: Hook called before board creation (for quota checks).
        post_create_hook: Hook called after successful board creation.

    Returns:
        BoardResponse with the created board including auto-generated ID and timestamps.

    Raises:
        403: User does not have access to the specified account.
        404: Game or account not found.
        400: Game doesn't belong to the specified account.
    """
    await pre_create_hook(request.account_id, request.game_id, auth)

    try:
        board = await service.create_board(
            account_id=request.account_id,
            game_id=request.game_id,
            name=request.name,
            slug=request.slug,
            icon=request.icon,
            short_code=request.short_code,
            unit=request.unit,
            is_active=request.is_active,
            is_published=request.is_published,
            sort_direction=request.sort_direction,
            keep_strategy=request.keep_strategy,
            created_from_template_id=request.created_from_template_id,
            template_name=request.template_name,
            starts_at=request.starts_at,
            ends_at=request.ends_at,
            tags=request.tags,
            description=request.description,
        )
    except IntegrityError as e:
        logger.exception(e)
        raise HTTPException(status_code=404, detail="Game or account not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    await post_create_hook(request.account_id, request.game_id, auth)
    return BoardResponse.from_domain(board)


@router.get("/boards/{board_id}", response_model=BoardResponse)
async def get_board(
    board_id: BoardID, service: BoardServiceDep, auth: AdminAuthContextDep
) -> BoardResponse:
    """Get a board by ID.

    Args:
        board_id: Unique identifier for the board.
        service: Injected board service dependency.
        auth: Authentication context with user info.

    Returns:
        BoardResponse with full board details.

    Raises:
        403: User does not have access to this board's account.
        404: Board not found.
    """
    board = await service.get_by_id_or_raise(board_id)

    # Check authorization
    if not auth.has_access_to_account(board.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this board's account",
        )

    return BoardResponse.from_domain(board)


async def handle_list_boards(
    auth: AuthContext,
    service: BoardService,
    game_service: GameService,
    pagination: PaginationParams,
    account_id: AccountID | None,
    game_id: GameID | None,
    code: str | None,
    game_slug: str | None,
    slug: str | None,
    is_active: bool | None,
    is_published: bool | None,
    starts_before: datetime | None,
    starts_after: datetime | None,
    ends_before: datetime | None,
    ends_after: datetime | None,
) -> PaginatedResponse[BoardResponse]:
    """Shared handler for listing boards with filtering.

    Args:
        auth: Authentication context with user info.
        service: Board service instance.
        game_service: Game service instance for game_slug resolution.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account ID to filter boards by.
        game_id: Optional game ID to filter boards by.
        code: Optional short code to filter boards by.
        game_slug: Optional game slug to filter boards by game (resolves to game_id).
        slug: Optional board slug to filter by specific board (requires game_slug).
        is_active: Optional filter for active status.
        is_published: Optional filter for published status.
        starts_before: Optional filter for boards starting before this time.
        starts_after: Optional filter for boards starting after this time.
        ends_before: Optional filter for boards ending before this time.
        ends_after: Optional filter for boards ending after this time.

    Returns:
        PaginatedResponse with boards and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
        404: Game or board not found when using slug filters.
    """
    # Handle game_slug filter - resolve to game_id
    if game_slug is not None:
        game = await game_service.get_game_by_slug(game_slug)
        if game is None:
            raise HTTPException(status_code=404, detail=f"Game with slug '{game_slug}' not found")

        # Check authorization
        if not auth.has_access_to_account(game.account_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this game's account",
            )

        game_id = game.id
        account_id = game.account_id  # Use game's account for filtering

    # Validate that game_id is required when filtering by slug
    if slug is not None and game_id is None:
        raise HTTPException(
            status_code=400,
            detail="game_slug parameter is required when filtering by board slug",
        )

    # Unified query path for all filter combinations
    try:
        result = await service.list_boards(
            account_id=account_id,
            game_id=game_id,
            code=code,
            slug=slug,
            is_active=is_active,
            is_published=is_published,
            starts_before=starts_before,
            starts_after=starts_after,
            ends_before=ends_before,
            ends_after=ends_after,
            pagination=pagination,
        )
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Build filter dict for cursor encoding
    filters_dict: dict[str, str] = {}
    if account_id is not None:
        filters_dict["account_id"] = str(account_id)
    if game_id is not None:
        filters_dict["game_id"] = str(game_id)
    if code is not None:
        filters_dict["code"] = code
    if slug is not None:
        filters_dict["slug"] = slug
    if is_active is not None:
        filters_dict["is_active"] = str(is_active)
    if is_published is not None:
        filters_dict["is_published"] = str(is_published)
    if starts_before is not None:
        filters_dict["starts_before"] = starts_before.isoformat()
    if starts_after is not None:
        filters_dict["starts_after"] = starts_after.isoformat()
    if ends_before is not None:
        filters_dict["ends_before"] = ends_before.isoformat()
    if ends_after is not None:
        filters_dict["ends_after"] = ends_after.isoformat()

    return PaginatedResponse.from_paginated_result(
        result=result,
        pagination=pagination,
        filters=filters_dict,
        response_model=BoardResponse,
    )


@router.get("/boards", response_model=PaginatedResponse[BoardResponse])
async def list_boards_admin(
    auth: AdminAuthContextDep,
    service: BoardServiceDep,
    game_service: GameServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: Annotated[AccountID | None, Query(description="Filter by account ID")] = None,
    game_id: Annotated[GameID | None, Query(description="Filter by game ID")] = None,
    code: Annotated[str | None, Query(description="Filter by short code")] = None,
    game_slug: Annotated[str | None, Query(description="Filter by game slug")] = None,
    slug: Annotated[
        str | None, Query(description="Filter by board slug (requires game_slug)")
    ] = None,
    is_active: Annotated[bool | None, Query(description="Filter by active status")] = None,
    is_published: Annotated[bool | None, Query(description="Filter by published status")] = None,
    starts_before: Annotated[
        datetime | None, Query(description="Filter boards starting before this time (ISO 8601)")
    ] = None,
    starts_after: Annotated[
        datetime | None, Query(description="Filter boards starting after this time (ISO 8601)")
    ] = None,
    ends_before: Annotated[
        datetime | None, Query(description="Filter boards ending before this time (ISO 8601)")
    ] = None,
    ends_after: Annotated[
        datetime | None, Query(description="Filter boards ending after this time (ISO 8601)")
    ] = None,
) -> PaginatedResponse[BoardResponse]:
    """List boards (Admin API).

    For regular users:
    - If account_id not provided, defaults to their API key's account
    - If account_id provided and they are superadmin, can access any account
    - If account_id provided and NOT superadmin, must match their account (validated in AuthContext)

    Filtering:
    - Use ?game_id={id} or ?game_slug={slug} to filter boards by game
    - Use ?game_slug={game_slug}&slug={slug} to find a specific board within a game
    - Use ?code={code} to filter boards by short code
    - Use ?is_active=true/false to filter by active status
    - Use ?is_published=true/false to filter by published status
    - Use ?starts_before=<datetime>&starts_after=<datetime> for start date range
    - Use ?ends_before=<datetime>&ends_after=<datetime> for end date range
    - Note: board slug filter requires game_slug parameter

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=name:asc,created_at:desc
    - Valid sort fields: id, name, slug, short_code, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/boards?account_id=acc_123&limit=50&sort=name:asc
        GET /v1/boards?game_slug=my-game&is_active=true
        GET /v1/boards?game_slug=my-game&slug=weekly-challenge
        GET /v1/boards?starts_after=2025-01-01T00:00:00Z&ends_before=2025-12-31T23:59:59Z

    Args:
        auth: Admin authentication context with user info.
        service: Injected board service dependency.
        game_service: Injected game service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account ID to filter boards by.
        game_id: Optional game ID to filter boards by.
        code: Optional short code to filter boards by.
        game_slug: Optional game slug to filter boards by game (resolves to game_id).
        slug: Optional board slug to filter by specific board (requires game_slug).
        is_active: Optional filter for active status.
        is_published: Optional filter for published status.
        starts_before: Optional filter for boards starting before this time.
        starts_after: Optional filter for boards starting after this time.
        ends_before: Optional filter for boards ending before this time.
        ends_after: Optional filter for boards ending after this time.

    Returns:
        PaginatedResponse with boards and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, cursor state mismatch, or slug without game_slug.
        404: Game or board not found when using slug filters.
    """
    # Superadmin without account_id = None (all accounts)
    # Superadmin with account_id = that specific account
    # Regular user = always their account_id (ignores query param)
    effective_account_id = account_id if auth.is_superadmin else auth.account_id
    return await handle_list_boards(
        auth=auth,
        service=service,
        game_service=game_service,
        pagination=pagination,
        account_id=effective_account_id,
        game_id=game_id,
        code=code,
        game_slug=game_slug,
        slug=slug,
        is_active=is_active,
        is_published=is_published,
        starts_before=starts_before,
        starts_after=starts_after,
        ends_before=ends_before,
        ends_after=ends_after,
    )


@client_router.get("/boards", response_model=PaginatedResponse[BoardResponse])
async def list_boards_client(
    auth: ClientAuthContextDep,
    service: BoardServiceDep,
    game_service: GameServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    game_id: Annotated[GameID | None, Query(description="Filter by game ID")] = None,
    code: Annotated[str | None, Query(description="Filter by short code")] = None,
    game_slug: Annotated[str | None, Query(description="Filter by game slug")] = None,
    slug: Annotated[
        str | None, Query(description="Filter by board slug (requires game_slug)")
    ] = None,
    is_published: Annotated[bool | None, Query(description="Filter by published status")] = None,
    starts_before: Annotated[
        datetime | None, Query(description="Filter boards starting before this time (ISO 8601)")
    ] = None,
    starts_after: Annotated[
        datetime | None, Query(description="Filter boards starting after this time (ISO 8601)")
    ] = None,
    ends_before: Annotated[
        datetime | None, Query(description="Filter boards ending before this time (ISO 8601)")
    ] = None,
    ends_after: Annotated[
        datetime | None, Query(description="Filter boards ending after this time (ISO 8601)")
    ] = None,
) -> PaginatedResponse[BoardResponse]:
    """List boards (Client API).

    Account ID is automatically derived from the authenticated device's account.
    Clients can optionally filter by various criteria to find specific boards.

    Filtering:
    - Use ?game_id={id} or ?game_slug={slug} to filter boards by game
    - Use ?game_slug={game_slug}&slug={slug} to find a specific board within a game
    - Use ?code={code} to filter boards by short code
    - Use ?is_published=true/false to filter by published status
    - Use ?starts_before=<datetime>&starts_after=<datetime> for start date range
    - Use ?ends_before=<datetime>&ends_after=<datetime> for end date range
    - Note: board slug filter requires game_slug parameter

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=name:asc,created_at:desc
    - Valid sort fields: id, name, slug, short_code, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/client/boards?code=WEEKLY-CHALLENGE&limit=50
        GET /v1/client/boards?game_slug=my-game&is_published=true
        GET /v1/client/boards?game_slug=my-game&slug=weekly-challenge
        GET /v1/client/boards?starts_after=2025-01-01T00:00:00Z

    Args:
        auth: Client authentication context with device info.
        service: Injected board service dependency.
        game_service: Injected game service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        game_id: Optional game ID to filter boards by.
        code: Optional short code to filter boards by.
        game_slug: Optional game slug to filter boards by game (resolves to game_id).
        slug: Optional board slug to filter by specific board (requires game_slug).
        is_published: Optional filter for published status.
        starts_before: Optional filter for boards starting before this time.
        starts_after: Optional filter for boards starting after this time.
        ends_before: Optional filter for boards ending before this time.
        ends_after: Optional filter for boards ending after this time.

    Returns:
        PaginatedResponse with boards and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, cursor state mismatch, or slug without game_slug.
        404: Game or board not found when using slug filters.
    """
    return await handle_list_boards(
        auth=auth,
        service=service,
        game_service=game_service,
        pagination=pagination,
        account_id=auth.account_id,
        game_id=game_id,
        code=code,
        game_slug=game_slug,
        slug=slug,
        is_active=True,  # Clients can't access inactive boards
        is_published=is_published,
        starts_before=starts_before,
        starts_after=starts_after,
        ends_before=ends_before,
        ends_after=ends_after,
    )


@router.patch("/boards/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: BoardID,
    request: BoardUpdateRequest,
    service: BoardServiceDep,
    auth: AdminAuthContextDep,
) -> BoardResponse:
    """Update a board.

    Supports updating any board field or soft-deleting the board.

    Args:
        board_id: Unique identifier for the board.
        request: Board update details (all fields optional).
        service: Injected board service dependency.
        auth: Authentication context with user info.

    Returns:
        BoardResponse with the updated board details.

    Raises:
        403: User does not have access to this board's account.
        404: Board not found.
    """
    # Fetch board to check authorization
    board = await service.get_by_id_or_raise(board_id)

    # Check authorization
    if not auth.has_access_to_account(board.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this board's account",
        )

    # Handle soft delete first
    if request.deleted is True:
        board = await service.soft_delete(board_id)
        return BoardResponse.from_domain(board)

    # Handle field updates using service method
    board = await service.update_board(
        board_id=board_id,
        name=request.name,
        icon=request.icon,
        short_code=request.short_code,
        unit=request.unit,
        is_active=request.is_active,
        is_published=request.is_published,
        sort_direction=request.sort_direction,
        keep_strategy=request.keep_strategy,
        created_from_template_id=request.created_from_template_id,
        template_name=request.template_name,
        starts_at=request.starts_at,
        ends_at=request.ends_at,
        tags=request.tags,
        description=request.description,
    )

    return BoardResponse.from_domain(board)
