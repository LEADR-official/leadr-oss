"""API routes for score management."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError

from leadr.auth.dependencies import (
    AuthContextDep,
    QueryAccountIDDep,
    validate_body_account_id,
)
from leadr.common.domain.ids import BoardID, DeviceID, GameID, ScoreID
from leadr.scores.api.schemas import ScoreCreateRequest, ScoreResponse, ScoreUpdateRequest
from leadr.scores.services.dependencies import ScoreServiceDep

router = APIRouter()


@router.post("/scores", status_code=status.HTTP_201_CREATED)
async def create_score(
    score_request: ScoreCreateRequest,
    request: Request,
    service: ScoreServiceDep,
    background_tasks: BackgroundTasks,
    auth: AuthContextDep,
) -> ScoreResponse:
    """Create a new score.

    Creates a new score submission for a board. Performs three-level validation:
    board exists, board belongs to the specified account, and game matches
    the board's game.

    For regular users, account_id must match their API key's account.
    For superadmins, any account_id is accepted.

    Args:
        request: Score creation details including account_id, game_id, board_id,
                device_id, player_name, value, and optional filters.
        service: Injected score service dependency.
        background_tasks: FastAPI background tasks for async metadata updates.
        auth: Authentication context with user info.

    Returns:
        ScoreResponse with the created score including auto-generated ID and timestamps.

    Raises:
        403: User does not have access to the specified account.
        404: Account, game, board, or device not found.
        400: Validation failed (board doesn't belong to account, or game doesn't
            match board's game).
    """
    validate_body_account_id(auth, score_request.account_id)

    # Get geo data from request state (populated by GeoIP middleware)
    timezone = getattr(request.state, "geo_timezone", None)
    country = getattr(request.state, "geo_country", None)
    city = getattr(request.state, "geo_city", None)

    try:
        score, anti_cheat_result = await service.create_score(
            account_id=score_request.account_id,
            game_id=score_request.game_id,
            board_id=score_request.board_id,
            device_id=score_request.device_id,
            player_name=score_request.player_name,
            value=score_request.value,
            value_display=score_request.value_display,
            timezone=timezone,
            country=country,
            city=city,
            metadata=score_request.metadata,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=404,
            detail="Account, game, board, or device not found",
        ) from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Schedule metadata update as background task (non-blocking)
    if score_request.device_id is not None:
        background_tasks.add_task(
            service.update_submission_metadata,
            score,
            score_request.device_id,
            score_request.board_id,
            anti_cheat_result,
        )

    return ScoreResponse.from_domain(score)


@router.get("/scores/{score_id}", response_model=ScoreResponse)
async def get_score(
    score_id: ScoreID,
    service: ScoreServiceDep,
    auth: AuthContextDep,
) -> ScoreResponse:
    """Get a score by ID.

    Args:
        score_id: UUID of the score to retrieve.
        service: Injected score service dependency.
        auth: Authentication context with user info.

    Returns:
        ScoreResponse with the score details.

    Raises:
        403: User does not have access to this score's account.
        404: Score not found or soft-deleted.
    """
    score = await service.get_by_id_or_raise(score_id)

    # Check authorization
    if not auth.has_access_to_account(score.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this score's account",
        )

    return ScoreResponse.from_domain(score)


@router.get("/scores", response_model=list[ScoreResponse])
async def list_scores(
    account_id: QueryAccountIDDep,
    service: ScoreServiceDep,
    board_id: BoardID | None = None,
    game_id: GameID | None = None,
    device_id: DeviceID | None = None,
) -> list[ScoreResponse]:
    """List scores for an account with optional filters.

    Returns all non-deleted scores for the specified account, with optional
    filtering by board, game, or device.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id must be explicitly provided as a query parameter.

    Args:
        account_id: Account ID (auto-resolved for regular users, required for superadmins).
        service: Injected score service dependency.
        board_id: Optional board ID to filter by.
        game_id: Optional game ID to filter by.
        device_id: Optional device ID to filter by.

    Returns:
        List of ScoreResponse objects matching the filter criteria.

    Raises:
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
    """
    scores = await service.list_scores(
        account_id=account_id,
        board_id=board_id,
        game_id=game_id,
        device_id=device_id,
    )
    return [ScoreResponse.from_domain(score) for score in scores]


@router.patch("/scores/{score_id}", response_model=ScoreResponse)
async def update_score(
    score_id: ScoreID,
    request: ScoreUpdateRequest,
    service: ScoreServiceDep,
    auth: AuthContextDep,
) -> ScoreResponse:
    """Update a score.

    Supports partial updates of score fields. Any field not provided will
    remain unchanged. Set deleted: true to soft delete the score.

    Args:
        score_id: UUID of the score to update.
        request: Score update details with optional fields to modify.
        service: Injected score service dependency.
        auth: Authentication context with user info.

    Returns:
        ScoreResponse with the updated score details.

    Raises:
        403: User does not have access to this score's account.
        404: Score not found or already soft-deleted.
    """
    # Fetch score to check authorization
    score = await service.get_by_id_or_raise(score_id)

    # Check authorization
    if not auth.has_access_to_account(score.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this score's account",
        )

    # Handle soft delete
    if request.deleted is True:
        score = await service.soft_delete(score_id)
        return ScoreResponse.from_domain(score)

    # Update other fields
    score = await service.update_score(
        score_id=score_id,
        player_name=request.player_name,
        value=request.value,
        value_display=request.value_display,
        timezone=request.timezone,
        country=request.country,
        city=request.city,
        metadata=request.metadata,
    )
    return ScoreResponse.from_domain(score)
