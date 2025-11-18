"""Board template API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from leadr.auth.dependencies import (
    AuthContextDep,
    QueryAccountIDDep,
    validate_body_account_id,
)
from leadr.boards.api.board_template_schemas import (
    BoardTemplateCreateRequest,
    BoardTemplateResponse,
    BoardTemplateUpdateRequest,
)
from leadr.boards.services.dependencies import BoardTemplateServiceDep
from leadr.common.api.pagination import PaginatedResponse, PaginationMeta, PaginationParams
from leadr.common.domain.cursor import Cursor, CursorValidationError
from leadr.common.domain.ids import BoardTemplateID, GameID
from leadr.common.domain.pagination import PaginationDirection

router = APIRouter()


@router.post(
    "/board-templates",
    status_code=status.HTTP_201_CREATED,
    response_model=BoardTemplateResponse,
)
async def create_board_template(
    request: BoardTemplateCreateRequest, service: BoardTemplateServiceDep, auth: AuthContextDep
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

    Returns:
        BoardTemplateResponse with the created template including auto-generated ID.

    Raises:
        403: User does not have access to the specified account.
        404: Game or account not found.
        400: Game doesn't belong to the specified account.
    """
    validate_body_account_id(auth, request.account_id)

    try:
        template = await service.create_board_template(
            account_id=request.account_id,
            game_id=request.game_id,
            name=request.name,
            repeat_interval=request.repeat_interval,
            next_run_at=request.next_run_at,
            is_active=request.is_active,
            name_template=request.name_template,
            config=request.config,
            config_template=request.config_template,
        )
    except IntegrityError:
        raise HTTPException(status_code=404, detail="Game or account not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    return BoardTemplateResponse.from_domain(template)


@router.get("/board-templates/{template_id}", response_model=BoardTemplateResponse)
async def get_board_template(
    template_id: BoardTemplateID, service: BoardTemplateServiceDep, auth: AuthContextDep
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
    account_id: QueryAccountIDDep,
    service: BoardTemplateServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    game_id: GameID | None = None,
) -> PaginatedResponse[BoardTemplateResponse]:
    """List board templates for an account with pagination, optionally filtered by game.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id must be explicitly provided as a query parameter.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=name:asc,created_at:desc
    - Valid sort fields: id, name, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/board-templates?account_id=acc_123&game_id=gam_456&limit=50&sort=name:asc

    Args:
        account_id: Account ID (auto-resolved for regular users, required for superadmins).
        service: Injected board template service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        game_id: Optional game ID to filter templates by.

    Returns:
        PaginatedResponse with board templates and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
    """
    try:
        if game_id is not None:
            result = await service.list_board_templates_by_game(
                account_id, game_id, pagination=pagination
            )
        else:
            result = await service.list_board_templates_by_account(
                account_id, pagination=pagination
            )
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Build filter dict for cursors
    filters_dict = {}
    if game_id is not None:
        filters_dict["game_id"] = str(game_id)

    # Build cursors from result positions
    next_cursor_str = None
    prev_cursor_str = None

    if result.next_position is not None:
        next_cursor = Cursor(
            position=result.next_position,
            sort_fields=pagination.sort_spec,
            filters=filters_dict,
            direction=PaginationDirection.FORWARD,
        )
        next_cursor_str = next_cursor.encode()

    if result.prev_position is not None:
        prev_cursor = Cursor(
            position=result.prev_position,
            sort_fields=pagination.sort_spec,
            filters=filters_dict,
            direction=PaginationDirection.BACKWARD,
        )
        prev_cursor_str = prev_cursor.encode()

    # Convert domain entities to response models
    response_items = [BoardTemplateResponse.from_domain(template) for template in result.items]

    # Build paginated response
    return PaginatedResponse(
        data=response_items,
        pagination=PaginationMeta(
            next_cursor=next_cursor_str,
            prev_cursor=prev_cursor_str,
            has_next=result.has_next,
            has_prev=result.has_prev,
            count=result.count,
        ),
    )


@router.patch("/board-templates/{template_id}", response_model=BoardTemplateResponse)
async def update_board_template(
    template_id: BoardTemplateID,
    request: BoardTemplateUpdateRequest,
    service: BoardTemplateServiceDep,
    auth: AuthContextDep,
) -> BoardTemplateResponse:
    """Update a board template.

    Supports updating any template field or soft-deleting the template.

    Args:
        template_id: Unique identifier for the template.
        request: Template update details (all fields optional).
        service: Injected board template service dependency.
        auth: Authentication context with user info.

    Returns:
        BoardTemplateResponse with the updated template details.

    Raises:
        403: User does not have access to this template's account.
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

    # Handle soft delete first
    if request.deleted is True:
        template = await service.soft_delete(template_id)
        return BoardTemplateResponse.from_domain(template)

    # Handle field updates
    template = await service.update_board_template(
        template_id=template_id,
        name=request.name,
        name_template=request.name_template,
        repeat_interval=request.repeat_interval,
        config=request.config,
        config_template=request.config_template,
        next_run_at=request.next_run_at,
        is_active=request.is_active,
    )

    return BoardTemplateResponse.from_domain(template)
