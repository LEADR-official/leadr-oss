"""API routes for score submission metadata management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from leadr.auth.dependencies import AuthContextDep, QueryAccountIDDep
from leadr.scores.api.score_submission_meta_schemas import ScoreSubmissionMetaResponse
from leadr.scores.services.dependencies import ScoreSubmissionMetaServiceDep

router = APIRouter()


@router.get("/score-submission-metadata", response_model=list[ScoreSubmissionMetaResponse])
async def list_submission_meta(
    account_id: QueryAccountIDDep,
    service: ScoreSubmissionMetaServiceDep,
    board_id: UUID | None = None,
    device_id: UUID | None = None,
) -> list[ScoreSubmissionMetaResponse]:
    """List score submission metadata for an account with optional filters.

    Returns all non-deleted submission metadata for the specified account, with optional
    filtering by board or device.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id must be explicitly provided as a query parameter.

    Args:
        account_id: Account ID (auto-resolved for regular users, required for superadmins).
        service: Injected submission metadata service dependency.
        board_id: Optional board ID to filter by.
        device_id: Optional device ID to filter by.

    Returns:
        List of ScoreSubmissionMetaResponse objects matching the filter criteria.

    Raises:
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
    """
    metas = await service.list_submission_meta(
        account_id=account_id,
        board_id=board_id,
        device_id=device_id,
    )

    return [ScoreSubmissionMetaResponse.from_domain(meta) for meta in metas]


@router.get(
    "/score-submission-metadata/{meta_id}",
    response_model=ScoreSubmissionMetaResponse,
)
async def get_submission_meta(
    meta_id: UUID,
    service: ScoreSubmissionMetaServiceDep,
    auth: AuthContextDep,
) -> ScoreSubmissionMetaResponse:
    """Get score submission metadata by ID.

    Args:
        meta_id: UUID of the submission metadata to retrieve.
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
    score_orm = await service.repository.session.get(ScoreORM, meta.score_id)
    if not score_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated score not found",
        )

    # Check authorization
    if not auth.has_access_to_account(score_orm.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this metadata's account",
        )

    return ScoreSubmissionMetaResponse.from_domain(meta)
