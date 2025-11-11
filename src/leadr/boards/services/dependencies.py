"""Board service dependency injection."""

from typing import Annotated

from fastapi import Depends

from leadr.boards.services.board_service import BoardService
from leadr.boards.services.board_template_service import BoardTemplateService
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


async def get_board_template_service(db: DatabaseSession) -> BoardTemplateService:
    """Get BoardTemplateService dependency.

    Args:
        db: Database session from dependency injection

    Returns:
        BoardTemplateService instance for handling board template operations
    """
    return BoardTemplateService(db)


BoardTemplateServiceDep = Annotated[BoardTemplateService, Depends(get_board_template_service)]
