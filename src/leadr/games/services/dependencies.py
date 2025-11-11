"""Game service dependencies for FastAPI dependency injection."""

from typing import Annotated

from fastapi import Depends

from leadr.common.dependencies import DatabaseSession
from leadr.games.services.game_service import GameService


async def get_game_service(db: DatabaseSession) -> GameService:
    """Get GameService dependency."""
    return GameService(db)


GameServiceDep = Annotated[GameService, Depends(get_game_service)]
