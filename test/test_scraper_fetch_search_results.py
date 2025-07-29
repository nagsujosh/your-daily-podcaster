#!/usr/bin/env python3
"""
Unit tests for yourdaily.scraper.fetch_search_results module.
"""

import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import pytest

from yourdaily.scraper.fetch_search_results import NewsFetcher


class TestNewsFetcher:
    """Test cases for NewsFetcher class."""

    @pytest.fixture
    def temp_db_paths(self):
        """Create temporary database file paths for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            search_db = os.path.join(temp_dir, "test_search.db")
            article_db = os.path.join(temp_dir, "test_articles.db")
            yield search_db, article_db

    @pytest.fixture
    def mock_env_vars(self, temp_db_paths):
        """Mock environment variables."""
        search_db, article_db = temp_db_paths
        with patch.dict(
            os.environ, {"SEARCH_DB_PATH": search_db, "ARTICLE_DB_PATH": article_db}
        ):
            yield

    @patch("yourdaily.scraper.fetch_search_results.DatabaseManager")
    @patch("yourdaily.scraper.fetch_search_results.load_dotenv")
    def test_init(self, mock_load_dotenv, mock_db_manager, mock_env_vars):
        """Test NewsFetcher initialization."""
        fetcher = NewsFetcher()

        mock_load_dotenv.assert_called_once()
        mock_db_manager.assert_called_once()

        assert fetcher.base_rss_url == "https://news.google.com/rss/search"
        assert fetcher.rss_params == {"hl": "en-US", "gl": "US", "ceid": "US:en"}
        assert hasattr(fetcher, "session")

    def test_load_topics_file_not_found(self):
        """Test load_topics when Topics.md file doesn't exist."""
        with patch("yourdaily.scraper.fetch_search_results.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            fetcher = NewsFetcher()
            topics = fetcher.load_topics()

            assert topics == []

    def test_load_topics_success(self):
        """Test successful loading of topics from Topics.md."""
        topics_content = """---
title: Topics
---

# Daily Topics

- Technology
- "Business News"
- Science
- Health
"""

        with patch("yourdaily.scraper.fetch_search_results.Path") as mock_path, patch(
            "builtins.open", mock_open(read_data=topics_content)
        ):
            mock_path.return_value.exists.return_value = True

            fetcher = NewsFetcher()
            topics = fetcher.load_topics()

            expected_topics = ["Technology", "Business News", "Science", "Health"]
            assert topics == expected_topics

    def test_load_topics_with_quotes(self):
        """Test loading topics that have quotes."""
        topics_content = """
- "Artificial Intelligence"
- 'Machine Learning'
- Climate Change
"""

        with patch("yourdaily.scraper.fetch_search_results.Path") as mock_path, patch(
            "builtins.open", mock_open(read_data=topics_content)
        ):
            mock_path.return_value.exists.return_value = True

            fetcher = NewsFetcher()
            topics = fetcher.load_topics()

            expected_topics = [
                "Artificial Intelligence",
                "Machine Learning",
                "Climate Change",
            ]
            assert topics == expected_topics

    def test_load_topics_error_handling(self):
        """Test load_topics error handling."""
        with patch("yourdaily.scraper.fetch_search_results.Path") as mock_path, patch(
            "builtins.open", side_effect=IOError("File error")
        ):
            mock_path.return_value.exists.return_value = True

            fetcher = NewsFetcher()
            topics = fetcher.load_topics()

            assert topics == []

    def test_parse_rss_date_success(self):
        """Test successful RSS date parsing."""
        fetcher = NewsFetcher()

        rss_date = "Mon, 28 Jul 2025 09:00:06 GMT"
        result = fetcher.parse_rss_date(rss_date)

        assert result == "2025-07-28"

    def test_parse_rss_date_invalid(self):
        """Test RSS date parsing with invalid format."""
        fetcher = NewsFetcher()

        invalid_date = "invalid-date-format"
        result = fetcher.parse_rss_date(invalid_date)

        assert result == ""

    def test_build_rss_url(self):
        """Test RSS URL building."""
        fetcher = NewsFetcher()

        topic = "artificial intelligence"
        url = fetcher.build_rss_url(topic)

        expected_base = "https://news.google.com/rss/search?q=artificial%20intelligence"
        assert expected_base in url
        assert "hl=en-US" in url
        assert "gl=US" in url
        assert "ceid=US:en" in url

    @patch("yourdaily.scraper.fetch_search_results.feedparser")
    @patch("yourdaily.scraper.fetch_search_results.get_yesterday_date")
    def test_search_topic_success(self, mock_yesterday, mock_feedparser):
        """Test successful topic search."""
        mock_yesterday.return_value = "2024-01-15"

        # Mock RSS feed response
        mock_entry = MagicMock()
        mock_entry.title = "Test Article"
        mock_entry.link = "https://example.com/article"
        mock_entry.published = "Mon, 15 Jan 2024 09:00:06 GMT"
        mock_entry.source.title = "Test Source"

        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]
        mock_feedparser.parse.return_value = mock_feed

        # Mock requests session
        mock_response = MagicMock()
        mock_response.content = "mock_content"

        fetcher = NewsFetcher()
        fetcher.session.get = MagicMock(return_value=mock_response)

        with patch.object(fetcher, "parse_rss_date", return_value="2024-01-15"):
            articles = fetcher.search_topic("Technology")

        assert len(articles) == 1
        assert articles[0]["title"] == "Test Article"
        assert articles[0]["topic"] == "Technology"

    @patch("yourdaily.scraper.fetch_search_results.get_yesterday_date")
    def test_search_topic_no_entries(self, mock_yesterday):
        """Test topic search with no RSS entries."""
        mock_yesterday.return_value = "2024-01-15"

        # Mock empty RSS feed
        with patch(
            "yourdaily.scraper.fetch_search_results.feedparser"
        ) as mock_feedparser:
            mock_feed = MagicMock()
            mock_feed.entries = []
            mock_feedparser.parse.return_value = mock_feed

            mock_response = MagicMock()
            mock_response.content = "mock_content"

            fetcher = NewsFetcher()
            fetcher.session.get = MagicMock(return_value=mock_response)

            articles = fetcher.search_topic("Technology")

            assert articles == []

    def test_search_topic_request_error(self):
        """Test topic search with request error."""
        fetcher = NewsFetcher()
        fetcher.session.get = MagicMock(side_effect=Exception("Network error"))

        articles = fetcher.search_topic("Technology")

        assert articles == []

    @patch("yourdaily.scraper.fetch_search_results.get_yesterday_date")
    def test_search_topic_date_filtering(self, mock_yesterday):
        """Test that only yesterday's articles are included."""
        mock_yesterday.return_value = "2024-01-15"

        # Mock RSS entries with different dates
        mock_entry_yesterday = MagicMock()
        mock_entry_yesterday.title = "Yesterday Article"
        mock_entry_yesterday.link = "https://example.com/yesterday"
        mock_entry_yesterday.published = "Mon, 15 Jan 2024 09:00:06 GMT"

        mock_entry_today = MagicMock()
        mock_entry_today.title = "Today Article"
        mock_entry_today.link = "https://example.com/today"
        mock_entry_today.published = "Tue, 16 Jan 2024 09:00:06 GMT"

        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry_yesterday, mock_entry_today]

        with patch(
            "yourdaily.scraper.fetch_search_results.feedparser"
        ) as mock_feedparser:
            mock_feedparser.parse.return_value = mock_feed

            mock_response = MagicMock()
            fetcher = NewsFetcher()
            fetcher.session.get = MagicMock(return_value=mock_response)

            with patch.object(fetcher, "parse_rss_date") as mock_parse_date:
                # Return different dates for different entries
                mock_parse_date.side_effect = lambda date: {
                    "Mon, 15 Jan 2024 09:00:06 GMT": "2024-01-15",
                    "Tue, 16 Jan 2024 09:00:06 GMT": "2024-01-16",
                }[date]

                articles = fetcher.search_topic("Technology")

        # Should only include yesterday's article
        assert len(articles) == 1
        assert articles[0]["title"] == "Yesterday Article"

    def test_store_articles_success(self):
        """Test successful article storage."""
        mock_db = MagicMock()
        mock_db.article_exists.return_value = False
        mock_db.insert_search_result.return_value = True

        fetcher = NewsFetcher()
        fetcher.db = mock_db

        articles = [
            {
                "topic": "Tech",
                "title": "Test Article 1",
                "url": "https://example.com/1",
                "source": "Source 1",
                "rss_date": "2024-01-15",
                "published_date": "2024-01-15",
            },
            {
                "topic": "Tech",
                "title": "Test Article 2",
                "url": "https://example.com/2",
                "source": "Source 2",
                "rss_date": "2024-01-15",
                "published_date": "2024-01-15",
            },
        ]

        stored_count = fetcher.store_articles(articles)

        assert stored_count == 2
        assert mock_db.insert_search_result.call_count == 2

    def test_store_articles_with_duplicates(self):
        """Test article storage with duplicates."""
        mock_db = MagicMock()
        # First article is new, second is duplicate
        mock_db.article_exists.side_effect = [False, True]
        mock_db.insert_search_result.return_value = True

        fetcher = NewsFetcher()
        fetcher.db = mock_db

        articles = [
            {
                "topic": "Tech",
                "title": "New Article",
                "url": "https://example.com/new",
                "source": "Source",
                "rss_date": "2024-01-15",
                "published_date": "2024-01-15",
            },
            {
                "topic": "Tech",
                "title": "Duplicate Article",
                "url": "https://example.com/duplicate",
                "source": "Source",
                "rss_date": "2024-01-15",
                "published_date": "2024-01-15",
            },
        ]

        stored_count = fetcher.store_articles(articles)

        assert stored_count == 1  # Only one new article stored
        assert mock_db.insert_search_result.call_count == 1

    def test_store_articles_database_error(self):
        """Test article storage with database errors."""
        mock_db = MagicMock()
        mock_db.article_exists.return_value = False
        mock_db.insert_search_result.side_effect = Exception("DB Error")

        fetcher = NewsFetcher()
        fetcher.db = mock_db

        articles = [
            {
                "topic": "Tech",
                "title": "Test Article",
                "url": "https://example.com/test",
                "source": "Source",
                "rss_date": "2024-01-15",
                "published_date": "2024-01-15",
            }
        ]

        stored_count = fetcher.store_articles(articles)

        assert stored_count == 0

    def test_run_no_topics(self):
        """Test run method when no topics are found."""
        fetcher = NewsFetcher()

        with patch.object(fetcher, "load_topics", return_value=[]):
            result = fetcher.run()

        assert result["success"] is False
        assert "No topics found" in result["error"]

    def test_run_success(self):
        """Test successful run of the fetcher."""
        mock_articles = [
            {
                "topic": "Tech",
                "title": "Article 1",
                "url": "https://example.com/1",
                "source": "Source",
                "rss_date": "2024-01-15",
                "published_date": "2024-01-15",
            }
        ]

        fetcher = NewsFetcher()

        with patch.object(
            fetcher, "load_topics", return_value=["Technology"]
        ), patch.object(
            fetcher, "search_topic", return_value=mock_articles
        ), patch.object(
            fetcher, "store_articles", return_value=1
        ):
            result = fetcher.run()

        assert result["success"] is True
        assert result["topics_searched"] == 1
        assert result["articles_found"] == 1
        assert result["articles_stored"] == 1

    def test_run_multiple_topics(self):
        """Test run method with multiple topics."""
        mock_articles_tech = [
            {
                "topic": "Tech",
                "title": "Tech Article",
                "url": "https://example.com/tech",
                "source": "Source",
                "rss_date": "2024-01-15",
                "published_date": "2024-01-15",
            }
        ]
        mock_articles_business = [
            {
                "topic": "Business",
                "title": "Business Article",
                "url": "https://example.com/business",
                "source": "Source",
                "rss_date": "2024-01-15",
                "published_date": "2024-01-15",
            }
        ]

        fetcher = NewsFetcher()

        with patch.object(
            fetcher, "load_topics", return_value=["Technology", "Business"]
        ), patch.object(fetcher, "search_topic") as mock_search, patch.object(
            fetcher, "store_articles", return_value=1
        ):
            # Mock different return values for different topics
            mock_search.side_effect = [mock_articles_tech, mock_articles_business]

            result = fetcher.run()

        assert result["success"] is True
        assert result["topics_searched"] == 2
        assert result["articles_found"] == 2
        assert result["articles_stored"] == 2

    @patch("yourdaily.scraper.fetch_search_results.setup_logger")
    @patch("yourdaily.scraper.fetch_search_results.get_logger")
    def test_main_function_success(self, mock_get_logger, mock_setup_logger):
        """Test main function successful execution."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.scraper.fetch_search_results.NewsFetcher"
        ) as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.run.return_value = {
                "success": True,
                "articles_stored": 5,
                "topics_searched": 3,
            }
            mock_fetcher_class.return_value = mock_fetcher

            from yourdaily.scraper.fetch_search_results import main

            # Should not raise SystemExit
            try:
                main()
                success = True
            except SystemExit as e:
                success = e.code == 0

            assert success
            mock_setup_logger.assert_called_once()

    @patch("yourdaily.scraper.fetch_search_results.setup_logger")
    @patch("yourdaily.scraper.fetch_search_results.get_logger")
    @patch("yourdaily.scraper.fetch_search_results.sys.exit")
    def test_main_function_failure(self, mock_exit, mock_get_logger, mock_setup_logger):
        """Test main function with failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.scraper.fetch_search_results.NewsFetcher"
        ) as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.run.return_value = {"success": False, "error": "Test error"}
            mock_fetcher_class.return_value = mock_fetcher

            from yourdaily.scraper.fetch_search_results import main

            main()

            mock_exit.assert_called_with(1)

    @patch("yourdaily.scraper.fetch_search_results.setup_logger")
    @patch("yourdaily.scraper.fetch_search_results.get_logger")
    @patch("yourdaily.scraper.fetch_search_results.sys.exit")
    def test_main_function_exception(
        self, mock_exit, mock_get_logger, mock_setup_logger
    ):
        """Test main function with unexpected exception."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.scraper.fetch_search_results.NewsFetcher"
        ) as mock_fetcher_class:
            mock_fetcher_class.side_effect = Exception("Unexpected error")

            from yourdaily.scraper.fetch_search_results import main

            main()

            mock_exit.assert_called_with(1)
            mock_logger.error.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])
