#!/usr/bin/env python3
"""Manual script to create superadmin user.

This script can be run manually to create a superadmin user and associated account
if one doesn't already exist. It uses the same bootstrap logic as the automatic
startup process.

Usage:
    uv run python scripts/create_superadmin.py

Environment Variables (configured in .env or .env.test):
    SUPERADMIN_ACCOUNT_NAME: Name of the system account (default: "LEADR")
    SUPERADMIN_ACCOUNT_SLUG: URL slug for the system account (default: "leadr")
    SUPERADMIN_EMAIL: Email for the superadmin user (default: "admin@leadr.gg")
    SUPERADMIN_DISPLAY_NAME: Display name for superadmin (default: "LEADR Admin")
    SUPERADMIN_API_KEY: API key value for authentication (REQUIRED)
    SUPERADMIN_API_KEY_NAME: Display name for the API key (default: "Superadmin Key")
"""

import asyncio
import logging
import sys

from leadr.auth.bootstrap import ensure_superadmin_exists
from leadr.common.database import async_session_factory
from leadr.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Create superadmin user if none exists."""
    logger.info("Starting superadmin creation script")
    logger.info("Environment: %s", settings.ENV)
    logger.info("Account name: %s", settings.SUPERADMIN_ACCOUNT_NAME)
    logger.info("Account slug: %s", settings.SUPERADMIN_ACCOUNT_SLUG)
    logger.info("Email: %s", settings.SUPERADMIN_EMAIL)
    logger.info("Display name: %s", settings.SUPERADMIN_DISPLAY_NAME)

    try:
        async with async_session_factory() as session:
            await ensure_superadmin_exists(session)

        logger.info("Superadmin creation completed successfully")
        logger.info("")
        logger.info("=" * 70)
        logger.info("SUPERADMIN DETAILS")
        logger.info("=" * 70)
        logger.info(
            "Account: %s (%s)", settings.SUPERADMIN_ACCOUNT_NAME, settings.SUPERADMIN_ACCOUNT_SLUG
        )
        logger.info("Email: %s", settings.SUPERADMIN_EMAIL)
        logger.info("Display Name: %s", settings.SUPERADMIN_DISPLAY_NAME)
        logger.info("API Key: %s...", settings.SUPERADMIN_API_KEY[:20])
        logger.info("=" * 70)
        logger.info("")
        logger.info("Use the API key above for authentication with the admin API.")
        logger.info("Set the 'leadr-api-key' header to this value in your requests.")

    except Exception as e:
        logger.exception("Failed to create superadmin: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
