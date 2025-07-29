#!/usr/bin/env python3
"""
Unit tests for yourdaily.utils.time module.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from yourdaily.utils.time import (
    format_date_for_rss,
    format_duration,
    get_current_timestamp,
    get_date_range,
    get_timezone_aware_datetime,
    get_today_date,
    get_yesterday_date,
    is_recent_article,
    parse_rss_date,
)


class TestTimeUtilities:
    """Test cases for time utility functions."""

    def test_get_yesterday_date(self):
        """Test get_yesterday_date returns correct format."""
        with patch("yourdaily.utils.time.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15)
            mock_datetime.now.return_value = mock_now

            result = get_yesterday_date()
            assert result == "2024-01-14"

    def test_get_today_date(self):
        """Test get_today_date returns correct format."""
        with patch("yourdaily.utils.time.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15)
            mock_datetime.now.return_value = mock_now

            result = get_today_date()
            assert result == "2024-01-15"

    def test_format_date_for_rss_valid_date(self):
        """Test format_date_for_rss with valid date string."""
        result = format_date_for_rss("2024-01-15")
        assert result == "2024-01-15"

    def test_format_date_for_rss_invalid_date(self):
        """Test format_date_for_rss with invalid date string."""
        invalid_date = "invalid-date"
        result = format_date_for_rss(invalid_date)
        assert result == invalid_date  # Should return original string

    def test_get_date_range_default(self):
        """Test get_date_range with default parameters."""
        with patch("yourdaily.utils.time.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15)
            mock_datetime.now.return_value = mock_now

            start_date, end_date = get_date_range()
            assert start_date == "2024-01-14"
            assert end_date == "2024-01-15"

    def test_get_date_range_custom_days(self):
        """Test get_date_range with custom days_back parameter."""
        with patch("yourdaily.utils.time.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15)
            mock_datetime.now.return_value = mock_now

            start_date, end_date = get_date_range(days_back=7)
            assert start_date == "2024-01-08"
            assert end_date == "2024-01-15"

    def test_parse_rss_date_rfc_2822_format(self):
        """Test parse_rss_date with RFC 2822 format."""
        rss_date = "Mon, 28 Jul 2025 09:00:06 GMT"
        result = parse_rss_date(rss_date)
        assert result == "2025-07-28"

    def test_parse_rss_date_iso_format(self):
        """Test parse_rss_date with ISO format."""
        iso_date = "2024-01-15T10:30:00Z"
        result = parse_rss_date(iso_date)
        assert result == "2024-01-15"

    def test_parse_rss_date_iso_with_microseconds(self):
        """Test parse_rss_date with ISO format including microseconds."""
        iso_date = "2024-01-15T10:30:00.123456Z"
        result = parse_rss_date(iso_date)
        assert result == "2024-01-15"

    def test_parse_rss_date_simple_format(self):
        """Test parse_rss_date with simple date format."""
        simple_date = "2024-01-15"
        result = parse_rss_date(simple_date)
        assert result == "2024-01-15"

    def test_parse_rss_date_invalid_format(self):
        """Test parse_rss_date with invalid date format."""
        invalid_date = "invalid-date-format"
        result = parse_rss_date(invalid_date)
        assert result is None

    def test_get_current_timestamp(self):
        """Test get_current_timestamp returns ISO format."""
        with patch("yourdaily.utils.time.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 10, 30, 45)
            mock_datetime.now.return_value = mock_now

            result = get_current_timestamp()
            assert result == "2024-01-15T10:30:45"

    def test_is_recent_article_recent(self):
        """Test is_recent_article with recent date."""
        with patch("yourdaily.utils.time.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strptime.return_value = datetime(2024, 1, 14)

            result = is_recent_article("2024-01-14", days_threshold=2)
            assert result is True

    def test_is_recent_article_old(self):
        """Test is_recent_article with old date."""
        with patch("yourdaily.utils.time.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strptime.return_value = datetime(2024, 1, 10)

            result = is_recent_article("2024-01-10", days_threshold=2)
            assert result is False

    def test_is_recent_article_invalid_date(self):
        """Test is_recent_article with invalid date format."""
        result = is_recent_article("invalid-date")
        assert result is False

    def test_format_duration_with_hours(self):
        """Test format_duration with hours."""
        result = format_duration(3665)  # 1 hour, 1 minute, 5 seconds
        assert result == "01:01:05"

    def test_format_duration_without_hours(self):
        """Test format_duration without hours."""
        result = format_duration(125)  # 2 minutes, 5 seconds
        assert result == "02:05"

    def test_format_duration_zero(self):
        """Test format_duration with zero seconds."""
        result = format_duration(0)
        assert result == "00:00"

    @patch("yourdaily.utils.time.pytz")
    def test_get_timezone_aware_datetime_utc(self, mock_pytz):
        """Test get_timezone_aware_datetime with UTC timezone."""
        mock_tz = MagicMock()
        mock_pytz.timezone.return_value = mock_tz

        with patch("yourdaily.utils.time.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 10, 30, 45)
            mock_datetime.now.return_value = mock_now

            result = get_timezone_aware_datetime("UTC")

            mock_pytz.timezone.assert_called_once_with("UTC")
            mock_datetime.now.assert_called_once_with(mock_tz)
            assert result == mock_now

    @patch("yourdaily.utils.time.pytz")
    def test_get_timezone_aware_datetime_custom_timezone(self, mock_pytz):
        """Test get_timezone_aware_datetime with custom timezone."""
        mock_tz = MagicMock()
        mock_pytz.timezone.return_value = mock_tz

        with patch("yourdaily.utils.time.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 10, 30, 45)
            mock_datetime.now.return_value = mock_now

            result = get_timezone_aware_datetime("US/Eastern")

            mock_pytz.timezone.assert_called_once_with("US/Eastern")
            mock_datetime.now.assert_called_once_with(mock_tz)
            assert result == mock_now


if __name__ == "__main__":
    pytest.main([__file__])
