"""API routes for score event management (admin only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from leadr.auth.dependencies import AdminAuthContextDep
from leadr.boards.domain.board import BoardType
from leadr.boards.services.dependencies import BoardServiceDep
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, BoardID, IdentityID, ScoreEventID
from leadr.scores.api.score_event_schemas import ScoreEventCreateRequest, ScoreEventResponse
from leadr.scores.services.dependencies import ScoreEventServiceDep, ScoreServiceDep

router = APIRouter()


@router.post("/score-events", status_code=status.HTTP_201_CREATED)
async def create_score_event(
    request: ScoreEventCreateRequest,
    auth: AdminAuthContextDep,
    score_service: ScoreServiceDep,
    board_service: BoardServiceDep,
) -> ScoreEventResponse:
    """Create a score event (Admin API).

    Creates a score event using the same processing as client submissions:
    - Runs anti-cheat checks
    - Updates rankings (BoardState/RunEntry)
    - Validates board type and payload

    This endpoint is for admin testing, data seeding, and demo purposes.

    Args:
        request: Score event creation request
        auth: Admin authentication context
        score_service: Score service for submission
        board_service: Board service for validation

    Returns:
        Created score event

    Raises:
        404: Board not found
        403: Non-superadmin accessing another account's board
        400: Validation error (wrong board type, etc.)
    """
    # Get board and validate access
    board = await board_service.get_board(request.board_id)
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")

    if not auth.is_superadmin and board.account_id != auth.account_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Determine value/delta based on board type
    value: float | None = None
    delta: float | None = None
    if board.board_type == BoardType.COUNTER:
        delta = request.value
    else:
        value = request.value

    try:
        event, _ranking_entry, _anti_cheat_result = await score_service.submit_score(
            board_id=request.board_id,
            identity_id=request.identity_id,
            value=value,
            delta=delta,
            player_name=request.player_name,
            timezone=request.timezone,
            country=request.country,
            city=request.city,
            is_test=request.is_test,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Board or identity not found"
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None

    return ScoreEventResponse.from_domain(event)


@router.get("/score-events")
async def list_score_events(
    auth: AdminAuthContextDep,
    service: ScoreEventServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: Annotated[AccountID | None, Query(description="Filter by account ID")] = None,
    board_id: Annotated[BoardID | None, Query(description="Filter by board ID")] = None,
    identity_id: Annotated[IdentityID | None, Query(description="Filter by identity ID")] = None,
    is_test: Annotated[bool | None, Query(description="Filter by test mode")] = None,
) -> PaginatedResponse[ScoreEventResponse]:
    """List score events (Admin API).

    Returns a paginated list of score events. Score events are immutable
    facts about score submissions and cannot be updated or deleted.

    For regular admins: account_id defaults to their account.
    For superadmins: can view events across all accounts.

    Args:
        auth: Admin authentication context.
        service: Injected score event service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional filter by account ID.
        board_id: Optional filter by board ID.
        identity_id: Optional filter by identity ID.
        is_test: Optional filter for test events.

    Returns:
        Paginated list of score events.

    Raises:
        400: Invalid pagination cursor.
    """
    # Non-superadmins can only view their own account's events
    effective_account_id = account_id if auth.is_superadmin else auth.account_id

    try:
        result = await service.list_score_events(
            account_id=effective_account_id,
            board_id=board_id,
            identity_id=identity_id,
            is_test=is_test,
            limit=pagination.limit,
        )
    except CursorValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    filters: dict[str, str] = {}
    if effective_account_id:
        filters["account_id"] = str(effective_account_id)
    if board_id:
        filters["board_id"] = str(board_id)
    if identity_id:
        filters["identity_id"] = str(identity_id)
    if is_test is not None:
        filters["is_test"] = str(is_test).lower()

    return PaginatedResponse.from_paginated_result(
        result=result,
        pagination=pagination,
        filters=filters,
        response_model=ScoreEventResponse,
    )


@router.get("/score-events/{event_id}")
async def get_score_event(
    event_id: ScoreEventID,
    auth: AdminAuthContextDep,
    service: ScoreEventServiceDep,
) -> ScoreEventResponse:
    """Get a single score event by ID (Admin API).

    Args:
        event_id: Score event ID.
        auth: Admin authentication context.
        service: Injected score event service dependency.

    Returns:
        Score event details.

    Raises:
        404: Score event not found.
        403: Non-superadmin trying to access another account's event.
    """
    event = await service.get_score_event(event_id)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Score event not found",
        )

    # Non-superadmins can only view their own account's events
    if not auth.is_superadmin and event.account_id != auth.account_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return ScoreEventResponse.from_domain(event)
