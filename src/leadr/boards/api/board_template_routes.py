"""Board template API routes."""

from fastapi import APIRouter, HTTPException, status
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
from leadr.common.domain.ids import BoardTemplateID, GameID

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
            counter=request.counter,
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


@router.get("/board-templates", response_model=list[BoardTemplateResponse])
async def list_board_templates(
    account_id: QueryAccountIDDep,
    service: BoardTemplateServiceDep,
    game_id: GameID | None = None,
) -> list[BoardTemplateResponse]:
    """List board templates for an account, optionally filtered by game.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id must be explicitly provided as a query parameter.

    Args:
        account_id: Account ID (auto-resolved for regular users, required for superadmins).
        service: Injected board template service dependency.
        game_id: Optional game ID to filter templates by.

    Returns:
        List of board templates matching the filter criteria.

    Raises:
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
    """
    if game_id is not None:
        templates = await service.list_board_templates_by_game(account_id, game_id)
    else:
        templates = await service.list_board_templates_by_account(account_id)

    return [BoardTemplateResponse.from_domain(template) for template in templates]


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
        counter=request.counter,
        repeat_interval=request.repeat_interval,
        config=request.config,
        config_template=request.config_template,
        next_run_at=request.next_run_at,
        is_active=request.is_active,
    )

    return BoardTemplateResponse.from_domain(template)
