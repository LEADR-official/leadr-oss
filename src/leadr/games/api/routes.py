"""Game API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from leadr.auth.dependencies import (
    AuthContextDep,
    QueryAccountIDDep,
    validate_body_account_id,
)
from leadr.games.api.schemas import (
    GameCreateRequest,
    GameResponse,
    GameUpdateRequest,
)
from leadr.games.services.dependencies import GameServiceDep

router = APIRouter()


@router.post("/games", status_code=status.HTTP_201_CREATED, response_model=GameResponse)
async def create_game(
    request: GameCreateRequest, service: GameServiceDep, auth: AuthContextDep
) -> GameResponse:
    """Create a new game.

    Creates a new game associated with an existing account. Games can optionally
    be configured with Steam integration and a default leaderboard.

    For regular users, account_id must match their API key's account.
    For superadmins, any account_id is accepted.

    Args:
        request: Game creation details including account_id, name, and optional settings.
        service: Injected game service dependency.
        auth: Authentication context with user info.

    Returns:
        GameResponse with the created game including auto-generated ID and timestamps.

    Raises:
        403: User does not have access to the specified account.
        404: Account not found.
    """
    validate_body_account_id(auth, request.account_id)

    try:
        game = await service.create_game(
            account_id=request.account_id,
            name=request.name,
            steam_app_id=request.steam_app_id,
            default_board_id=request.default_board_id,
            anti_cheat_enabled=request.anti_cheat_enabled,
        )
    except IntegrityError:
        raise HTTPException(status_code=404, detail="Account not found") from None

    return GameResponse.from_domain(game)


@router.get("/games/{game_id}", response_model=GameResponse)
async def get_game(game_id: UUID, service: GameServiceDep, auth: AuthContextDep) -> GameResponse:
    """Get a game by ID.

    Args:
        game_id: Unique identifier for the game.
        service: Injected game service dependency.
        auth: Authentication context with user info.

    Returns:
        GameResponse with full game details.

    Raises:
        403: User does not have access to this game's account.
        404: Game not found.
    """
    game = await service.get_by_id_or_raise(game_id)

    # Check authorization
    if not auth.has_access_to_account(game.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this game's account",
        )

    return GameResponse.from_domain(game)


@router.get("/games", response_model=list[GameResponse])
async def list_games(
    account_id: QueryAccountIDDep,
    service: GameServiceDep,
) -> list[GameResponse]:
    """List all games for an account.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id must be explicitly provided as a query parameter.

    Args:
        account_id: Account ID (auto-resolved for regular users, required for superadmins).
        service: Injected game service dependency.

    Returns:
        List of all active games for the specified account.

    Raises:
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
    """
    games = await service.list_games(account_id)
    return [GameResponse.from_domain(game) for game in games]


@router.patch("/games/{game_id}", response_model=GameResponse)
async def update_game(
    game_id: UUID, request: GameUpdateRequest, service: GameServiceDep, auth: AuthContextDep
) -> GameResponse:
    """Update a game.

    Supports updating name, Steam App ID, default board ID, or soft-deleting the game.

    Args:
        game_id: Unique identifier for the game.
        request: Game update details (all fields optional).
        service: Injected game service dependency.
        auth: Authentication context with user info.

    Returns:
        GameResponse with the updated game details.

    Raises:
        403: User does not have access to this game's account.
        404: Game not found.
    """
    # Fetch game to check authorization
    game = await service.get_by_id_or_raise(game_id)

    # Check authorization
    if not auth.has_access_to_account(game.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this game's account",
        )

    # Handle soft delete first
    if request.deleted is True:
        game = await service.soft_delete(game_id)
        return GameResponse.from_domain(game)

    # Handle field updates using service method
    game = await service.update_game(
        game_id=game_id,
        name=request.name,
        steam_app_id=request.steam_app_id,
        default_board_id=request.default_board_id,
        anti_cheat_enabled=request.anti_cheat_enabled,
    )

    return GameResponse.from_domain(game)
