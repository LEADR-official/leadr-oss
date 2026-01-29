"""API routes for board state management (admin only, read-only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from leadr.auth.dependencies import AdminAuthContextDep
from leadr.boards.api.board_state_schemas import BoardStateResponse
from leadr.boards.services.dependencies import BoardStateServiceDep
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import BoardID, BoardStateID, IdentityID

router = APIRouter()


@router.get("/board-states")
async def list_board_states(
    auth: AdminAuthContextDep,
    service: BoardStateServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    board_id: Annotated[BoardID | None, Query(description="Filter by board ID")] = None,
    identity_id: Annotated[IdentityID | None, Query(description="Filter by identity ID")] = None,
) -> PaginatedResponse[BoardStateResponse]:
    """List board states (Admin API).

    Returns a paginated list of board states. Board states are materialized
    ranking states computed from score events.

    Args:
        auth: Admin authentication context.
        service: Injected board state service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        board_id: Optional filter by board ID.
        identity_id: Optional filter by identity ID.

    Returns:
        Paginated list of board states.

    Raises:
        400: Invalid pagination cursor.
    """
    try:
        result = await service.list_board_states(
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
        response_model=BoardStateResponse,
    )


@router.get("/board-states/{state_id}")
async def get_board_state(
    state_id: BoardStateID,
    auth: AdminAuthContextDep,
    service: BoardStateServiceDep,
) -> BoardStateResponse:
    """Get a single board state by ID (Admin API).

    Args:
        state_id: Board state ID.
        auth: Admin authentication context.
        service: Injected board state service dependency.

    Returns:
        Board state details.

    Raises:
        404: Board state not found.
    """
    state = await service.get_board_state(state_id)

    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board state not found",
        )

    return BoardStateResponse.from_domain(state)
