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
from leadr.boards.domain.board import BoardType
from leadr.boards.domain.board_state import BoardState
from leadr.boards.domain.run_entry import RunEntry
from leadr.boards.services.dependencies import BoardServiceDep
from leadr.common.api.hooks import PostCreateScoreHookDep, PreCreateScoreHookDep
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, BoardID, DeviceID, GameID, ScoreID
from leadr.scores.api.score_schemas import (
    IsTestFilter,
    ScoreClientCreateRequest,
    ScoreClientResponse,
    ScoreCreateRequest,
    ScoreResponse,
    ScoreUpdateRequest,
)
from leadr.scores.domain.anti_cheat.enums import FlagAction, ScoreStatus
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
    board_service: BoardServiceDep,
    background_tasks: BackgroundTasks,
    auth: ClientAuthContextWithNonceDep,
    pre_create_hook: PreCreateScoreHookDep,
    post_create_hook: PostCreateScoreHookDep,
) -> ScoreClientResponse:
    """Create a new score (Client API).

    Creates a new score submission for a board. All IDs (account_id, game_id, identity_id)
    are automatically derived from the authenticated session.

    Args:
        score_request: Score creation details including board_id, player_name, and value.
        request: FastAPI request object for accessing geo data.
        service: Injected score service dependency.
        board_service: Injected board service for board lookup.
        background_tasks: FastAPI background tasks for async metadata updates.
        auth: Client authentication context with device and identity info.
        pre_create_hook: Hook called before score creation (for quota checks).
        post_create_hook: Hook called after successful score creation.

    Returns:
        ScoreClientResponse with the created score (excludes device_id).

    Raises:
        404: Board not found.
        400: Validation failed (board doesn't belong to account, or game doesn't
            match board's game).
        403: Score rejected by anti-cheat (rate limit exceeded).
    """
    # Get geo data populated by GeoIP middleware
    timezone = getattr(request.state, "geo_timezone", None)
    country = getattr(request.state, "geo_country", None)
    city = getattr(request.state, "geo_city", None)

    # Identity derived from authenticated session
    identity = auth.identity

    # Update identity display name if provided in request
    if score_request.player_name and identity.display_name != score_request.player_name:
        identity.display_name = score_request.player_name

    await pre_create_hook(score_request, auth, background_tasks)

    # Get board to determine type
    board = await board_service.get_by_id(score_request.board_id)
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")

    # Validate board belongs to the game
    if board.game_id != auth.game_id:
        raise HTTPException(
            status_code=400,
            detail="Board does not belong to this game",
        )

    try:
        # Determine value/delta based on board type
        value: float | None = None
        delta: float | None = None
        if board.board_type == BoardType.COUNTER:
            delta = score_request.value  # Use value as delta for COUNTER boards
        else:
            value = score_request.value

        event, ranking_entry, anti_cheat_result = await service.submit_score(
            board_id=score_request.board_id,
            identity_id=identity.id,
            value=value,
            delta=delta,
            player_name=score_request.player_name,
            timezone=timezone,
            country=country,
            city=city,
            is_test=auth.test_mode,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=404,
            detail="Board not found",
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Handle anti-cheat REJECT
    if anti_cheat_result and anti_cheat_result.action == FlagAction.REJECT:
        raise HTTPException(
            status_code=429,
            detail=anti_cheat_result.reason or "Rate limit exceeded",
        )

    await post_create_hook(score_request, auth, background_tasks)

    # Build response from event and ranking entry
    return _build_score_client_response(
        event=event,
        ranking_entry=ranking_entry,
        identity=identity,
        board_type=board.board_type,
    )


def _build_score_client_response(
    event,
    ranking_entry: BoardState | RunEntry | None,
    identity,
    board_type: BoardType,
) -> ScoreClientResponse:
    """Build ScoreClientResponse from event-sourced data.

    Args:
        event: The ScoreEvent created.
        ranking_entry: BoardState or RunEntry if ranking was updated.
        identity: The submitting identity.
        board_type: The board type for response building.

    Returns:
        ScoreClientResponse with appropriate data.
    """
    if isinstance(ranking_entry, BoardState):
        return ScoreClientResponse.from_board_state(
            state=ranking_entry,
            identity=identity,
            score_event=event,
            rank=0,  # Rank not computed for creation response
        )
    elif isinstance(ranking_entry, RunEntry):
        return ScoreClientResponse.from_run_entry(
            entry=ranking_entry,
            identity=identity,
            score_event=event,
            rank=0,  # Rank not computed for creation response
        )
    else:
        # Fallback for cases with no ranking entry (shouldn't happen for normal flow)
        # This could happen if board type is RATIO or something went wrong
        from leadr.common.domain.ids import ScoreID

        return ScoreClientResponse(
            id=ScoreID(event.id.uuid),  # Mask event ID as score ID
            account_id=event.account_id,
            game_id=event.game_id,
            board_id=event.board_id,
            identity_id=identity.id,
            player_name=identity.display_name or "",
            value=event.event_payload.get("value", event.event_payload.get("delta", 0.0)),
            value_display=None,
            metadata=None,
            rank=None,
            is_placeholder=False,
            is_test=event.is_test,
            status=ScoreStatus.ACTIVE,
            created_at=event.created_at,
            updated_at=event.created_at,  # For new events, updated_at = created_at
        )


@router.get("/scores/{score_id}", response_model=ScoreResponse)
async def get_score(
    score_id: ScoreID,
    service: ScoreServiceDep,
    auth: AdminAuthContextDep,
) -> ScoreResponse:
    """Get a score by ID.

    Returns the score with its computed rank based on the board's sort direction.
    The rank represents the score's position in the leaderboard (1 = first place).

    Args:
        score_id: Score identifier to retrieve.
        service: Injected score service dependency.
        auth: Authentication context with user info.

    Returns:
        ScoreResponse with the score details including rank.

    Raises:
        403: User does not have access to this score's account.
        404: Score not found or soft-deleted.
    """
    score = await service.get_score_with_rank(score_id)

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
    is_test: bool | None = None,
    around_score_id: ScoreID | None = None,
    around_score_value: float | None = None,
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
        is_test: Optional filter for test scores. True returns only test scores,
            False returns only production scores, None returns all scores.
        around_score_id: Optional score ID to center results around.
        around_score_value: Optional score value to center results around (with placeholder).

    Returns:
        PaginatedResponse with scores and appropriate response model based on auth type.

    Raises:
        HTTPException: 400 if cursor is invalid, sort field is invalid,
            or validation fails for around_score_id/around_score_value.
        HTTPException: 404 if around_score_id score not found.
    """
    # Validate around_score_id constraints
    if around_score_id is not None:
        # around_score_id and cursor are mutually exclusive
        if pagination.has_cursor():
            raise HTTPException(
                status_code=400,
                detail="Cannot use both cursor and around_score_id parameters",
            )
        # around_score_id and around_score_value are mutually exclusive
        if around_score_value is not None:
            raise HTTPException(
                status_code=400,
                detail="Cannot use both around_score_id and around_score_value parameters",
            )
        # around_score_id requires board_id
        if board_id is None:
            raise HTTPException(
                status_code=400,
                detail="board_id is required when using around_score_id",
            )

    # Validate around_score_value constraints
    if around_score_value is not None:
        # around_score_value and cursor are mutually exclusive
        if pagination.has_cursor():
            raise HTTPException(
                status_code=400,
                detail="Cannot use both cursor and around_score_value parameters",
            )
        # around_score_value requires board_id
        if board_id is None:
            raise HTTPException(
                status_code=400,
                detail="board_id is required when using around_score_value",
            )

    try:
        result = await service.list_scores(
            account_id=account_id,
            board_id=board_id,
            game_id=game_id,
            device_id=device_id,
            is_test=is_test,
            pagination=pagination,
            around_score_id=around_score_id,
            around_score_value=around_score_value,
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
    if is_test is not None:
        filters_dict["is_test"] = str(is_test)

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
    is_test: Annotated[
        IsTestFilter,
        Query(
            description="Filter for test scores. 'false' (default) returns production only, "
            "'true' returns test only, 'all' returns both test and production"
        ),
    ] = IsTestFilter.FALSE,
    around_score_id: Annotated[
        ScoreID | None, Query(description="Center results around this score ID")
    ] = None,
    around_score_value: Annotated[
        float | None,
        Query(description="Center results around this score value (returns placeholder)"),
    ] = None,
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

    Around Score:
    - Use around_score_id to get scores centered around a specific score
    - Use around_score_value to get scores centered around a hypothetical value
      (returns a placeholder score with is_placeholder=True)
    - Both require board_id to be specified
    - Mutually exclusive with cursor pagination and each other
    - Returns a window of scores with the target in the middle
    - Respects limit (e.g., limit=5 returns 2 above + target + 2 below)

    Example:
        GET /v1/scores?board_id=brd_123&limit=50&sort=value:desc,created_at:asc
        GET /v1/scores?board_id=brd_123&around_score_id=scr_456&limit=11
        GET /v1/scores?board_id=brd_123&around_score_value=1500&limit=11

    Args:
        auth: Authentication context with user info.
        service: Injected score service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account_id query parameter (required for superadmins).
        board_id: Optional board ID to filter by.
        game_id: Optional game ID to filter by.
        device_id: Optional device ID to filter by.
        around_score_id: Optional score ID to center results around.
        around_score_value: Optional value to center results around (with placeholder).

    Returns:
        PaginatedResponse with scores and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, cursor state mismatch, or around validation.
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
        404: around_score_id score not found.
    """
    # Superadmin without account_id = None (all accounts)
    # Superadmin with account_id = that specific account
    # Regular user = always their account_id (ignores query param)
    effective_account_id = account_id if auth.is_superadmin else auth.account_id

    # Convert IsTestFilter enum to bool | None for service layer
    is_test_filter: bool | None = None
    if is_test is IsTestFilter.TRUE:
        is_test_filter = True
    elif is_test is IsTestFilter.FALSE:
        is_test_filter = False
    # IsTestFilter.ALL remains None (no filter)

    return await handle_list_scores(  # type: ignore[return-value]
        auth,
        service,
        pagination,
        effective_account_id,
        board_id,
        game_id,
        device_id,
        is_test_filter,
        around_score_id,
        around_score_value,
    )


@client_router.get("/scores/{score_id}", response_model=ScoreClientResponse)
async def get_score_client(
    score_id: ScoreID,
    service: ScoreServiceDep,
    auth: ClientAuthContextDep,
) -> ScoreClientResponse:
    """Get a score by ID (Client API).

    Returns the score with its computed rank based on the board's sort direction.
    The rank represents the score's position in the leaderboard (1 = first place).

    Clients can only access scores from boards belonging to the same game
    as their authenticated device.

    Args:
        score_id: Score identifier to retrieve.
        service: Injected score service dependency.
        auth: Client authentication context with device info.

    Returns:
        ScoreClientResponse with the score details including rank.

    Raises:
        403: Client does not have access to this score's game.
        404: Score not found or soft-deleted.
    """
    score = await service.get_score_with_rank(score_id)

    # Check client has access to this score's game
    if score.game_id != auth.game_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this score",
        )

    return ScoreClientResponse.from_domain(score)


