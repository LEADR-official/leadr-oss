"""Slug generation utilities.

Provides utilities for generating URL-friendly slugs from text,
with support for collision handling and uniqueness constraints.
"""

import re
import unicodedata
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


def generate_slug(text: str, max_length: int = 50) -> str:
    """Generate a URL-friendly slug from text.

    Converts text to lowercase, replaces spaces with hyphens, removes special
    characters, and handles unicode by transliterating accented characters.

    Args:
        text: The text to convert to a slug
        max_length: Maximum length of the generated slug (default: 50)

    Returns:
        A lowercase slug with alphanumeric characters, hyphens, and underscores

    Raises:
        ValueError: If text is empty or contains no valid characters after processing

    Examples:
        >>> generate_slug("Hello World")
        "hello-world"
        >>> generate_slug("Café Board")
        "cafe-board"
        >>> generate_slug("Speed-Run 2024")
        "speed-run-2024"
    """
    if not text or not text.strip():
        raise ValueError("Cannot generate slug from empty text")

    # Normalize unicode characters (NFD = decompose, then remove combining marks)
    # This converts é -> e, ñ -> n, etc.
    normalized = unicodedata.normalize("NFD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")

    # Convert to lowercase
    slug = ascii_text.lower()

    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)

    # Remove all characters except alphanumeric and hyphens
    slug = re.sub(r"[^a-z0-9-]+", "", slug)

    # Replace consecutive hyphens with single hyphen
    slug = re.sub(r"-+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    # Validate that we have something left
    if not slug:
        raise ValueError("Cannot generate slug from text with no valid characters")

    # Truncate to max length, ensuring we don't cut in the middle of a word
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")

    return slug


async def generate_unique_slug_with_retry(
    base_text: str,
    check_exists: Callable[[str], Awaitable[bool]],
    max_retries: int = 10,
    max_length: int = 50,
) -> str:
    """Generate a unique slug with collision handling.

    Attempts to generate a unique slug from the base text. If a collision is
    detected (slug already exists), appends a numeric suffix and retries.

    Args:
        base_text: The text to convert to a slug
        check_exists: Async function that returns True if slug already exists
        max_retries: Maximum number of collision retries (default: 10)
        max_length: Maximum length of the generated slug (default: 50)

    Returns:
        A unique slug that doesn't collide with existing slugs

    Raises:
        ValueError: If unable to generate unique slug after max_retries
        ValueError: If base_text is invalid for slug generation

    Examples:
        >>> async def check(slug: str) -> bool:
        ...     return slug in ["my-board", "my-board-2"]
        >>> await generate_unique_slug_with_retry("My Board", check)
        "my-board-3"
    """
    # Generate base slug
    base_slug = generate_slug(base_text, max_length=max_length)

    # Try base slug first
    if not await check_exists(base_slug):
        return base_slug

    # Try with numeric suffixes
    for i in range(2, max_retries + 2):
        suffix = f"-{i}"
        # Ensure total length doesn't exceed max_length
        truncated_base = base_slug[: max_length - len(suffix)]
        candidate = f"{truncated_base}{suffix}"

        if not await check_exists(candidate):
            return candidate

    raise ValueError(
        f"Unable to generate unique slug after {max_retries} retries for base text: {base_text}"
    )
