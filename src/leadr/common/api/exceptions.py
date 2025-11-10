"""Global exception handlers for API layer."""

from typing import cast

from fastapi import Request
from fastapi.responses import JSONResponse

from leadr.common.domain.exceptions import EntityNotFoundError


async def entity_not_found_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Convert EntityNotFoundError to 404 HTTP response.

    Args:
        request: The incoming request
        exc: The domain exception

    Returns:
        JSONResponse with 404 status and error detail
    """
    # Cast to EntityNotFoundError since we register this handler specifically for that type
    entity_exc = cast(EntityNotFoundError, exc)
    return JSONResponse(
        status_code=404,
        content={"detail": f"{entity_exc.entity_type} not found"},
    )
