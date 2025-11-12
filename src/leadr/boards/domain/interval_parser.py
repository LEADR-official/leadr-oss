"""Utilities for parsing PostgreSQL interval syntax."""

from datetime import timedelta


def parse_interval_to_timedelta(interval_string: str) -> timedelta:
    """Parse PostgreSQL interval syntax to Python timedelta.

    Supports formats like:
    - "7 days"
    - "1 week"
    - "2 hours"
    - "30 minutes"

    Args:
        interval_string: PostgreSQL interval syntax string.

    Returns:
        Equivalent Python timedelta.

    Raises:
        ValueError: If interval format is invalid or unsupported.

    Example:
        >>> parse_interval_to_timedelta("7 days")
        timedelta(days=7)
        >>> parse_interval_to_timedelta("1 week")
        timedelta(weeks=1)
    """
    parts = interval_string.strip().split()

    if len(parts) < 2:
        raise ValueError(
            f"Invalid interval format: '{interval_string}'. "
            "Expected format: 'N unit' (e.g., '7 days', '1 week')"
        )

    try:
        amount = int(parts[0])
    except ValueError as e:
        raise ValueError(f"Invalid amount in interval '{interval_string}': {parts[0]}") from e

    unit = parts[1].lower().rstrip("s")  # Remove trailing 's'

    if unit == "day":
        return timedelta(days=amount)
    elif unit == "week":
        return timedelta(weeks=amount)
    elif unit == "hour":
        return timedelta(hours=amount)
    elif unit == "minute":
        return timedelta(minutes=amount)
    elif unit == "second":
        return timedelta(seconds=amount)
    else:
        raise ValueError(
            f"Unsupported time unit in interval '{interval_string}': {unit}. "
            "Supported units: day, week, hour, minute, second"
        )
