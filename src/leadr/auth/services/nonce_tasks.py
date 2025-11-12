"""Background tasks for nonce cleanup.

Contains tasks for:
- Cleaning up expired nonces to prevent database bloat
"""

import logging

from sqlalchemy.exc import DBAPIError, OperationalError

from leadr.auth.services.nonce_service import NonceService
from leadr.common.database import get_db

logger = logging.getLogger(__name__)


async def cleanup_expired_nonces() -> None:
    """Clean up expired pending nonces.

    Deletes nonces that are:
    - Status: PENDING (unused)
    - Expired before current time

    Used and expired nonces are kept for audit purposes.

    This task is designed to be called periodically (e.g., every hour).
    """
    logger.debug("Checking for expired nonces to clean up...")

    # Get database session
    async for session in get_db():
        # Create nonce service
        nonce_service = NonceService(session)

        # Clean up expired nonces - fail fast on database errors
        try:
            deleted_count = await nonce_service.cleanup_expired_nonces(older_than_hours=0)
        except (OperationalError, DBAPIError) as e:
            logger.error("Database error cleaning up expired nonces: %s", e)
            return
        except Exception:
            logger.exception("Unexpected error cleaning up expired nonces")
            return

        if deleted_count > 0:
            logger.info("Successfully cleaned up %d expired nonces", deleted_count)
        else:
            logger.debug("No expired nonces to clean up")
