#!/usr/bin/env python3
"""
Unit tests for yourdaily.scraper.scrape_articles module.
"""

import os
import tempfile
from unittest.mock import MagicMock, call, patch
from urllib.parse import urlparse

import pytest

from yourdaily.scraper.scrape_articles import ArticleScraper


class TestArticleScraper:
    """Test cases for ArticleScraper class."""

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

    @patch("yourdaily.scraper.scrape_articles.DatabaseManager")
    @patch("yourdaily.scraper.scrape_articles.load_dotenv")
    def test_init(self, mock_load_dotenv, mock_db_manager, mock_env_vars):
        """Test ArticleScraper initialization."""
        scraper = ArticleScraper()

        mock_load_dotenv.assert_called_once()
        mock_db_manager.assert_called_once()

        assert scraper.request_delay == 2

    def test_get_unprocessed_articles(self):
        """Test getting unprocessed articles."""
        mock_db = MagicMock()
        mock_articles = [{"id": 1, "title": "Test Article"}]
        mock_db.get_unprocessed_articles.return_value = mock_articles

        scraper = ArticleScraper()
        scraper.db = mock_db

        result = scraper.get_unprocessed_articles()

        assert result == mock_articles
        mock_db.get_unprocessed_articles.assert_called_once()

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://example.com/article", True),
            ("http://test.com", True),
            ("ftp://example.com", False),
            ("invalid-url", False),
            ("", False),
            ("example.com", False),
        ],
    )
    def test_is_valid_url(self, url, expected):
        """Test URL validation."""
        scraper = ArticleScraper()
        result = scraper.is_valid_url(url)
        assert result == expected

    @patch("yourdaily.scraper.scrape_articles.BrowserManager")
    def test_resolve_rss_url_to_real_url_google_news(self, mock_browser_manager):
        """Test resolving Google News URL."""
        mock_browser = MagicMock()
        mock_browser.__enter__.return_value = mock_browser
        mock_browser.resolve_google_news_url.return_value = (
            "https://real-news.com/article"
        )
        mock_browser_manager.return_value = mock_browser

        scraper = ArticleScraper()

        google_url = "https://news.google.com/articles/test"
        result = scraper.resolve_rss_url_to_real_url(google_url)

        assert result == "https://real-news.com/article"
        mock_browser.resolve_google_news_url.assert_called_once_with(google_url)

    def test_resolve_rss_url_to_real_url_non_google(self):
        """Test resolving non-Google News URL."""
        scraper = ArticleScraper()

        regular_url = "https://directnews.com/article"
        result = scraper.resolve_rss_url_to_real_url(regular_url)

        assert result == regular_url

    @patch("yourdaily.scraper.scrape_articles.BrowserManager")
    def test_resolve_rss_url_to_real_url_failure(self, mock_browser_manager):
        """Test URL resolution failure."""
        mock_browser = MagicMock()
        mock_browser.__enter__.return_value = mock_browser
        mock_browser.resolve_google_news_url.return_value = None
        mock_browser_manager.return_value = mock_browser

        scraper = ArticleScraper()

        google_url = "https://news.google.com/articles/test"
        result = scraper.resolve_rss_url_to_real_url(google_url)

        assert result is None

    @patch("yourdaily.scraper.scrape_articles.BrowserManager")
    def test_resolve_rss_url_to_real_url_exception(self, mock_browser_manager):
        """Test URL resolution with exception."""
        mock_browser_manager.side_effect = Exception("Browser error")

        scraper = ArticleScraper()

        result = scraper.resolve_rss_url_to_real_url("https://news.google.com/test")

        assert result is None

    @patch("yourdaily.scraper.scrape_articles.BrowserManager")
    def test_fetch_article_content_with_browser_success(self, mock_browser_manager):
        """Test successful content fetching with browser."""
        mock_browser = MagicMock()
        mock_browser.__enter__.return_value = mock_browser
        mock_browser.get_page_content.return_value = (
            "<html><body>Test content</body></html>"
        )
        mock_browser_manager.return_value = mock_browser

        scraper = ArticleScraper()

        result = scraper.fetch_article_content_with_browser("https://example.com")

        assert result == "<html><body>Test content</body></html>"
        mock_browser.get_page_content.assert_called_once_with("https://example.com")

    @patch("yourdaily.scraper.scrape_articles.BrowserManager")
    def test_fetch_article_content_with_browser_no_content(self, mock_browser_manager):
        """Test content fetching when no content is retrieved."""
        mock_browser = MagicMock()
        mock_browser.__enter__.return_value = mock_browser
        mock_browser.get_page_content.return_value = None
        mock_browser_manager.return_value = mock_browser

        scraper = ArticleScraper()

        result = scraper.fetch_article_content_with_browser("https://example.com")

        assert result is None

    @patch("yourdaily.scraper.scrape_articles.BrowserManager")
    def test_fetch_article_content_with_browser_exception(self, mock_browser_manager):
        """Test content fetching with exception."""
        mock_browser_manager.side_effect = Exception("Browser error")

        scraper = ArticleScraper()

        result = scraper.fetch_article_content_with_browser("https://example.com")

        assert result is None

    @patch("yourdaily.scraper.scrape_articles.trafilatura")
    def test_clean_article_content_success(self, mock_trafilatura):
        """Test successful content cleaning."""
        mock_trafilatura.extract.return_value = "This is a long extracted article content that should pass the minimum length requirement for meaningful content."

        scraper = ArticleScraper()

        html_content = "<html><body><p>Article content</p></body></html>"
        result = scraper.clean_article_content(html_content, "https://example.com")

        assert "extracted article content" in result
        mock_trafilatura.extract.assert_called_once()

    @patch("yourdaily.scraper.scrape_articles.trafilatura")
    def test_clean_article_content_no_extraction(self, mock_trafilatura):
        """Test content cleaning when trafilatura returns None."""
        mock_trafilatura.extract.return_value = None

        scraper = ArticleScraper()

        html_content = "<html><body><p>Article content</p></body></html>"
        result = scraper.clean_article_content(html_content, "https://example.com")

        assert result is None

    @patch("yourdaily.scraper.scrape_articles.trafilatura")
    def test_clean_article_content_too_short(self, mock_trafilatura):
        """Test content cleaning when extracted text is too short."""
        mock_trafilatura.extract.return_value = "Short"  # Less than 100 characters

        scraper = ArticleScraper()

        html_content = "<html><body><p>Short content</p></body></html>"
        result = scraper.clean_article_content(html_content, "https://example.com")

        assert result is None

    @patch("yourdaily.scraper.scrape_articles.trafilatura")
    def test_clean_article_content_exception(self, mock_trafilatura):
        """Test content cleaning with exception."""
        mock_trafilatura.extract.side_effect = Exception("Extraction error")

        scraper = ArticleScraper()

        html_content = "<html><body><p>Article content</p></body></html>"
        result = scraper.clean_article_content(html_content, "https://example.com")

        assert result is None

    def test_post_process_text_normal(self):
        """Test post-processing of normal text."""
        scraper = ArticleScraper()

        input_text = "Line 1\n\nLine 2\n   \nLine 3\n\n\n\nLine 4"
        result = scraper.post_process_text(input_text)

        expected = "Line 1\n\nLine 2\n\nLine 3\n\nLine 4"
        assert result == expected

    def test_post_process_text_empty(self):
        """Test post-processing of empty text."""
        scraper = ArticleScraper()

        result = scraper.post_process_text("")
        assert result == ""

    def test_post_process_text_none(self):
        """Test post-processing of None."""
        scraper = ArticleScraper()

        result = scraper.post_process_text(None)
        assert result == ""

    def test_generate_content_hash(self):
        """Test content hash generation."""
        scraper = ArticleScraper()

        content = "Test content for hashing"
        hash1 = scraper.generate_content_hash(content)
        hash2 = scraper.generate_content_hash(content)

        # Same content should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hash length

        # Different content should produce different hash
        different_content = "Different test content"
        hash3 = scraper.generate_content_hash(different_content)
        assert hash1 != hash3

    def test_scrape_article_invalid_rss_url(self):
        """Test scraping article with invalid RSS URL."""
        scraper = ArticleScraper()

        article = {"rss_url": "invalid-url", "title": "Test Article", "real_url": None}

        result = scraper.scrape_article(article)

        assert result is False

    def test_scrape_article_with_existing_real_url(self):
        """Test scraping article that already has real URL."""
        mock_db = MagicMock()
        mock_db.insert_article_data.return_value = True

        scraper = ArticleScraper()
        scraper.db = mock_db

        article = {
            "rss_url": "https://news.google.com/test",
            "title": "Test Article",
            "real_url": "https://real-news.com/article",
        }

        with patch.object(scraper, "is_valid_url", return_value=True), patch.object(
            scraper,
            "fetch_article_content_with_browser",
            return_value="<html>content</html>",
        ), patch.object(
            scraper, "clean_article_content", return_value="Cleaned content"
        ):
            result = scraper.scrape_article(article)

        assert result is True
        mock_db.insert_article_data.assert_called_once()

    def test_scrape_article_url_resolution_failure(self):
        """Test scraping article when URL resolution fails."""
        scraper = ArticleScraper()

        article = {
            "rss_url": "https://news.google.com/test",
            "title": "Test Article",
            "real_url": None,
        }

        with patch.object(scraper, "is_valid_url", return_value=True), patch.object(
            scraper, "resolve_rss_url_to_real_url", return_value=None
        ):
            result = scraper.scrape_article(article)

        assert result is False

    def test_scrape_article_content_fetch_failure(self):
        """Test scraping article when content fetching fails."""
        scraper = ArticleScraper()

        article = {
            "rss_url": "https://news.google.com/test",
            "title": "Test Article",
            "real_url": None,
        }

        with patch.object(scraper, "is_valid_url", return_value=True), patch.object(
            scraper, "resolve_rss_url_to_real_url", return_value="https://real-news.com"
        ), patch.object(
            scraper, "fetch_article_content_with_browser", return_value=None
        ):
            result = scraper.scrape_article(article)

        assert result is False

    def test_scrape_article_cleaning_failure(self):
        """Test scraping article when content cleaning fails."""
        scraper = ArticleScraper()

        article = {
            "rss_url": "https://news.google.com/test",
            "title": "Test Article",
            "real_url": None,
        }

        with patch.object(scraper, "is_valid_url", return_value=True), patch.object(
            scraper, "resolve_rss_url_to_real_url", return_value="https://real-news.com"
        ), patch.object(
            scraper,
            "fetch_article_content_with_browser",
            return_value="<html>content</html>",
        ), patch.object(
            scraper, "clean_article_content", return_value=None
        ):
            result = scraper.scrape_article(article)

        assert result is False

    def test_scrape_article_database_error(self):
        """Test scraping article with database insertion error."""
        mock_db = MagicMock()
        mock_db.insert_article_data.return_value = False

        scraper = ArticleScraper()
        scraper.db = mock_db

        article = {
            "rss_url": "https://news.google.com/test",
            "title": "Test Article",
            "real_url": "https://real-news.com/article",
        }

        with patch.object(scraper, "is_valid_url", return_value=True), patch.object(
            scraper,
            "fetch_article_content_with_browser",
            return_value="<html>content</html>",
        ), patch.object(
            scraper, "clean_article_content", return_value="Cleaned content"
        ):
            result = scraper.scrape_article(article)

        assert result is False

    def test_scrape_article_complete_success(self):
        """Test complete successful article scraping."""
        mock_db = MagicMock()
        mock_db.update_real_url.return_value = True
        mock_db.insert_article_data.return_value = True

        scraper = ArticleScraper()
        scraper.db = mock_db

        article = {
            "rss_url": "https://news.google.com/test",
            "title": "Test Article",
            "real_url": None,
        }

        with patch.object(scraper, "is_valid_url", return_value=True), patch.object(
            scraper, "resolve_rss_url_to_real_url", return_value="https://real-news.com"
        ), patch.object(
            scraper,
            "fetch_article_content_with_browser",
            return_value="<html>content</html>",
        ), patch.object(
            scraper, "clean_article_content", return_value="Cleaned content"
        ):
            result = scraper.scrape_article(article)

        assert result is True
        mock_db.update_real_url.assert_called_once_with(
            "https://news.google.com/test", "https://real-news.com"
        )
        mock_db.insert_article_data.assert_called_once()

    def test_run_no_articles(self):
        """Test run method when no unprocessed articles exist."""
        scraper = ArticleScraper()

        with patch.object(scraper, "get_unprocessed_articles", return_value=[]):
            result = scraper.run()

        assert result["success"] is True
        assert result["articles_processed"] == 0
        assert result["articles_successful"] == 0

    @patch("yourdaily.scraper.scrape_articles.time.sleep")
    def test_run_with_articles_success(self, mock_sleep):
        """Test successful run with articles."""
        mock_articles = [
            {"id": 1, "title": "Article 1", "rss_url": "https://example.com/1"},
            {"id": 2, "title": "Article 2", "rss_url": "https://example.com/2"},
        ]

        scraper = ArticleScraper()

        with patch.object(
            scraper, "get_unprocessed_articles", return_value=mock_articles
        ), patch.object(scraper, "scrape_article", return_value=True):
            result = scraper.run()

        assert result["success"] is True
        assert result["articles_processed"] == 2
        assert result["articles_successful"] == 2
        assert result["articles_failed"] == 0

        # Check rate limiting was applied (sleep called once, not after last article)
        mock_sleep.assert_called_once_with(2)

    @patch("yourdaily.scraper.scrape_articles.time.sleep")
    def test_run_with_mixed_results(self, mock_sleep):
        """Test run with some successful and some failed articles."""
        mock_articles = [
            {"id": 1, "title": "Article 1", "rss_url": "https://example.com/1"},
            {"id": 2, "title": "Article 2", "rss_url": "https://example.com/2"},
            {"id": 3, "title": "Article 3", "rss_url": "https://example.com/3"},
        ]

        scraper = ArticleScraper()

        with patch.object(
            scraper, "get_unprocessed_articles", return_value=mock_articles
        ), patch.object(scraper, "scrape_article") as mock_scrape:
            # First succeeds, second fails, third succeeds
            mock_scrape.side_effect = [True, False, True]

            result = scraper.run()

        assert result["success"] is True
        assert result["articles_processed"] == 3
        assert result["articles_successful"] == 2
        assert result["articles_failed"] == 1

    @patch("yourdaily.scraper.scrape_articles.time.sleep")
    def test_run_with_exception(self, mock_sleep):
        """Test run method when scrape_article raises exception."""
        mock_articles = [
            {"id": 1, "title": "Article 1", "rss_url": "https://example.com/1"}
        ]

        scraper = ArticleScraper()

        with patch.object(
            scraper, "get_unprocessed_articles", return_value=mock_articles
        ), patch.object(
            scraper, "scrape_article", side_effect=Exception("Processing error")
        ):
            result = scraper.run()

        assert result["success"] is True
        assert result["articles_processed"] == 1
        assert result["articles_successful"] == 0
        assert result["articles_failed"] == 1

    @patch("yourdaily.scraper.scrape_articles.setup_logger")
    @patch("yourdaily.scraper.scrape_articles.get_logger")
    def test_main_function_success(self, mock_get_logger, mock_setup_logger):
        """Test main function successful execution."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.scraper.scrape_articles.ArticleScraper"
        ) as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.run.return_value = {
                "success": True,
                "articles_successful": 3,
                "articles_processed": 3,
            }
            mock_scraper_class.return_value = mock_scraper

            from yourdaily.scraper.scrape_articles import main

            # Should not raise SystemExit
            try:
                main()
                success = True
            except SystemExit as e:
                success = e.code == 0

            assert success
            mock_setup_logger.assert_called_once()

    @patch("yourdaily.scraper.scrape_articles.setup_logger")
    @patch("yourdaily.scraper.scrape_articles.get_logger")
    @patch("yourdaily.scraper.scrape_articles.sys.exit")
    def test_main_function_failure(self, mock_exit, mock_get_logger, mock_setup_logger):
        """Test main function with scraper failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.scraper.scrape_articles.ArticleScraper"
        ) as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper.run.return_value = {"success": False}
            mock_scraper_class.return_value = mock_scraper

            from yourdaily.scraper.scrape_articles import main

            main()

            mock_exit.assert_called_with(1)

    @patch("yourdaily.scraper.scrape_articles.setup_logger")
    @patch("yourdaily.scraper.scrape_articles.get_logger")
    @patch("yourdaily.scraper.scrape_articles.sys.exit")
    def test_main_function_exception(
        self, mock_exit, mock_get_logger, mock_setup_logger
    ):
        """Test main function with unexpected exception."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.scraper.scrape_articles.ArticleScraper"
        ) as mock_scraper_class:
            mock_scraper_class.side_effect = Exception("Unexpected error")

            from yourdaily.scraper.scrape_articles import main

            main()

            mock_exit.assert_called_with(1)
            mock_logger.error.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])
