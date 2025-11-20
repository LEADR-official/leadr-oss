"""API routes for score flag management."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from leadr.auth.dependencies import AdminAuthContextDep, AdminAuthContextWithAccountIDDep
from leadr.common.domain.ids import AccountID, BoardID, GameID, ScoreFlagID
from leadr.scores.api.score_flag_schemas import ScoreFlagResponse, ScoreFlagUpdateRequest
from leadr.scores.domain.anti_cheat.enums import ScoreFlagStatus
from leadr.scores.services.dependencies import ScoreFlagServiceDep

router = APIRouter()


@router.get("/score-flags", response_model=list[ScoreFlagResponse])
async def list_score_flags(
    auth: AdminAuthContextWithAccountIDDep,
    service: ScoreFlagServiceDep,
    account_id: Annotated[AccountID | None, Query(description="Account ID filter")] = None,
    board_id: BoardID | None = None,
    game_id: GameID | None = None,
    status: str | None = None,
    flag_type: str | None = None,
) -> list[ScoreFlagResponse]:
    """List score flags for an account with optional filters.

    Returns all non-deleted flags for the specified account, with optional
    filtering by board, game, status, or flag type.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id must be explicitly provided as a query parameter.

    Args:
        auth: Authentication context with user info.
        service: Injected score flag service dependency.
        account_id: Optional account_id query parameter (required for superadmins).
        board_id: Optional board ID to filter by.
        game_id: Optional game ID to filter by.
        status: Optional status to filter by (PENDING, CONFIRMED_CHEAT, etc.).
        flag_type: Optional flag type to filter by (VELOCITY, DUPLICATE, etc.).

    Returns:
        List of ScoreFlagResponse objects matching the filter criteria.

    Raises:
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
    """
    flags = await service.list_flags(
        account_id=account_id or auth.account_id,
        board_id=board_id,
        game_id=game_id,
        status=status,
        flag_type=flag_type,
    )

    return [ScoreFlagResponse.from_domain(flag) for flag in flags]


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
