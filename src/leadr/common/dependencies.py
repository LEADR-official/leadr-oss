"""Shared FastAPI dependencies for the application."""

import logging
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.database import get_db
from leadr.common.geoip import GeoInfo
from leadr.common.utils.ip import extract_client_ip
from leadr.config import settings

logger = logging.getLogger(__name__)

# Type alias for async database session dependency
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


async def get_geo_info(request: Request) -> GeoInfo:
    """FastAPI dependency to get GeoIP info for the request.

    This dependency performs GeoIP lookup for the client's IP address. It's
    designed to be used on specific endpoints (like score submissions) rather
    than globally as middleware.

    The dependency gracefully handles failures - if GeoIP lookup fails for any
    reason, it returns a GeoInfo with all None fields.

    Args:
        request: The incoming FastAPI request.

    Returns:
        GeoInfo with timezone, country, and city (all may be None).

    Example:
        @router.post("/scores")
        async def submit_score(geo: GeoInfoDep):
            timezone = geo.timezone
            country = geo.country
            city = geo.city
    """
    # Default empty result
    empty_result = GeoInfo(timezone=None, country=None, city=None)

    try:
        # Get GeoIP service from app state
        geoip_service = getattr(request.app.state, "geoip_service", None)
        if geoip_service is None:
            logger.debug("GeoIP service not available, skipping geo extraction")
            return empty_result

        # Extract client IP (dev override takes priority)
        client_ip = settings.DEV_OVERRIDE_IP or extract_client_ip(request)
        if not client_ip:
            logger.debug("No client IP found for request to %s", request.url.path)
            return empty_result

        # Look up geolocation data
        geo_info = geoip_service.get_geo_info(client_ip)
        if geo_info is None:
            return empty_result

        return geo_info

    except Exception:
        # DELIBERATE CATCHALL: Log loudly but continue request gracefully
        logger.exception(
            "UNEXPECTED ERROR in GeoIP lookup for %s - geo fields set to None",
            request.url.path,
        )
        return empty_result


# Type alias for GeoInfo dependency injection
GeoInfoDep = Annotated[GeoInfo, Depends(get_geo_info)]
