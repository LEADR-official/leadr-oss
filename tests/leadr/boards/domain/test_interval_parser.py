"""Tests for PostgreSQL interval parsing."""

import pytest
from dateutil.relativedelta import relativedelta

from leadr.boards.domain.interval_parser import normalize_interval, parse_interval


class TestParseInterval:
    """Tests for parse_interval function."""

    def test_parse_days(self):
        """Test parsing days interval."""
        result = parse_interval("7 days")
        assert result == relativedelta(days=7)

    def test_parse_single_day(self):
        """Test parsing single day interval."""
        result = parse_interval("1 day")
        assert result == relativedelta(days=1)

    def test_parse_weeks(self):
        """Test parsing weeks interval."""
        result = parse_interval("2 weeks")
        assert result == relativedelta(weeks=2)

    def test_parse_single_week(self):
        """Test parsing single week interval."""
        result = parse_interval("1 week")
        assert result == relativedelta(weeks=1)

    def test_parse_months(self):
        """Test parsing months interval."""
        result = parse_interval("3 months")
        assert result == relativedelta(months=3)

    def test_parse_single_month(self):
        """Test parsing single month interval."""
        result = parse_interval("1 month")
        assert result == relativedelta(months=1)

    def test_parse_years(self):
        """Test parsing years interval."""
        result = parse_interval("2 years")
        assert result == relativedelta(years=2)

    def test_parse_single_year(self):
        """Test parsing single year interval."""
        result = parse_interval("1 year")
        assert result == relativedelta(years=1)

    def test_parse_hours(self):
        """Test parsing hours interval."""
        result = parse_interval("24 hours")
        assert result == relativedelta(hours=24)

    def test_parse_single_hour(self):
        """Test parsing single hour interval."""
        result = parse_interval("1 hour")
        assert result == relativedelta(hours=1)

    def test_parse_minutes(self):
        """Test parsing minutes interval."""
        result = parse_interval("30 minutes")
        assert result == relativedelta(minutes=30)

    def test_parse_single_minute(self):
        """Test parsing single minute interval."""
        result = parse_interval("1 minute")
        assert result == relativedelta(minutes=1)

    def test_parse_seconds(self):
        """Test parsing seconds interval."""
        result = parse_interval("10 seconds")
        assert result == relativedelta(seconds=10)

    def test_parse_single_second(self):
        """Test parsing single second interval."""
        result = parse_interval("1 second")
        assert result == relativedelta(seconds=1)

    def test_parse_with_extra_whitespace(self):
        """Test parsing with extra whitespace."""
        result = parse_interval("  7   days  ")
        assert result == relativedelta(days=7)

    def test_parse_invalid_format_missing_unit(self):
        """Test error on invalid format with missing unit."""
        with pytest.raises(ValueError, match="Invalid interval format"):
            parse_interval("7")

    def test_parse_invalid_format_no_parts(self):
        """Test error on empty interval."""
        with pytest.raises(ValueError, match="Invalid interval format"):
            parse_interval("")

    def test_parse_invalid_amount(self):
        """Test error on non-numeric amount."""
        with pytest.raises(ValueError, match="Invalid amount"):
            parse_interval("abc days")

    def test_parse_unsupported_unit(self):
        """Test error on unsupported time unit."""
        with pytest.raises(ValueError, match="Unsupported time unit"):
            parse_interval("1 fortnight")

    def test_parse_large_amount(self):
        """Test parsing large amounts."""
        result = parse_interval("365 days")
        assert result == relativedelta(days=365)

    def test_parse_negative_amount(self):
        """Test parsing negative amounts (allowed by parser)."""
        result = parse_interval("-7 days")
        assert result == relativedelta(days=-7)

    def test_parse_shorthand_hourly(self):
        """Test parsing 'hourly' shorthand."""
        result = parse_interval("hourly")
        assert result == relativedelta(hours=1)

    def test_parse_shorthand_daily(self):
        """Test parsing 'daily' shorthand."""
        result = parse_interval("daily")
        assert result == relativedelta(days=1)

    def test_parse_shorthand_weekly(self):
        """Test parsing 'weekly' shorthand."""
        result = parse_interval("weekly")
        assert result == relativedelta(days=7)

    def test_parse_shorthand_monthly(self):
        """Test parsing 'monthly' shorthand."""
        result = parse_interval("monthly")
        assert result == relativedelta(months=1)

    def test_parse_shorthand_case_insensitive(self):
        """Test shorthand aliases are case-insensitive."""
        assert parse_interval("Daily") == relativedelta(days=1)
        assert parse_interval("WEEKLY") == relativedelta(days=7)

    def test_parse_shorthand_with_whitespace(self):
        """Test shorthand aliases with surrounding whitespace."""
        result = parse_interval("  daily  ")
        assert result == relativedelta(days=1)


class TestNormalizeInterval:
    """Tests for normalize_interval function."""

    def test_normalize_shorthand_hourly(self):
        assert normalize_interval("hourly") == "1 hour"

    def test_normalize_shorthand_daily(self):
        assert normalize_interval("daily") == "1 day"

    def test_normalize_shorthand_weekly(self):
        assert normalize_interval("weekly") == "7 days"

    def test_normalize_shorthand_monthly(self):
        assert normalize_interval("monthly") == "1 month"

    def test_normalize_passthrough(self):
        """Standard interval syntax passes through unchanged."""
        assert normalize_interval("7 days") == "7 days"
        assert normalize_interval("1 hour") == "1 hour"

    def test_normalize_shorthand_case_insensitive(self):
        assert normalize_interval("Daily") == "1 day"
        assert normalize_interval("MONTHLY") == "1 month"

    def test_normalize_strips_whitespace(self):
        assert normalize_interval("  weekly  ") == "7 days"
        assert normalize_interval("  7 days  ") == "7 days"

    def test_normalize_invalid_raises(self):
        """Invalid intervals still raise ValueError."""
        with pytest.raises(ValueError):
            normalize_interval("")
        with pytest.raises(ValueError):
            normalize_interval("bogus")