@client_router.get("/scores")
async def list_scores_client(
    auth: ClientAuthContextDep,
    service: ScoreServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    board_id: BoardID | None = None,
    device_id: DeviceID | None = None,
    around_score_id: Annotated[
        ScoreID | None, Query(description="Center results around this score ID")
    ] = None,
    around_score_value: Annotated[
        float | None,
        Query(description="Center results around this score value (returns placeholder)"),
    ] = None,
) -> PaginatedResponse[ScoreClientResponse]:
    """List scores for an account with optional filters and pagination.

    Returns paginated scores for the specified account, with optional
    filtering by board and/or device. Supports cursor-based pagination
    with bidirectional navigation and custom sorting.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=value:desc,created_at:asc
    - Valid sort fields: id, value, player_name, filter_timezone, filter_country,
      filter_city, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Around Score:
    - Use around_score_id to get scores centered around a specific score
    - Use around_score_value to get scores centered around a hypothetical value
      (returns a placeholder score with is_placeholder=True)
    - Both require board_id to be specified
    - Mutually exclusive with cursor pagination and each other
    - Returns a window of scores with the target in the middle
    - Respects limit (e.g., limit=5 returns 2 above + target + 2 below)

    Example:
        GET /client/scores?board_id=brd_123&limit=50&sort=value:desc,created_at:asc
        GET /client/scores?board_id=brd_123&around_score_id=scr_456&limit=11
        GET /client/scores?board_id=brd_123&around_score_value=1500&limit=11

    Args:
        auth: Authentication context with user info.
        service: Injected score service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        board_id: Optional board ID to filter by.
        device_id: Optional device ID to filter by (e.g., to get "my scores").
        around_score_id: Optional score ID to center results around.
        around_score_value: Optional value to center results around (with placeholder).

    Returns:
        PaginatedResponse with scores and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, cursor state mismatch, or around validation.
        403: User does not have access to the specified account.
        404: around_score_id score not found.
    """
    return await handle_list_scores(  # type: ignore[return-value]
        auth,
        service,
        pagination,
        auth.account_id,
        board_id,
        auth.game_id,
        device_id,
        auth.test_mode,
        around_score_id,
        around_score_value,
    )


@router.patch("/scores/{score_id}", response_model=ScoreResponse, deprecated=True)
async def update_score(
    score_id: ScoreID,
    request: ScoreUpdateRequest,
    service: ScoreServiceDep,
    auth: AdminAuthContextDep,
) -> ScoreResponse:
    """Update a score.

    DEPRECATED: This endpoint is deprecated and will be removed in a future version.
    Scores are now immutable events. Use score flags for moderation instead.

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

    # Get only fields explicitly provided in request (exclude_unset=True)
    # This allows null values to clear fields vs omitted fields staying unchanged
    update_data = request.model_dump(exclude_unset=True)
    update_data.pop("deleted", None)  # Handled separately above

    if update_data:
        score = await service.update_score(score_id, **update_data)

    return ScoreResponse.from_domain(score)
