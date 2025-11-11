"""Tests for PostgreSQL interval parsing."""

from datetime import timedelta

import pytest

from leadr.boards.domain.interval_parser import parse_interval_to_timedelta


class TestParseIntervalToTimedelta:
    """Tests for parse_interval_to_timedelta function."""

    def test_parse_days(self):
        """Test parsing days interval."""
        result = parse_interval_to_timedelta("7 days")
        assert result == timedelta(days=7)

    def test_parse_single_day(self):
        """Test parsing single day interval."""
        result = parse_interval_to_timedelta("1 day")
        assert result == timedelta(days=1)

    def test_parse_weeks(self):
        """Test parsing weeks interval."""
        result = parse_interval_to_timedelta("2 weeks")
        assert result == timedelta(weeks=2)

    def test_parse_single_week(self):
        """Test parsing single week interval."""
        result = parse_interval_to_timedelta("1 week")
        assert result == timedelta(weeks=1)

    def test_parse_hours(self):
        """Test parsing hours interval."""
        result = parse_interval_to_timedelta("24 hours")
        assert result == timedelta(hours=24)

    def test_parse_single_hour(self):
        """Test parsing single hour interval."""
        result = parse_interval_to_timedelta("1 hour")
        assert result == timedelta(hours=1)

    def test_parse_minutes(self):
        """Test parsing minutes interval."""
        result = parse_interval_to_timedelta("30 minutes")
        assert result == timedelta(minutes=30)

    def test_parse_single_minute(self):
        """Test parsing single minute interval."""
        result = parse_interval_to_timedelta("1 minute")
        assert result == timedelta(minutes=1)

    def test_parse_seconds(self):
        """Test parsing seconds interval."""
        result = parse_interval_to_timedelta("60 seconds")
        assert result == timedelta(seconds=60)

    def test_parse_single_second(self):
        """Test parsing single second interval."""
        result = parse_interval_to_timedelta("1 second")
        assert result == timedelta(seconds=1)

    def test_parse_with_extra_whitespace(self):
        """Test parsing with extra whitespace."""
        result = parse_interval_to_timedelta("  7   days  ")
        assert result == timedelta(days=7)

    def test_parse_invalid_format_missing_unit(self):
        """Test error on invalid format with missing unit."""
        with pytest.raises(ValueError, match="Invalid interval format"):
            parse_interval_to_timedelta("7")

    def test_parse_invalid_format_no_parts(self):
        """Test error on empty interval."""
        with pytest.raises(ValueError, match="Invalid interval format"):
            parse_interval_to_timedelta("")

    def test_parse_invalid_amount(self):
        """Test error on non-numeric amount."""
        with pytest.raises(ValueError, match="Invalid amount"):
            parse_interval_to_timedelta("abc days")

    def test_parse_unsupported_unit(self):
        """Test error on unsupported time unit."""
        with pytest.raises(ValueError, match="Unsupported time unit"):
            parse_interval_to_timedelta("1 month")

    def test_parse_large_amount(self):
        """Test parsing large amounts."""
        result = parse_interval_to_timedelta("365 days")
        assert result == timedelta(days=365)

    def test_parse_negative_amount(self):
        """Test parsing negative amounts (allowed by parser)."""
        result = parse_interval_to_timedelta("-7 days")
        assert result == timedelta(days=-7)
