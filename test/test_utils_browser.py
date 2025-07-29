#!/usr/bin/env python3
"""
Unit tests for yourdaily.utils.browser module.
"""

from unittest.mock import MagicMock, call, patch

import pytest
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options

from yourdaily.utils.browser import (
    BrowserManager,
    fetch_article_content_with_browser,
    resolve_google_news_url,
)


class TestBrowserManager:
    """Test cases for BrowserManager class."""

    def test_init_default_parameters(self):
        """Test BrowserManager initialization with default parameters."""
        browser = BrowserManager()

        assert browser.headless is True
        assert browser.timeout == 30
        assert browser.driver is None

    def test_init_custom_parameters(self):
        """Test BrowserManager initialization with custom parameters."""
        browser = BrowserManager(headless=False, timeout=60)

        assert browser.headless is False
        assert browser.timeout == 60
        assert browser.driver is None

    @patch("yourdaily.utils.browser.webdriver.Chrome")
    @patch("yourdaily.utils.browser.Service")
    @patch("yourdaily.utils.browser.ChromeDriverManager")
    def test_setup_browser_headless(
        self, mock_driver_manager, mock_service, mock_chrome
    ):
        """Test browser setup in headless mode."""
        mock_driver_manager.return_value.install.return_value = "/path/to/chromedriver"
        browser = BrowserManager(headless=True)

        result = browser._setup_browser()

        # Verify ChromeDriverManager was used
        mock_driver_manager.assert_called_once()
        mock_service.assert_called_once_with("/path/to/chromedriver")

        # Verify Chrome was initialized with correct options
        mock_chrome.assert_called_once()

        # Check that --headless was added to options
        call_args = mock_chrome.call_args
        options = call_args[1]["options"]
        assert any("--headless" in str(arg) for arg in options.arguments)

    @patch("yourdaily.utils.browser.webdriver.Chrome")
    @patch("yourdaily.utils.browser.Service")
    @patch("yourdaily.utils.browser.ChromeDriverManager")
    def test_setup_browser_not_headless(
        self, mock_driver_manager, mock_service, mock_chrome
    ):
        """Test browser setup in non-headless mode."""
        mock_driver_manager.return_value.install.return_value = "/path/to/chromedriver"
        browser = BrowserManager(headless=False)

        result = browser._setup_browser()

        # Verify Chrome was initialized
        mock_chrome.assert_called_once()

        # Check that --headless was NOT added to options
        call_args = mock_chrome.call_args
        options = call_args[1]["options"]
        assert not any("--headless" in str(arg) for arg in options.arguments)

    @patch("yourdaily.utils.browser.webdriver.Chrome")
    @patch("yourdaily.utils.browser.Service")
    @patch("yourdaily.utils.browser.ChromeDriverManager")
    def test_setup_browser_standard_options(
        self, mock_driver_manager, mock_service, mock_chrome
    ):
        """Test that standard browser options are set."""
        mock_driver_manager.return_value.install.return_value = "/path/to/chromedriver"
        browser = BrowserManager()

        result = browser._setup_browser()

        call_args = mock_chrome.call_args
        options = call_args[1]["options"]

        # Check for standard options
        expected_options = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1920,1080",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
        ]

        for expected_option in expected_options:
            assert any(expected_option in str(arg) for arg in options.arguments)

    @patch("yourdaily.utils.browser.BrowserManager._setup_browser")
    def test_context_manager_enter(self, mock_setup):
        """Test context manager __enter__ method."""
        mock_driver = MagicMock()
        mock_setup.return_value = mock_driver

        browser = BrowserManager()

        result = browser.__enter__()

        assert browser.driver == mock_driver
        assert result == browser
        mock_setup.assert_called_once()

    def test_context_manager_exit_with_driver(self):
        """Test context manager __exit__ method when driver exists."""
        browser = BrowserManager()
        mock_driver = MagicMock()
        browser.driver = mock_driver

        browser.__exit__(None, None, None)

        mock_driver.quit.assert_called_once()
        assert browser.driver is None

    @patch("yourdaily.utils.browser.logger")
    def test_context_manager_exit_with_exception(self, mock_logger):
        """Test context manager __exit__ method when quit raises exception."""
        browser = BrowserManager()
        mock_driver = MagicMock()
        mock_driver.quit.side_effect = Exception("Test error")
        browser.driver = mock_driver

        browser.__exit__(None, None, None)

        mock_logger.warning.assert_called_with("Error closing browser: Test error")
        assert browser.driver is None

    def test_context_manager_exit_without_driver(self):
        """Test context manager __exit__ method when no driver exists."""
        browser = BrowserManager()
        browser.driver = None

        # Should not raise exception
        browser.__exit__(None, None, None)

    @patch("yourdaily.utils.browser.time.sleep")
    @patch("yourdaily.utils.browser.WebDriverWait")
    def test_resolve_google_news_url_success(self, mock_wait, mock_sleep):
        """Test successful Google News URL resolution."""
        browser = BrowserManager()
        mock_driver = MagicMock()
        browser.driver = mock_driver

        # Mock successful redirect
        google_url = "https://news.google.com/articles/test"
        real_url = "https://realnews.com/article"
        mock_driver.current_url = real_url

        result = browser.resolve_google_news_url(google_url)

        mock_driver.get.assert_called_once_with(google_url)
        assert result == real_url

    def test_resolve_google_news_url_no_driver(self):
        """Test resolve_google_news_url without driver initialized."""
        browser = BrowserManager()
        browser.driver = None

        result = browser.resolve_google_news_url("https://news.google.com/test")

        assert result is None

    @patch("yourdaily.utils.browser.time.sleep")
    @patch("yourdaily.utils.browser.WebDriverWait")
    @patch("yourdaily.utils.browser.logger")
    def test_resolve_google_news_url_still_on_google(
        self, mock_logger, mock_wait, mock_sleep
    ):
        """Test resolve_google_news_url when still on Google domain."""
        browser = BrowserManager()
        mock_driver = MagicMock()
        browser.driver = mock_driver

        # Mock staying on Google News domain
        google_url = "https://news.google.com/articles/test"
        mock_driver.current_url = google_url

        # Mock finding no external links
        mock_driver.find_elements.return_value = []

        result = browser.resolve_google_news_url(google_url)

        assert result is None
        mock_logger.warning.assert_called()

    @patch("yourdaily.utils.browser.time.sleep")
    @patch("yourdaily.utils.browser.WebDriverWait")
    def test_resolve_google_news_url_find_external_link(self, mock_wait, mock_sleep):
        """Test resolve_google_news_url finding external link."""
        browser = BrowserManager()
        mock_driver = MagicMock()
        browser.driver = mock_driver

        google_url = "https://news.google.com/articles/test"
        mock_driver.current_url = google_url

        # Mock finding external link
        mock_link = MagicMock()
        mock_link.get_attribute.return_value = "https://external-news.com/article"
        mock_driver.find_elements.return_value = [mock_link]

        result = browser.resolve_google_news_url(google_url)

        assert result == "https://external-news.com/article"

    @patch("yourdaily.utils.browser.logger")
    def test_resolve_google_news_url_webdriver_exception(self, mock_logger):
        """Test resolve_google_news_url handling WebDriverException."""
        browser = BrowserManager()
        mock_driver = MagicMock()
        browser.driver = mock_driver
        mock_driver.get.side_effect = WebDriverException("Test error")

        result = browser.resolve_google_news_url("https://news.google.com/test")

        assert result is None
        mock_logger.error.assert_called()

    @patch("yourdaily.utils.browser.WebDriverWait")
    @patch("yourdaily.utils.browser.EC")
    def test_get_page_content_success(self, mock_ec, mock_wait):
        """Test successful page content retrieval."""
        browser = BrowserManager()
        mock_driver = MagicMock()
        browser.driver = mock_driver

        test_url = "https://example.com/article"
        test_content = "<html><body>Test content</body></html>"
        mock_driver.page_source = test_content

        result = browser.get_page_content(test_url)

        mock_driver.set_page_load_timeout.assert_called_once_with(30)
        mock_driver.get.assert_called_once_with(test_url)
        assert result == test_content

    def test_get_page_content_no_driver(self):
        """Test get_page_content without driver initialized."""
        browser = BrowserManager()
        browser.driver = None

        result = browser.get_page_content("https://example.com")

        assert result is None

    @patch("yourdaily.utils.browser.WebDriverWait")
    @patch("yourdaily.utils.browser.logger")
    def test_get_page_content_timeout(self, mock_logger, mock_wait):
        """Test get_page_content handling timeout."""
        browser = BrowserManager()
        mock_driver = MagicMock()
        browser.driver = mock_driver
        mock_driver.get.side_effect = TimeoutException("Timeout")

        result = browser.get_page_content("https://example.com")

        assert result is None
        mock_logger.error.assert_called()

    def test_get_page_content_empty_content(self):
        """Test get_page_content with empty content."""
        browser = BrowserManager()
        mock_driver = MagicMock()
        browser.driver = mock_driver
        mock_driver.page_source = ""

        result = browser.get_page_content("https://example.com")

        assert result is None

    def test_resolve_and_fetch_success(self):
        """Test successful resolve_and_fetch operation."""
        browser = BrowserManager()

        with patch.object(
            browser, "resolve_google_news_url"
        ) as mock_resolve, patch.object(
            browser, "get_page_content"
        ) as mock_get_content:
            mock_resolve.return_value = "https://real-news.com/article"
            mock_get_content.return_value = "<html>Content</html>"

            real_url, content = browser.resolve_and_fetch(
                "https://news.google.com/test"
            )

            assert real_url == "https://real-news.com/article"
            assert content == "<html>Content</html>"

    def test_resolve_and_fetch_resolve_failure(self):
        """Test resolve_and_fetch when URL resolution fails."""
        browser = BrowserManager()

        with patch.object(browser, "resolve_google_news_url") as mock_resolve:
            mock_resolve.return_value = None

            real_url, content = browser.resolve_and_fetch(
                "https://news.google.com/test"
            )

            assert real_url is None
            assert content is None

    def test_is_external_link_valid_external(self):
        """Test _is_external_link with valid external URL."""
        browser = BrowserManager()

        result = browser._is_external_link("https://external-news.com/article")
        assert result is True

    def test_is_external_link_google_domain(self):
        """Test _is_external_link with Google domain URL."""
        browser = BrowserManager()

        google_urls = [
            "https://google.com/test",
            "https://news.google.com/test",
            "https://googleusercontent.com/test",
            "https://gstatic.com/test",
        ]

        for url in google_urls:
            result = browser._is_external_link(url)
            assert result is False

    def test_is_external_link_invalid_url(self):
        """Test _is_external_link with invalid URL."""
        browser = BrowserManager()

        result = browser._is_external_link("invalid-url")
        assert result is False


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    @patch("yourdaily.utils.browser.BrowserManager")
    def test_resolve_google_news_url_function(self, mock_browser_manager):
        """Test resolve_google_news_url convenience function."""
        mock_browser = MagicMock()
        mock_browser.__enter__.return_value = mock_browser
        mock_browser.resolve_google_news_url.return_value = "https://real-news.com"
        mock_browser_manager.return_value = mock_browser

        result = resolve_google_news_url("https://news.google.com/test")

        mock_browser_manager.assert_called_once_with(headless=True)
        mock_browser.resolve_google_news_url.assert_called_once_with(
            "https://news.google.com/test"
        )
        assert result == "https://real-news.com"

    @patch("yourdaily.utils.browser.BrowserManager")
    @patch("yourdaily.utils.browser.logger")
    def test_resolve_google_news_url_function_exception(
        self, mock_logger, mock_browser_manager
    ):
        """Test resolve_google_news_url convenience function with exception."""
        mock_browser_manager.side_effect = Exception("Test error")

        result = resolve_google_news_url("https://news.google.com/test")

        assert result is None
        mock_logger.error.assert_called()

    @patch("yourdaily.utils.browser.BrowserManager")
    def test_fetch_article_content_with_browser_function(self, mock_browser_manager):
        """Test fetch_article_content_with_browser convenience function."""
        mock_browser = MagicMock()
        mock_browser.__enter__.return_value = mock_browser
        mock_browser.get_page_content.return_value = "<html>Content</html>"
        mock_browser_manager.return_value = mock_browser

        result = fetch_article_content_with_browser("https://example.com")

        mock_browser_manager.assert_called_once_with(headless=True)
        mock_browser.get_page_content.assert_called_once_with("https://example.com")
        assert result == "<html>Content</html>"

    @patch("yourdaily.utils.browser.BrowserManager")
    @patch("yourdaily.utils.browser.logger")
    def test_fetch_article_content_with_browser_function_exception(
        self, mock_logger, mock_browser_manager
    ):
        """Test fetch_article_content_with_browser convenience function with exception."""
        mock_browser_manager.side_effect = Exception("Test error")

        result = fetch_article_content_with_browser("https://example.com")

        assert result is None
        mock_logger.error.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])
