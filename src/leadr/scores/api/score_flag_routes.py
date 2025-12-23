"""API routes for score flag management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from leadr.auth.dependencies import AdminAuthContextDep
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, BoardID, GameID, ScoreFlagID
from leadr.scores.api.score_flag_schemas import ScoreFlagResponse, ScoreFlagUpdateRequest
from leadr.scores.domain.anti_cheat.enums import ScoreFlagStatus
from leadr.scores.services.dependencies import ScoreFlagServiceDep

router = APIRouter()


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
        status: Optional status to filter by (PENDING, CONFIRMED_CHEAT, etc.).
        flag_type: Optional flag type to filter by (VELOCITY, DUPLICATE, etc.).

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

    # Get the associated score to check account access
    # We need to import ScoreService to look up the score
    from leadr.scores.services.score_service import ScoreService

    score_service = ScoreService(service.repository.session)
    score = await score_service.get_by_id_or_raise(flag.score_id)

    # Check authorization
    if not auth.has_access_to_account(score.account_id):
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

    # Get the associated score to check account access
    from leadr.scores.services.score_service import ScoreService

    score_service = ScoreService(service.repository.session)
    score = await score_service.get_by_id_or_raise(flag.score_id)

    # Check authorization
    if not auth.has_access_to_account(score.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this flag's account",
        )

    # Handle soft delete
    if request.deleted is True:
        flag = await service.soft_delete(flag_id)
        return ScoreFlagResponse.from_domain(flag)

    # Handle review/update
    if request.status is not None:
        try:
            status_enum = ScoreFlagStatus(request.status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid status: {request.status}. "
                    "Must be one of: PENDING, CONFIRMED_CHEAT, FALSE_POSITIVE, DISMISSED"
                ),
            ) from None

        # AuthContextDep (AdminAuthContext) guarantees user is non-None
        flag = await service.review_flag(
            flag_id=flag_id,
            status=status_enum,
            reviewer_decision=request.reviewer_decision,
            reviewer_id=auth.user.id,
        )
    elif request.reviewer_decision is not None:
        flag = await service.update_flag(
            flag_id=flag_id,
            reviewer_decision=request.reviewer_decision,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide either status, reviewer_decision, or deleted=true",
        )

    return ScoreFlagResponse.from_domain(flag)
