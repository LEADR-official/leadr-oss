"""API routes for score management."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError

from leadr.auth.dependencies import (
    AdminAuthContextDep,
    AuthContext,
    ClientAuthContextDep,
    ClientAuthContextWithNonceDep,
)
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, BoardID, DeviceID, GameID, ScoreID
from leadr.scores.api.score_schemas import (
    ScoreClientCreateRequest,
    ScoreClientResponse,
    ScoreCreateRequest,
    ScoreResponse,
    ScoreUpdateRequest,
)
from leadr.scores.services.dependencies import ScoreServiceDep
from leadr.scores.services.score_service import ScoreService

router = APIRouter()
client_router = APIRouter()


@router.post("/scores", status_code=status.HTTP_201_CREATED)
async def create_score_admin(
    score_request: ScoreCreateRequest,
    request: Request,
    service: ScoreServiceDep,
    background_tasks: BackgroundTasks,
    auth: AdminAuthContextDep,
) -> ScoreResponse:
    """Create a new score (Admin API).

    Creates a new score submission for a board. Performs three-level validation:
    board exists, board belongs to the specified account, and game matches
    the board's game.

    For regular admins: account_id is derived from auth, must provide game_id and device_id.
    For superadmins: can provide account_id to create scores for any account.

    Args:
        score_request: Score creation details including board_id, player_name, value,
                      and optionally account_id (superadmin only), game_id, device_id.
        request: FastAPI request object for accessing geo data.
        service: Injected score service dependency.
        background_tasks: FastAPI background tasks for async metadata updates.
        auth: Admin authentication context.

    Returns:
        ScoreResponse with the created score including auto-generated ID and timestamps.

    Raises:
        403: Non-superadmin tries to specify account_id, or access denied.
        400: Missing required fields (game_id or device_id).
        404: Account, game, board, or device not found.
        400: Validation failed (board doesn't belong to account, or game doesn't
            match board's game).
    """
    # Get geo data from request or GeoIP middleware
    timezone = score_request.timezone or getattr(request.state, "geo_timezone", None)
    country = score_request.country or getattr(request.state, "geo_country", None)
    city = score_request.city or getattr(request.state, "geo_city", None)

    try:
        score, _ = await service.create_score(
            account_id=score_request.account_id or auth.account_id,
            game_id=score_request.game_id,
            board_id=score_request.board_id,
            device_id=score_request.device_id,
            player_name=score_request.player_name,
            value=score_request.value,
            value_display=score_request.value_display,
            timezone=timezone,
            country=country,
            city=city,
            metadata=score_request.metadata,
            background_tasks=background_tasks,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=404,
            detail="Account, game, board, or device not found",
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return ScoreResponse.from_domain(score)


@client_router.post("/scores", status_code=status.HTTP_201_CREATED)
async def create_score_client(
    score_request: ScoreClientCreateRequest,
    request: Request,
    service: ScoreServiceDep,
    background_tasks: BackgroundTasks,
    auth: ClientAuthContextWithNonceDep,
) -> ScoreClientResponse:
    """Create a new score (Client API).

    Creates a new score submission for a board. All IDs (account_id, game_id, device_id)
    are automatically derived from the authenticated device session.

    Args:
        score_request: Score creation details including board_id, player_name, and value.
        request: FastAPI request object for accessing geo data.
        service: Injected score service dependency.
        background_tasks: FastAPI background tasks for async metadata updates.
        auth: Client authentication context with device info.

    Returns:
        ScoreClientResponse with the created score (excludes device_id).

    Raises:
        404: Board not found.
        400: Validation failed (board doesn't belong to account, or game doesn't
            match board's game).
    """
    # Get geo data populated by GeoIP middleware
    timezone = getattr(request.state, "geo_timezone", None)
    country = getattr(request.state, "geo_country", None)
    city = getattr(request.state, "geo_city", None)

    # All IDs derived from authenticated device
    account_id = auth.account_id
    game_id = auth.device.game_id
    device_id = auth.device.id

    try:
        score, _ = await service.create_score(
            account_id=account_id,
            game_id=game_id,
            board_id=score_request.board_id,
            device_id=device_id,
            player_name=score_request.player_name,
            value=score_request.value,
            value_display=score_request.value_display,
            timezone=timezone,
            country=country,
            city=city,
            metadata=score_request.metadata,
            background_tasks=background_tasks,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=404,
            detail="Board not found",
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return ScoreClientResponse.from_domain(score)


@router.get("/scores/{score_id}", response_model=ScoreResponse)
async def get_score(
    score_id: ScoreID,
    service: ScoreServiceDep,
    auth: AdminAuthContextDep,
) -> ScoreResponse:
    """Get a score by ID.

    Args:
        score_id: Score identifier to retrieve.
        service: Injected score service dependency.
        auth: Authentication context with user info.

    Returns:
        ScoreResponse with the score details.

    Raises:
        403: User does not have access to this score's account.
        404: Score not found or soft-deleted.
    """
    score = await service.get_by_id_or_raise(score_id)

    # Check authorization
    if not auth.has_access_to_account(score.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this score's account",
        )

    return ScoreResponse.from_domain(score)


async def handle_list_scores(
    auth: AuthContext,
    service: ScoreService,
    pagination: PaginationParams,
    account_id: AccountID | None,
    board_id: BoardID | None,
    game_id: GameID | None,
    device_id: DeviceID | None,
) -> PaginatedResponse[ScoreResponse] | PaginatedResponse[ScoreClientResponse]:
    """Handle list scores logic for both admin and client endpoints.

    This shared handler implements the core list scores functionality and returns
    different response models based on the authentication type:
    - Admin auth: Returns ScoreResponse with device_id and geo fields
    - Client auth: Returns ScoreClientResponse without device_id and geo fields

    Args:
        auth: Authentication context (admin or client).
        service: Score service for data access.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account ID filter.
        board_id: Optional board ID filter.
        game_id: Optional game ID filter.
        device_id: Optional device ID filter.

    Returns:
        PaginatedResponse with scores and appropriate response model based on auth type.

    Raises:
        HTTPException: 400 if cursor is invalid or sort field is invalid.
    """
    try:
        result = await service.list_scores(
            account_id=account_id,
            board_id=board_id,
            game_id=game_id,
            device_id=device_id,
            pagination=pagination,
        )
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Since we always pass pagination, result is always PaginatedResult (via overload)
    # Build filter dict for cursors
    filters_dict = {}
    if board_id is not None:
        filters_dict["board_id"] = str(board_id)
    if game_id is not None:
        filters_dict["game_id"] = str(game_id)
    if device_id is not None:
        filters_dict["device_id"] = str(device_id)

    if auth.auth_type == "admin":
        return PaginatedResponse.from_paginated_result(
            result=result,
            pagination=pagination,
            filters=filters_dict,
            response_model=ScoreResponse,
        )
    else:
        return PaginatedResponse.from_paginated_result(
            result=result,
            pagination=pagination,
            filters=filters_dict,
            response_model=ScoreClientResponse,
        )


@router.get("/scores")
async def list_scores_admin(
    auth: AdminAuthContextDep,
    service: ScoreServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: Annotated[AccountID | None, Query(description="Account ID filter")] = None,
    board_id: BoardID | None = None,
    game_id: GameID | None = None,
    device_id: DeviceID | None = None,
) -> PaginatedResponse[ScoreResponse]:
    """List scores for an account with optional filters and pagination.

    Returns paginated scores for the specified account, with optional
    filtering by board, game, or device. Supports cursor-based pagination
    with bidirectional navigation and custom sorting.

    For regular admin users, account_id is automatically derived from their API key.
    For superadmins, account_id must be explicitly provided as a query parameter.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=value:desc,created_at:asc
    - Valid sort fields: id, value, player_name, filter_timezone, filter_country,
      filter_city, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/scores?board_id=brd_123&limit=50&sort=value:desc,created_at:asc

    Args:
        auth: Authentication context with user info.
        service: Injected score service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account_id query parameter (required for superadmins).
        board_id: Optional board ID to filter by.
        game_id: Optional game ID to filter by.
        device_id: Optional device ID to filter by.

    Returns:
        PaginatedResponse with scores and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
    """
    # Superadmin without account_id = None (all accounts)
    # Superadmin with account_id = that specific account
    # Regular user = always their account_id (ignores query param)
    effective_account_id = account_id if auth.is_superadmin else auth.account_id
    return await handle_list_scores(  # type: ignore[return-value]
        auth, service, pagination, effective_account_id, board_id, game_id, device_id
    )


@client_router.get("/scores")
async def list_scores_client(
    auth: ClientAuthContextDep,
    service: ScoreServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    board_id: BoardID | None = None,
) -> PaginatedResponse[ScoreClientResponse]:
    """List scores for an account with optional filters and pagination.

    Returns paginated scores for the specified account, with optional
    filtering by board. Supports cursor-based pagination
    with bidirectional navigation and custom sorting.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=value:desc,created_at:asc
    - Valid sort fields: id, value, player_name, filter_timezone, filter_country,
      filter_city, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/scores?board_id=brd_123&limit=50&sort=value:desc,created_at:asc

    Args:
        auth: Authentication context with user info.
        service: Injected score service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        board_id: Optional board ID to filter by.

    Returns:
        PaginatedResponse with scores and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
    """
    return await handle_list_scores(  # type: ignore[return-value]
        auth,
        service,
        pagination,
        auth.account_id,
        board_id,
        auth.device.game_id,
        auth.device.id,
    )


@router.patch("/scores/{score_id}", response_model=ScoreResponse)
async def update_score(
    score_id: ScoreID,
    request: ScoreUpdateRequest,
    service: ScoreServiceDep,
    auth: AdminAuthContextDep,
) -> ScoreResponse:
    """Update a score.

    Supports partial updates of score fields. Any field not provided will
    remain unchanged. Set deleted: true to soft delete the score.

    Args:
        score_id: Score identifier to update.
        request: Score update details with optional fields to modify.
        service: Injected score service dependency.
        auth: Authentication context with user info.

    Returns:
        ScoreResponse with the updated score details.

    Raises:
        403: User does not have access to this score's account.
        404: Score not found or already soft-deleted.
    """
    # Fetch score to check authorization
    score = await service.get_by_id_or_raise(score_id)

    # Check authorization
    if not auth.has_access_to_account(score.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this score's account",
        )

    # Handle soft delete
    if request.deleted is True:
        score = await service.soft_delete(score_id)
        return ScoreResponse.from_domain(score)

    # Update other fields
    score = await service.update_score(
        score_id=score_id,
        player_name=request.player_name,
        value=request.value,
        value_display=request.value_display,
        timezone=request.timezone,
        country=request.country,
        city=request.city,
        metadata=request.metadata,
    )
    return ScoreResponse.from_domain(score)
