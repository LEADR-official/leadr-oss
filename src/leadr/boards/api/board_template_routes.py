"""Board template API routes."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from leadr.auth.dependencies import AdminAuthContextDep
from leadr.boards.api.board_template_schemas import (
    BoardTemplateCreateRequest,
    BoardTemplateResponse,
    BoardTemplateUpdateRequest,
)
from leadr.boards.domain.board import BoardType, KeepStrategy
from leadr.boards.services.dependencies import BoardTemplateServiceDep
from leadr.common.api.hooks import (
    PreCreateBoardTemplateHookDep,
    PreUpdateBoardTemplateHookDep,
)
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, BoardTemplateID, GameID

router = APIRouter()


@router.post(
    "/board-templates",
    status_code=status.HTTP_201_CREATED,
    response_model=BoardTemplateResponse,
)
async def create_board_template(
    request: BoardTemplateCreateRequest,
    service: BoardTemplateServiceDep,
    auth: AdminAuthContextDep,
    background_tasks: BackgroundTasks,
    pre_hook: PreCreateBoardTemplateHookDep,
) -> BoardTemplateResponse:
    """Create a new board template.

    Creates a template for automatically generating boards at regular intervals.
    The game must belong to the specified account.

    For regular users, account_id must match their API key's account.
    For superadmins, any account_id is accepted.

    Args:
        request: Template creation details including repeat_interval and configuration.
        service: Injected board template service dependency.
        auth: Authentication context with user info.
        pre_hook: Pre-create hook for entitlement checks.

    Returns:
        BoardTemplateResponse with the created template including auto-generated ID.

    Raises:
        403: User does not have access to the specified account, or repeat_interval not allowed.
        404: Game or account not found.
        400: Game doesn't belong to the specified account.
    """
    # Run pre-create hook (entitlement checks, validation, etc.)
    await pre_hook(request, auth, background_tasks)

    # Resolve keep_strategy based on board_type
    if request.board_type == BoardType.RUN_IDENTITY:
        effective_keep_strategy = request.keep_strategy or KeepStrategy.BEST
    else:
        # Non-RUN_IDENTITY boards always use NA
        effective_keep_strategy = KeepStrategy.NA

    try:
        template = await service.create_board_template(
            account_id=request.account_id,
            game_id=request.game_id,
            name=request.name,
            slug=request.slug,
            repeat_interval=request.repeat_interval,
            next_run_at=request.next_run_at,
            is_active=request.is_active,
            is_published=request.is_published,
            unique_player_names=request.unique_player_names,
            name_template=request.name_template,
            series=request.series,
            icon=request.icon,
            unit=request.unit,
            sort_direction=request.sort_direction,
            board_type=request.board_type,
            keep_strategy=effective_keep_strategy,
            starts_at=request.starts_at,
            ends_at=request.ends_at,
            tags=request.tags,
            config=request.config,
        )
    except IntegrityError:
        raise HTTPException(status_code=404, detail="Game or account not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return BoardTemplateResponse.from_domain(template)


@router.get("/board-templates/{template_id}", response_model=BoardTemplateResponse)
async def get_board_template(
    template_id: BoardTemplateID, service: BoardTemplateServiceDep, auth: AdminAuthContextDep
) -> BoardTemplateResponse:
    """Get a board template by ID.

    Args:
        template_id: Unique identifier for the template.
        service: Injected board template service dependency.
        auth: Authentication context with user info.

    Returns:
        BoardTemplateResponse with full template details.

    Raises:
        403: User does not have access to this template's account.
        404: Template not found.
    """
    template = await service.get_by_id_or_raise(template_id)

    # Check authorization
    if not auth.has_access_to_account(template.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this template's account",
        )

    return BoardTemplateResponse.from_domain(template)


@router.get("/board-templates", response_model=PaginatedResponse[BoardTemplateResponse])
async def list_board_templates(
    auth: AdminAuthContextDep,
    service: BoardTemplateServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: Annotated[AccountID | None, Query(description="Account ID filter")] = None,
    game_id: Annotated[GameID | None, Query(description="Filter by game ID")] = None,
) -> PaginatedResponse[BoardTemplateResponse]:
    """List board templates for an account with pagination, optionally filtered by game.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id is optional - if omitted, returns templates from all accounts.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=name:asc,created_at:desc
    - Valid sort fields: id, name, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/board-templates?account_id=acc_123&game_id=gam_456&limit=50&sort=name:asc

    Args:
        auth: Authentication context with user info.
        service: Injected board template service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account_id query parameter (superadmins can omit to see all).
        game_id: Optional game ID to filter templates by.

    Returns:
        PaginatedResponse with board templates and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
        403: User does not have access to the specified account.
    """
    # Superadmin without account_id = None (all accounts)
    # Superadmin with account_id = that specific account
    # Regular user = always their account_id (ignores query param)
    effective_account_id = account_id if auth.is_superadmin else auth.account_id
    try:
        if game_id is not None:
            result = await service.list_board_templates_by_game(
                effective_account_id, game_id, pagination=pagination
            )
        else:
            result = await service.list_board_templates_by_account(
                effective_account_id, pagination=pagination
            )
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Build filter dict for cursors
    filters_dict = {}
    if game_id is not None:
        filters_dict["game_id"] = str(game_id)

    return PaginatedResponse.from_paginated_result(
        result=result,
        pagination=pagination,
        filters=filters_dict,
        response_model=BoardTemplateResponse,
    )


@router.patch("/board-templates/{template_id}", response_model=BoardTemplateResponse)
async def update_board_template(
    template_id: BoardTemplateID,
    request: BoardTemplateUpdateRequest,
    service: BoardTemplateServiceDep,
    auth: AdminAuthContextDep,
    background_tasks: BackgroundTasks,
    pre_hook: PreUpdateBoardTemplateHookDep,
) -> BoardTemplateResponse:
    """Update a board template.

    Supports updating any template field or soft-deleting the template.

    Args:
        template_id: Unique identifier for the template.
        request: Template update details (all fields optional).
        service: Injected board template service dependency.
        auth: Authentication context with user info.
        pre_hook: Pre-update hook for entitlement checks.

    Returns:
        BoardTemplateResponse with the updated template details.

    Raises:
        403: User does not have access to this template's account, or repeat_interval not allowed.
        404: Template not found.
    """
    # Fetch template to check authorization
    template = await service.get_by_id_or_raise(template_id)

    # Check authorization
    if not auth.has_access_to_account(template.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this template's account",
        )

    # Run pre-update hook (entitlement checks, validation, etc.)
    await pre_hook(template.account_id, request, auth, background_tasks)

    # Handle soft delete first
    if request.deleted is True:
        template = await service.soft_delete(template_id)
        return BoardTemplateResponse.from_domain(template)

    # Get only fields explicitly provided in request (exclude_unset=True)
    # This allows null values to clear fields vs omitted fields staying unchanged
    update_data = request.model_dump(exclude_unset=True)
    update_data.pop("deleted", None)  # Handled separately above

    if update_data:
        template = await service.update_board_template(template_id, **update_data)

    return BoardTemplateResponse.from_domain(template)
