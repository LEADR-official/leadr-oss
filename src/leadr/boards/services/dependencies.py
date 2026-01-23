"""Board service dependency injection."""

from typing import Annotated

from fastapi import Depends

from leadr.boards.services.board_ratio_config_service import BoardRatioConfigService
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.board_state_service import BoardStateService
from leadr.boards.services.board_template_service import BoardTemplateService
from leadr.boards.services.run_entry_service import RunEntryService
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


async def get_board_state_service(db: DatabaseSession) -> BoardStateService:
    """Get BoardStateService dependency.

    Args:
        db: Database session from dependency injection

    Returns:
        BoardStateService instance for handling board state operations
    """
    return BoardStateService(db)


BoardStateServiceDep = Annotated[BoardStateService, Depends(get_board_state_service)]


async def get_run_entry_service(db: DatabaseSession) -> RunEntryService:
    """Get RunEntryService dependency.

    Args:
        db: Database session from dependency injection

    Returns:
        RunEntryService instance for handling run entry operations
    """
    return RunEntryService(db)


RunEntryServiceDep = Annotated[RunEntryService, Depends(get_run_entry_service)]


async def get_board_ratio_config_service(db: DatabaseSession) -> BoardRatioConfigService:
    """Get BoardRatioConfigService dependency.

    Args:
        db: Database session from dependency injection

    Returns:
        BoardRatioConfigService instance for handling ratio config operations
    """
    return BoardRatioConfigService(db)


BoardRatioConfigServiceDep = Annotated[
    BoardRatioConfigService, Depends(get_board_ratio_config_service)
]
