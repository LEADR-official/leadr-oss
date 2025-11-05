"""Shared FastAPI dependencies for the application."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.database import get_db

# Type alias for async database session dependency
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


# Example pattern for storage factory dependencies (to be implemented):
#
# async def get_game_storage(
#     session: DatabaseSession,
# ) -> GameStorage:
#     """Get game storage dependency."""
#     return GameStorage(session)
#
# Then use in routes as:
# storage: Annotated[GameStorage, Depends(get_game_storage)]
