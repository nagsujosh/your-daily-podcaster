"""
Your Daily Podcaster - AI-powered automated daily podcast generator

A Python package that creates personalized audio news digests by:
1. Fetching news articles from Google News RSS feeds
2. Scraping and summarizing content
3. Generating audio using Google Cloud TTS
4. Publishing to Spotify
"""

__version__ = "1.0.0"
__author__ = "Sujosh Nag"
__email__ = "nagsujosh2004@gmail.com"

from .utils.db import DatabaseManager

# Import main components for easy access
from .utils.logger import get_logger, setup_logger
from .utils.time import (
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

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    # Logger utilities
    "get_logger",
    "setup_logger",
    # Database utilities
    "DatabaseManager",
    # Time utilities
    "get_yesterday_date",
    "get_today_date",
    "format_date_for_rss",
    "get_date_range",
    "parse_rss_date",
    "get_current_timestamp",
    "is_recent_article",
    "format_duration",
    "get_timezone_aware_datetime",
]
