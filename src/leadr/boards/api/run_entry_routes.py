"""API routes for run entry management (admin only, read-only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from leadr.auth.dependencies import AdminAuthContextDep
from leadr.boards.api.run_entry_schemas import RunEntryResponse
from leadr.boards.services.dependencies import RunEntryServiceDep
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import BoardID, IdentityID, RunEntryID

router = APIRouter()


@router.get("/run-entries")
async def list_run_entries(
    auth: AdminAuthContextDep,
    service: RunEntryServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    board_id: Annotated[BoardID | None, Query(description="Filter by board ID")] = None,
    identity_id: Annotated[IdentityID | None, Query(description="Filter by identity ID")] = None,
) -> PaginatedResponse[RunEntryResponse]:
    """List run entries (Admin API).

    Returns a paginated list of run entries. Run entries are individual scored
    submissions for RUN_RUNS boards where every submission is ranked.

    Args:
        auth: Admin authentication context.
        service: Injected run entry service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        board_id: Optional filter by board ID.
        identity_id: Optional filter by identity ID.

    Returns:
        Paginated list of run entries.

    Raises:
        400: Invalid pagination cursor.
    """
    try:
        result = await service.list_run_entries(
            board_id=board_id,
            identity_id=identity_id,
            pagination=pagination,
        )
    except CursorValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    filters: dict[str, str] = {}
    if board_id:
        filters["board_id"] = str(board_id)
    if identity_id:
        filters["identity_id"] = str(identity_id)

    return PaginatedResponse.from_paginated_result(
        result=result,
        pagination=pagination,
        filters=filters,
        response_model=RunEntryResponse,
    )


@router.get("/run-entries/{entry_id}")
async def get_run_entry(
    entry_id: RunEntryID,
    auth: AdminAuthContextDep,
    service: RunEntryServiceDep,
) -> RunEntryResponse:
    """Get a single run entry by ID (Admin API).

    Args:
        entry_id: Run entry ID.
        auth: Admin authentication context.
        service: Injected run entry service dependency.

    Returns:
        Run entry details.

    Raises:
        404: Run entry not found.
    """
    entry = await service.get_run_entry(entry_id)

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run entry not found",
        )

    return RunEntryResponse.from_domain(entry)
