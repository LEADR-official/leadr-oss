"""Board service dependency injection."""

from typing import Annotated

from fastapi import Depends

from leadr.boards.services.board_service import BoardService
from leadr.common.dependencies import DatabaseSession


async def get_board_service(db: DatabaseSession) -> BoardService:
    """Get BoardService dependency.

    Args:
        db: Database session from dependency injection

    Returns:
        BoardService instance for handling board operations
    """
    return BoardService(db)


BoardServiceDep = Annotated[BoardService, Depends(get_board_service)]
