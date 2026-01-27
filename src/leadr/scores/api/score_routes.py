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
from leadr.common.api.pagination import PaginatedResponse, PaginationMeta, PaginationParams
from leadr.common.domain.cursor import Cursor, CursorValidationError, PaginationDirection
from leadr.common.domain.ids import AccountID, BoardID, GameID, IdentityID, ScoreID
from leadr.scores.api.score_schemas import (
    IsTestFilter,
    ScoreClientCreateRequest,
    ScoreClientResponse,
    ScoreResponse,
)
from leadr.scores.domain.anti_cheat.enums import FlagAction, ScoreStatus
from leadr.scores.services.dependencies import ScoreServiceDep
from leadr.scores.services.score_service import ScoreService

router = APIRouter()
client_router = APIRouter()


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
            account_id=event.account_id,
            game_id=event.game_id,
            rank=0,  # Rank not computed for creation response
        )
    elif isinstance(ranking_entry, RunEntry):
        return ScoreClientResponse.from_run_entry(
            entry=ranking_entry,
            account_id=event.account_id,
            game_id=event.game_id,
            rank=0,  # Rank not computed for creation response
        )
    else:
        # Fallback for cases with no ranking entry (shouldn't happen for normal flow)
        # This could happen if board type is RATIO or something went wrong
        return ScoreClientResponse(
            id=ScoreID(event.id.uuid),  # Mask event ID as score ID
            account_id=event.account_id,
            game_id=event.game_id,
            board_id=event.board_id,
            identity_id=IdentityID(identity.id.uuid),
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
    ranking_entry, board, rank = await service.get_score_by_id(score_id)

    # Check authorization
    if not auth.has_access_to_account(board.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this score's account",
        )

    # Build response based on entry type
    if isinstance(ranking_entry, BoardState):
        return ScoreResponse.from_board_state(
            state=ranking_entry,
            account_id=board.account_id,
            game_id=board.game_id,
            rank=rank,
        )
    else:
        return ScoreResponse.from_run_entry(
            entry=ranking_entry,
            account_id=board.account_id,
            game_id=board.game_id,
            rank=rank,
        )


async def handle_list_scores(
    auth: AuthContext,
    service: ScoreService,
    board_service,
    pagination: PaginationParams,
    account_id: AccountID | None,
    board_id: BoardID | None,
    game_id: GameID | None,
    identity_id: IdentityID | None,
    is_test: bool | None = None,
    around_score_id: ScoreID | None = None,
    around_score_value: float | None = None,
) -> PaginatedResponse[ScoreResponse] | PaginatedResponse[ScoreClientResponse]:
    """Handle list scores logic for both admin and client endpoints.

    This shared handler implements the core list scores functionality and returns
    different response models based on the authentication type:
    - Admin auth: Returns ScoreResponse with geo fields
    - Client auth: Returns ScoreClientResponse without geo fields

    Args:
        auth: Authentication context (admin or client).
        service: Score service for data access.
        board_service: Board service for fetching board details.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account ID filter.
        board_id: Optional board ID filter.
        game_id: Optional game ID filter.
        identity_id: Optional identity ID filter.
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

    # board_id is required for list_scores
    if board_id is None:
        raise HTTPException(
            status_code=400,
            detail="board_id is required for listing scores",
        )

    # Get board for account_id/game_id in response building
    board = await board_service.get_by_id(board_id)
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")

    try:
        result = await service.list_scores(
            account_id=account_id,
            board_id=board_id,
            game_id=game_id,
            identity_id=identity_id,
            is_test=is_test,
            pagination=pagination,
            around_score_id=around_score_id,
            around_score_value=around_score_value,
        )
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Build filter dict for cursors
    filters_dict: dict[str, str] = {}
    filters_dict["board_id"] = str(board_id)
    if game_id is not None:
        filters_dict["game_id"] = str(game_id)
    if identity_id is not None:
        filters_dict["identity_id"] = str(identity_id)
    if is_test is not None:
        filters_dict["is_test"] = str(is_test)

    # Convert items to response models with computed ranks
    # Rank is 1-indexed position in the result set
    if auth.auth_type == "admin":
        response_items: list[ScoreResponse] = []
        for idx, item in enumerate(result.items):
            rank = idx + 1  # 1-indexed rank
            if isinstance(item, BoardState):
                response_items.append(
                    ScoreResponse.from_board_state(
                        state=item,
                        account_id=board.account_id,
                        game_id=board.game_id,
                        rank=rank,
                    )
                )
            else:
                response_items.append(
                    ScoreResponse.from_run_entry(
                        entry=item,
                        account_id=board.account_id,
                        game_id=board.game_id,
                        rank=rank,
                    )
                )
        return _build_paginated_response_admin(
            items=response_items,
            result=result,
            pagination=pagination,
            filters=filters_dict,
        )
    else:
        client_response_items: list[ScoreClientResponse] = []
        for idx, item in enumerate(result.items):
            rank = idx + 1  # 1-indexed rank
            if isinstance(item, BoardState):
                client_response_items.append(
                    ScoreClientResponse.from_board_state(
                        state=item,
                        account_id=board.account_id,
                        game_id=board.game_id,
                        rank=rank,
                    )
                )
            else:
                client_response_items.append(
                    ScoreClientResponse.from_run_entry(
                        entry=item,
                        account_id=board.account_id,
                        game_id=board.game_id,
                        rank=rank,
                    )
                )
        return _build_paginated_response_client(
            items=client_response_items,
            result=result,
            pagination=pagination,
            filters=filters_dict,
        )


def _build_paginated_response_admin(
    items: list[ScoreResponse],
    result,
    pagination: PaginationParams,
    filters: dict[str, str],
) -> PaginatedResponse[ScoreResponse]:
    """Build a PaginatedResponse for admin with cursor encoding."""
    next_cursor_str = None
    prev_cursor_str = None

    if result.next_position is not None:
        next_cursor = Cursor(
            position=result.next_position,
            sort_fields=pagination.sort_spec,
            filters=filters,
            direction=PaginationDirection.FORWARD,
        )
        next_cursor_str = next_cursor.encode()

    if result.prev_position is not None:
        prev_cursor = Cursor(
            position=result.prev_position,
            sort_fields=pagination.sort_spec,
            filters=filters,
            direction=PaginationDirection.BACKWARD,
        )
        prev_cursor_str = prev_cursor.encode()

    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(
            next_cursor=next_cursor_str,
            prev_cursor=prev_cursor_str,
            has_next=result.has_next,
            has_prev=result.has_prev,
            count=result.count,
        ),
    )


def _build_paginated_response_client(
    items: list[ScoreClientResponse],
    result,
    pagination: PaginationParams,
    filters: dict[str, str],
) -> PaginatedResponse[ScoreClientResponse]:
    """Build a PaginatedResponse for client with cursor encoding."""
    next_cursor_str = None
    prev_cursor_str = None

    if result.next_position is not None:
        next_cursor = Cursor(
            position=result.next_position,
            sort_fields=pagination.sort_spec,
            filters=filters,
            direction=PaginationDirection.FORWARD,
        )
        next_cursor_str = next_cursor.encode()

    if result.prev_position is not None:
        prev_cursor = Cursor(
            position=result.prev_position,
            sort_fields=pagination.sort_spec,
            filters=filters,
            direction=PaginationDirection.BACKWARD,
        )
        prev_cursor_str = prev_cursor.encode()

    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(
            next_cursor=next_cursor_str,
            prev_cursor=prev_cursor_str,
            has_next=result.has_next,
            has_prev=result.has_prev,
            count=result.count,
        ),
    )


@router.get("/scores")
async def list_scores_admin(
    auth: AdminAuthContextDep,
    service: ScoreServiceDep,
    board_service: BoardServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: Annotated[AccountID | None, Query(description="Account ID filter")] = None,
    board_id: BoardID | None = None,
    game_id: GameID | None = None,
    identity_id: IdentityID | None = None,
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
    filtering by board, game, or identity. Supports cursor-based pagination
    with bidirectional navigation and custom sorting.

    For regular admin users, account_id is automatically derived from their API key.
    For superadmins, account_id must be explicitly provided as a query parameter.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=value:desc,created_at:asc
    - Valid sort fields: id, value, player_name, created_at, updated_at
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
        identity_id: Optional identity ID to filter by.
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
        board_service,
        pagination,
        effective_account_id,
        board_id,
        game_id,
        identity_id,
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
    ranking_entry, board, rank = await service.get_score_by_id(score_id)

    # Check client has access to this score's game
    if board.game_id != auth.game_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this score",
        )

    # Build response based on entry type
    if isinstance(ranking_entry, BoardState):
        return ScoreClientResponse.from_board_state(
            state=ranking_entry,
            account_id=board.account_id,
            game_id=board.game_id,
            rank=rank,
        )
    else:
        return ScoreClientResponse.from_run_entry(
            entry=ranking_entry,
            account_id=board.account_id,
            game_id=board.game_id,
            rank=rank,
        )


@client_router.get("/scores")
async def list_scores_client(
    auth: ClientAuthContextDep,
    service: ScoreServiceDep,
    board_service: BoardServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    board_id: BoardID | None = None,
    identity_id: IdentityID | None = None,
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
    filtering by board and/or identity. Supports cursor-based pagination
    with bidirectional navigation and custom sorting.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=value:desc,created_at:asc
    - Valid sort fields: id, value, player_name, created_at, updated_at
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
        identity_id: Optional identity ID to filter by (e.g., to get "my scores").
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
        board_service,
        pagination,
        auth.account_id,
        board_id,
        auth.game_id,
        identity_id,
        auth.test_mode,
        around_score_id,
        around_score_value,
    )
