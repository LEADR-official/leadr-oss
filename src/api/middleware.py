"""FastAPI middleware for request processing."""

import logging
import time
from typing import Any

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from leadr.common.utils.ip import extract_client_ip
from leadr.logging import get_logger

logger = logging.getLogger(__name__)

MAX_HEADER_LOG_LENGTH = 256


def _sanitise_header(value: str | None) -> str | None:
    """Sanitise and truncate a header value for safe logging."""
    if not value:
        return None
    return value[:MAX_HEADER_LOG_LENGTH]


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests with timing information.

    Logs each request with:
    - HTTP method and path as the event
    - status_code: HTTP response status
    - duration_ms: Request processing time in milliseconds
    - client_ip: Client IP address (from headers or direct connection)
    - LEADR-Client header
    - User-Agent header

    Example log output (JSON format):
        {"event": "GET /v1/health", "status_code": 200, "duration_ms": 12.5, ...}

    Example:
        app.add_middleware(AccessLogMiddleware)
    """

    def __init__(
        self,
        app: Any,
        logger: structlog.stdlib.BoundLogger | None = None,
    ):
        """Initialize access log middleware.

        Args:
            app: The FastAPI/Starlette application
            logger: Optional structlog logger instance (defaults to module logger)
        """
        super().__init__(app)
        self._logger = logger or get_logger(__name__)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request, measure timing, and log.

        Args:
            request: The incoming request
            call_next: The next middleware/route handler

        Returns:
            Response from the next handler
        """
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        log_kwargs = {
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": extract_client_ip(request),
            "account_id": getattr(request.state, "account_id", None),
            "game_id": getattr(request.state, "game_id", None),
            "client_fingerprint": getattr(request.state, "client_fingerprint", None),
            "leadr_client": _sanitise_header(request.headers.get("leadr-client")),
            "user_agent": _sanitise_header(request.headers.get("user-agent")),
        }
        log_method = (
            self._logger.error
            if response.status_code >= 500
            else self._logger.warning
            if response.status_code >= 400
            else self._logger.info
        )
        log_method("%s %s", request.method, request.url.path, **log_kwargs)

        return response
