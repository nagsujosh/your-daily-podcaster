from datetime import datetime, timedelta
from typing import Optional

import pytz


def get_yesterday_date() -> str:
    """Get yesterday's date in YYYY-MM-DD format."""
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")


def get_today_date() -> str:
    """Get today's date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")


def format_date_for_rss(date_str: str) -> str:
    """Format date for RSS feeds (YYYY-MM-DD format)."""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        return date_str


def get_date_range(days_back: int = 1) -> tuple[str, str]:
    """Get a date range for the last N days."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    return (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))


def parse_rss_date(date_str: str) -> Optional[str]:
    """Parse RSS date format and return YYYY-MM-DD."""
    try:
        # RSS feeds return dates in RFC 2822 format like "Mon, 28 Jul 2025 09:00:06 GMT"
        try:
            date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            pass

        # Try other common formats as fallback
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None
    except Exception:
        return None


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat()


def is_recent_article(date_str: str, days_threshold: int = 2) -> bool:
    """Check if an article is recent (within N days)."""
    try:
        article_date = datetime.strptime(date_str, "%Y-%m-%d")
        threshold_date = datetime.now() - timedelta(days=days_threshold)
        return article_date >= threshold_date
    except ValueError:
        return False


def format_duration(seconds: int) -> str:
    """Format duration in seconds to HH:MM:SS format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def get_timezone_aware_datetime(timezone: str = "UTC") -> datetime:
    """Get current datetime in specified timezone."""
    tz = pytz.timezone(timezone)
    return datetime.now(tz)
