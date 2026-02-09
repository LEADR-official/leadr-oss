"""Utilities for parsing PostgreSQL interval syntax."""

from dateutil.relativedelta import relativedelta


def parse_interval(interval_string: str) -> relativedelta:
    """Parse PostgreSQL interval syntax to Python relativedelta.

    Supports formats like:
    - "7 days"
    - "1 week"
    - "1 month"
    - "1 year"
    - "2 hours"

    Args:
        interval_string: PostgreSQL interval syntax string.

    Returns:
        Equivalent Python relativedelta.

    Raises:
        ValueError: If interval format is invalid or unsupported.

    Example:
        >>> parse_interval("7 days")
        relativedelta(days=7)
        >>> parse_interval("1 month")
        relativedelta(months=1)
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
        return relativedelta(days=amount)
    elif unit == "week":
        return relativedelta(weeks=amount)
    elif unit == "month":
        return relativedelta(months=amount)
    elif unit == "year":
        return relativedelta(years=amount)
    elif unit == "hour":
        return relativedelta(hours=amount)
    else:
        raise ValueError(
            f"Unsupported time unit in interval '{interval_string}': {unit}. "
            "Supported units: day, week, month, year, hour"
        )
