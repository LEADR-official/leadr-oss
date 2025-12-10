"""API routes for score submission metadata management."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from leadr.auth.dependencies import AdminAuthContextDep
from leadr.common.domain.ids import AccountID, BoardID, DeviceID, ScoreSubmissionMetaID
from leadr.scores.api.score_submission_meta_schemas import ScoreSubmissionMetaResponse
from leadr.scores.services.dependencies import ScoreSubmissionMetaServiceDep

router = APIRouter()


@router.get("/score-submission-metadata", response_model=list[ScoreSubmissionMetaResponse])
async def list_submission_meta(
    auth: AdminAuthContextDep,
    service: ScoreSubmissionMetaServiceDep,
    account_id: Annotated[AccountID | None, Query(description="Account ID filter")] = None,
    board_id: BoardID | None = None,
    device_id: DeviceID | None = None,
) -> list[ScoreSubmissionMetaResponse]:
    """List score submission metadata for an account with optional filters.

    Returns all non-deleted submission metadata for the specified account, with optional
    filtering by board or device.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id is optional - if omitted, returns metadata from all accounts.

    Args:
        auth: Authentication context with user info.
        service: Injected submission metadata service dependency.
        account_id: Optional account_id query parameter (superadmins can omit to see all).
        board_id: Optional board ID to filter by.
        device_id: Optional device ID to filter by.

    Returns:
        List of ScoreSubmissionMetaResponse objects matching the filter criteria.

    Raises:
        403: User does not have access to the specified account.
    """
    # Superadmin without account_id = None (all accounts)
    # Superadmin with account_id = that specific account
    # Regular user = always their account_id (ignores query param)
    effective_account_id = account_id if auth.is_superadmin else auth.account_id
    metas = await service.list_submission_meta(
        account_id=effective_account_id,
        board_id=board_id,
        device_id=device_id,
    )

    return [ScoreSubmissionMetaResponse.from_domain(meta) for meta in metas]


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
    from leadr.scores.adapters.orm import ScoreORM

    meta = await service.get_by_id_or_raise(meta_id)

    # Get the associated score to check account access
    score_orm = await service.repository.session.get(ScoreORM, meta.score_id.uuid)
    if not score_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated score not found",
        )

    # Check authorization
    if not auth.has_access_to_account(AccountID(score_orm.account_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this metadata's account",
        )

    return ScoreSubmissionMetaResponse.from_domain(meta)
