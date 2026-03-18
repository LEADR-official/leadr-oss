"""API routes for score flag management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from leadr.auth.dependencies import AdminAuthContextDep
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, BoardID, GameID, ScoreFlagID
from leadr.scores.api.score_flag_schemas import (
    ScoreFlagCreateRequest,
    ScoreFlagResponse,
    ScoreFlagUpdateRequest,
)
from leadr.scores.domain.anti_cheat.enums import ScoreFlagStatus
from leadr.scores.services.dependencies import ScoreFlagServiceDep
from leadr.scores.services.score_event_service import ScoreEventService

router = APIRouter()


@router.post("/score-flags", status_code=status.HTTP_201_CREATED, response_model=ScoreFlagResponse)
async def create_score_flag(
    request: ScoreFlagCreateRequest,
    service: ScoreFlagServiceDep,
    auth: AdminAuthContextDep,
) -> ScoreFlagResponse:
    """Create a score flag (manual flagging by admin).

    Allows game admins to manually flag a score for review. By default, flags
    are created with type 'manual' and confidence 'medium', but admins can
    override these to specify a different flag type (e.g., duplicate, velocity).

    Args:
        request: Flag creation details (score_event_id, optional flag_type,
            confidence, and metadata).
        service: Injected score flag service dependency.
        auth: Authentication context with user info.

    Returns:
        ScoreFlagResponse with the created flag details.

    Raises:
        422: Invalid flag_type or confidence value.
        403: User does not have access to this score event's account.
        404: Score event not found.
    """
    # Get the score event to verify it exists and check account access
    score_event_service = ScoreEventService(service.repository.session)
    score_event = await score_event_service.get_score_event(request.score_event_id)

    if score_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Score event not found",
        )

    # Check authorization
    if not auth.has_access_to_account(score_event.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this score event's account",
        )

    # Create the flag (flag_type and confidence are already validated as enums by Pydantic)
    flag = await service.create_flag(
        score_event_id=request.score_event_id,
        flag_type=request.flag_type,
        confidence=request.confidence,
        status=request.status or ScoreFlagStatus.REMOVED,
        metadata=request.metadata,
    )

    return ScoreFlagResponse.from_domain(flag)


@router.get("/score-flags", response_model=PaginatedResponse[ScoreFlagResponse])
async def list_score_flags(
    auth: AdminAuthContextDep,
    service: ScoreFlagServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: Annotated[AccountID | None, Query(description="Account ID filter")] = None,
    board_id: BoardID | None = None,
    game_id: GameID | None = None,
    status: str | None = None,
    flag_type: str | None = None,
) -> PaginatedResponse[ScoreFlagResponse]:
    """List score flags for an account with optional filters and pagination.

    Returns paginated flags for the specified account, with optional
    filtering by board, game, status, or flag type. Supports cursor-based
    pagination with bidirectional navigation and custom sorting.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id is optional - if omitted, returns flags from all accounts.

    Args:
        auth: Authentication context with user info.
        service: Injected score flag service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account_id query parameter (superadmins can omit to see all).
        board_id: Optional board ID to filter by.
        game_id: Optional game ID to filter by.
        status: Optional status to filter by (pending, confirmed_cheat, etc.).
        flag_type: Optional flag type to filter by (velocity, duplicate, etc.).

    Returns:
        PaginatedResponse containing ScoreFlagResponse objects matching the filter criteria.

    Raises:
        400: Invalid cursor or sort field.
        403: User does not have access to the specified account.
    """
    # Superadmin without account_id = None (all accounts)
    # Superadmin with account_id = that specific account
    # Regular user = always their account_id (ignores query param)
    effective_account_id = account_id if auth.is_superadmin else auth.account_id

    try:
        result = await service.list_flags(
            account_id=effective_account_id,
            board_id=board_id,
            game_id=game_id,
            status=status,
            flag_type=flag_type,
            pagination=pagination,
        )
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Build filters dict for cursor validation
    filters_dict = {}
    if effective_account_id is not None:
        filters_dict["account_id"] = str(effective_account_id)
    if board_id is not None:
        filters_dict["board_id"] = str(board_id)
    if game_id is not None:
        filters_dict["game_id"] = str(game_id)
    if status is not None:
        filters_dict["status"] = status
    if flag_type is not None:
        filters_dict["flag_type"] = flag_type

    return PaginatedResponse.from_paginated_result(
        result=result,
        pagination=pagination,
        filters=filters_dict,
        response_model=ScoreFlagResponse,
    )


@router.get("/score-flags/{flag_id}", response_model=ScoreFlagResponse)
async def get_score_flag(
    flag_id: ScoreFlagID,
    service: ScoreFlagServiceDep,
    auth: AdminAuthContextDep,
) -> ScoreFlagResponse:
    """Get a score flag by ID.

    Args:
        flag_id: Flag identifier to retrieve.
        service: Injected score flag service dependency.
        auth: Authentication context with user info.

    Returns:
        ScoreFlagResponse with the flag details.

    Raises:
        403: User does not have access to this flag's account.
        404: Flag not found or soft-deleted.
    """
    flag = await service.get_by_id_or_raise(flag_id)

    # Get the associated score event to check account access
    score_event_service = ScoreEventService(service.repository.session)
    score_event = await score_event_service.get_by_id_or_raise(flag.score_event_id)

    # Check authorization
    if not auth.has_access_to_account(score_event.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this flag's account",
        )

    return ScoreFlagResponse.from_domain(flag)


@router.patch("/score-flags/{flag_id}", response_model=ScoreFlagResponse)
async def update_score_flag(
    flag_id: ScoreFlagID,
    request: ScoreFlagUpdateRequest,
    service: ScoreFlagServiceDep,
    auth: AdminAuthContextDep,
) -> ScoreFlagResponse:
    """Update a score flag (review or soft-delete).

    Allows reviewing a flag (updating status and reviewer decision) or
    soft-deleting the flag.

    Args:
        flag_id: Flag identifier to update.
        request: Update details (status, reviewer_decision, or deleted flag).
        service: Injected score flag service dependency.
        auth: Authentication context with user info.

    Returns:
        ScoreFlagResponse with the updated flag details.

    Raises:
        403: User does not have access to this flag's account.
        404: Flag not found.
        400: Invalid update request.
    """
    # Get the flag to check account access
    flag = await service.get_by_id_or_raise(flag_id)

    # Get the associated score event to check account access
    score_event_service = ScoreEventService(service.repository.session)
    score_event = await score_event_service.get_by_id_or_raise(flag.score_event_id)

    # Check authorization
    if not auth.has_access_to_account(score_event.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this flag's account",
        )

    # Handle soft delete
    if request.deleted is True:
        flag = await service.soft_delete(flag_id)
        return ScoreFlagResponse.from_domain(flag)

    # Get only fields explicitly provided in request (exclude_unset=True)
    update_data = request.model_dump(exclude_unset=True)
    update_data.pop("deleted", None)  # Handled separately above

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Must provide either status, reviewer_decision, or deleted=true",
        )

    # Handle review/update - if status is provided, use review_flag
    if request.status is not None:
        # AuthContextDep (AdminAuthContext) guarantees user is non-None
        flag = await service.review_flag(
            flag_id=flag_id,
            status=request.status,
            reviewer_decision=update_data.get("reviewer_decision"),
            reviewer_id=auth.user.id,
        )
    else:
        # No status - use generic update_flag for other fields
        flag = await service.update_flag(flag_id, **update_data)

    return ScoreFlagResponse.from_domain(flag)
