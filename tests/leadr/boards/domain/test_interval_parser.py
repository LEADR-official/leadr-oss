"""Tests for PostgreSQL interval parsing."""

import pytest
from dateutil.relativedelta import relativedelta

from leadr.boards.domain.interval_parser import parse_interval


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
