"""Utility for generating unique short codes for boards.

Short codes are used for direct board sharing (e.g., example.com/board/ABC123XY).
They must be globally unique across all boards.
"""

import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.boards.services.repositories import BoardRepository

# Charset: uppercase letters + digits, excluding ambiguous characters
# Excludes: 0 (zero), O (letter O), 1 (one), I (letter I), l (lowercase L)
# This leaves us with 32 characters for better readability
CHARSET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
CODE_LENGTH = 8


def generate_short_code() -> str:
    """Generate a random 8-character alphanumeric short code.

    Uses cryptographically strong random number generator for security.
    Excludes ambiguous characters (0/O, 1/I/l) for better readability.

    Returns:
        8-character uppercase alphanumeric code (e.g., 'A7B3X9K2').

    Example:
        >>> code = generate_short_code()
        >>> len(code)
        8
        >>> code.isupper()
        True
    """
    return "".join(secrets.choice(CHARSET) for _ in range(CODE_LENGTH))


async def generate_unique_short_code(session: AsyncSession, max_retries: int = 10) -> str:
    """Generate a globally unique short code with collision retry logic.

    Generates random codes and checks database for uniqueness. If a collision
    is detected, retries up to max_retries times before raising an error.

    With 32^8 = 1.1 trillion possible codes, collisions are extremely rare
    until we have millions of boards.

    Args:
        session: Database session for uniqueness checking.
        max_retries: Maximum number of generation attempts (default 10).

    Returns:
        Unique 8-character short code guaranteed not to exist in database.

    Raises:
        RuntimeError: If unable to generate unique code within max_retries attempts.

    Example:
        >>> code = await generate_unique_short_code(session)
        >>> # Code is guaranteed to be unique in database
    """
    repository = BoardRepository(session)

    for _attempt in range(max_retries):
        code = generate_short_code()

        # Check if code already exists
        existing = await repository.get_by_short_code(code)
        if existing is None:
            return code

        # Collision detected, will retry

    # Exhausted all retries
    raise RuntimeError(
        f"Failed to generate unique short code after {max_retries} attempts. "
        "This is extremely unlikely and may indicate a database issue."
    )
