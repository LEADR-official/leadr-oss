"""Global exception handlers for API layer."""

import logging

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.config import settings

logger = logging.getLogger(__name__)


async def catchall_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Convert all unhandled Exceptions to a 500 HTTP response with
    our response envelope.

    Args:
        request: The incoming request
        exc: The exception

    Returns:
        JSONResponse with 500 status and error detail
    """
    logger.exception(exc)
    if settings.DEBUG:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Convert all FastAPI HTTPExceptions to ensure our response envelope.

    Args:
        request: The incoming request
        exc: The exception

    Returns:
        JSONResponse with HTTP status code and error detail
    """
    if exc.status_code >= 500:
        logger.exception(exc)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


async def entity_not_found_handler(
    request: Request,
    exc: EntityNotFoundError,
) -> JSONResponse:
    """Convert EntityNotFoundError to 404 HTTP response.

    Args:
        request: The incoming request
        exc: The domain exception

    Returns:
        JSONResponse with 404 status and error detail
    """
    return JSONResponse(
        status_code=404,
        content={"error": f"{exc.entity_type} not found"},
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Convert RequestValidationError to 422 HTTP response with our
    error response envelope.

    Args:
        request: The incoming request
        exc: The validation exception

    Returns:
        JSONResponse with 422 status and list of validation errors
    """
    return JSONResponse(
        status_code=422,
        content={"error": jsonable_encoder(exc.errors()), "body": exc.body},
    )
