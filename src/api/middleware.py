"""FastAPI middleware for request processing."""

import logging
import time
from typing import Any

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from leadr.common.geoip import GeoIPService
from leadr.common.utils.ip import extract_client_ip
from leadr.logging import get_logger

logger = logging.getLogger(__name__)


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests with timing information.

    Logs each request with:
    - HTTP method and path as the event
    - status_code: HTTP response status
    - duration_ms: Request processing time in milliseconds
    - client_ip: Client IP address (from headers or direct connection)

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

        self._logger.info(
            "%s %s",
            request.method,
            request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            client_ip=extract_client_ip(request),
        )

        return response


class GeoIPMiddleware(BaseHTTPMiddleware):
    """Middleware to extract client IP and attach geolocation data to request state.

    This middleware:
    1. Extracts the client IP from various headers (X-Real-IP, X-Forwarded-For, CF-Connecting-IP)
    2. Falls back to request.client.host if no headers present
    3. Optionally uses a dev override IP for local development
    4. Looks up geolocation data using MaxMind GeoLite2 databases
    5. Attaches geo info to request.state for use in route handlers

    The middleware is designed to fail gracefully - if geo lookup fails for any reason,
    the request continues without geo data.

    Example:
        app.add_middleware(
            GeoIPMiddleware,
            geoip_service=geoip_service,
            dev_override_ip="8.8.8.8",  # Optional: for development
        )
    """

    def __init__(
        self,
        app,
        geoip_service: GeoIPService | None = None,
        dev_override_ip: str | None = None,
    ):
        """Initialize GeoIP middleware.

        Args:
            app: The FastAPI/Starlette application
            geoip_service: Optional GeoIPService instance for IP lookups
                           (if None, will use app.state.geoip_service)
            dev_override_ip: Optional IP to use in development (bypasses extraction)
        """
        super().__init__(app)
        self._geoip_service = geoip_service
        self.dev_override_ip = dev_override_ip

    def _get_geoip_service(self, request: Request) -> GeoIPService | None:
        """Get GeoIPService from either init parameter or app state.

        Args:
            request: The incoming request

        Returns:
            GeoIPService instance or None
        """
        if self._geoip_service:
            return self._geoip_service
        return getattr(request.app.state, "geoip_service", None)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request, extract IP, attach geo data, and continue.

        Args:
            request: The incoming request
            call_next: The next middleware/route handler

        Returns:
            Response from the next handler
        """
        # Initialize geo fields to None (default if anything fails)
        request.state.geo_timezone = None
        request.state.geo_country = None
        request.state.geo_city = None

        try:
            # Get GeoIP service
            geoip_service = self._get_geoip_service(request)
            if not geoip_service:
                logger.debug("GeoIP service not available, skipping geo extraction")
                return await call_next(request)

            # Extract client IP (dev override takes priority)
            client_ip = self.dev_override_ip or extract_client_ip(request)
            if not client_ip:
                logger.debug("No client IP found for request to %s", request.url.path)
                return await call_next(request)

            # Look up geolocation data
            geo_info = geoip_service.get_geo_info(client_ip)
            if geo_info:
                request.state.geo_timezone = geo_info.timezone
                request.state.geo_country = geo_info.country
                request.state.geo_city = geo_info.city

        except Exception:
            # UNEXPECTED ERROR: Log loudly but continue request gracefully
            logger.exception(
                "UNEXPECTED ERROR in GeoIP middleware for %s from IP %s - geo fields set to None",
                request.url.path,
                self.dev_override_ip or extract_client_ip(request) or "unknown",
            )
            # Geo fields already set to None above

        # Continue processing the request
        return await call_next(request)
