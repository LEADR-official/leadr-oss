"""API routes for score submission metadata management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from leadr.auth.dependencies import AdminAuthContextDep
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, BoardID, ScoreSubmissionMetaID
from leadr.scores.adapters.orm import ScoreEventORM
from leadr.scores.api.score_submission_meta_schemas import ScoreSubmissionMetaResponse
from leadr.scores.services.dependencies import ScoreSubmissionMetaServiceDep

router = APIRouter()


@router.get(
    "/score-submission-metadata", response_model=PaginatedResponse[ScoreSubmissionMetaResponse]
)
async def list_submission_meta(
    auth: AdminAuthContextDep,
    service: ScoreSubmissionMetaServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: Annotated[AccountID | None, Query(description="Account ID filter")] = None,
    board_id: BoardID | None = None,
) -> PaginatedResponse[ScoreSubmissionMetaResponse]:
    """List score submission metadata for an account with optional filters and pagination.

    Returns paginated submission metadata for the specified account, with optional
    filtering by board. Supports cursor-based pagination with bidirectional
    navigation and custom sorting.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id is optional - if omitted, returns metadata from all accounts.

    Args:
        auth: Authentication context with user info.
        service: Injected submission metadata service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account_id query parameter (superadmins can omit to see all).
        board_id: Optional board ID to filter by.

    Returns:
        PaginatedResponse containing ScoreSubmissionMetaResponse objects matching the filter.

    Raises:
        400: Invalid cursor or sort field.
        403: User does not have access to the specified account.
    """
    # Superadmin without account_id = None (all accounts)
    # Superadmin with account_id = that specific account
    # Regular user = always their account_id (ignores query param)
    effective_account_id = account_id if auth.is_superadmin else auth.account_id

    try:
        result = await service.list_submission_meta(
            account_id=effective_account_id,
            board_id=board_id,
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

    return PaginatedResponse.from_paginated_result(
        result=result,
        pagination=pagination,
        filters=filters_dict,
        response_model=ScoreSubmissionMetaResponse,
    )


@router.get(
    "/score-submission-metadata/{meta_id}",
    response_model=ScoreSubmissionMetaResponse,
)
async def get_submission_meta(
    meta_id: ScoreSubmissionMetaID,
    service: ScoreSubmissionMetaServiceDep,
    auth: AdminAuthContextDep,
) -> ScoreSubmissionMetaResponse:
    """Get score submission metadata by ID.

    Args:
        meta_id: Submission metadata identifier to retrieve.
        service: Injected submission metadata service dependency.
        auth: Authentication context with user info.

    Returns:
        ScoreSubmissionMetaResponse with the submission metadata details.

    Raises:
        403: User does not have access to this metadata's account.
        404: Submission metadata not found or soft-deleted.
    """
    meta = await service.get_by_id_or_raise(meta_id)

    # Get the associated score event to check account access
    score_event_orm = await service.repository.session.get(ScoreEventORM, meta.score_event_id.uuid)
    if not score_event_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated score event not found",
        )

    # Check authorization
    if not auth.has_access_to_account(AccountID(score_event_orm.account_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this metadata's account",
        )

    return ScoreSubmissionMetaResponse.from_domain(meta)
