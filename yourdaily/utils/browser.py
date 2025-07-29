#!/usr/bin/env python3
"""
Browser Utilities for Article Scraping

Provides headless browser functionality for resolving Google News URLs
and scraping article content that requires JavaScript execution.
"""

import time
from typing import Optional, Tuple
from urllib.parse import urlparse

from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


class BrowserManager:
    """Manages headless browser operations for article scraping."""

    def __init__(self, headless: bool = True, timeout: int = 30):
        """
        Initialize the browser manager.

        Args:
            headless (bool): Whether to run browser in headless mode
            timeout (int): Default timeout for operations in seconds
        """
        self.headless = headless
        self.timeout = timeout
        self.driver = None

    def _setup_browser(self) -> webdriver.Chrome:
        """Set up Chrome browser with appropriate options."""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless")

        # Performance and stability options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")

        # User agent to avoid blocking
        from yourdaily.utils.user_agent import get_chrome_user_agent

        chrome_options.add_argument(f"--user-agent={get_chrome_user_agent()}")

        # Automatically download and manage ChromeDriver
        service = Service(ChromeDriverManager().install())

        return webdriver.Chrome(service=service, options=chrome_options)

    def __enter__(self):
        """Context manager entry."""
        self.driver = self._setup_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup browser."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self.driver = None

    def resolve_google_news_url(self, google_news_url: str) -> Optional[str]:
        """
        Resolve a Google News URL to get the real article URL.

        Args:
            google_news_url (str): The Google News URL to resolve

        Returns:
            str: The resolved article URL, or None if failed
        """
        if not self.driver:
            logger.error("Browser not initialized. Use within context manager.")
            return None

        try:
            logger.debug(f"Resolving Google News URL: {google_news_url}")

            # Navigate to the Google News URL
            self.driver.get(google_news_url)

            # Wait for any JavaScript redirects to complete
            time.sleep(3)

            # Try to wait for URL change (redirect)
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda d: d.current_url != google_news_url
                )
            except TimeoutException:
                logger.debug("No automatic redirect detected")

            final_url = self.driver.current_url

            # Check if we're still on Google News domain
            parsed_url = urlparse(final_url)
            if "news.google.com" in parsed_url.netloc:
                logger.debug(
                    "Still on Google News domain, searching for redirect links"
                )

                # Try to find redirect links in the page
                try:
                    # Look for external links that might be the article
                    links = self.driver.find_elements(By.TAG_NAME, "a")

                    for link in links[:20]:  # Check first 20 links
                        href = link.get_attribute("href")
                        if href and self._is_external_link(href):
                            logger.debug(f"Found potential article link: {href}")
                            return href

                    # Try clicking the first clickable link to trigger redirect
                    clickable_links = self.driver.find_elements(
                        By.CSS_SELECTOR, "a[href*='http']:not([href*='google'])"
                    )

                    if clickable_links:
                        logger.debug("Attempting to click redirect link")
                        clickable_links[0].click()
                        time.sleep(2)

                        new_url = self.driver.current_url
                        if new_url != final_url and "news.google.com" not in new_url:
                            return new_url

                except Exception as e:
                    logger.debug(f"Error searching for redirect links: {e}")

                logger.warning("Could not resolve Google News URL to real article")
                return None

            logger.debug(f"Successfully resolved to: {final_url}")
            return final_url

        except WebDriverException as e:
            logger.error(f"Browser error resolving URL: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error resolving URL: {e}")
            return None

    def get_page_content(self, url: str) -> Optional[str]:
        """
        Get the HTML content of a webpage.

        Args:
            url (str): The URL to fetch content from

        Returns:
            str: The page HTML content, or None if failed
        """
        if not self.driver:
            logger.error("Browser not initialized. Use within context manager.")
            return None

        try:
            logger.debug(f"Fetching content from: {url}")

            # Set page load timeout
            self.driver.set_page_load_timeout(self.timeout)

            # Navigate to the URL
            self.driver.get(url)

            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Get page source
            content = self.driver.page_source

            if not content or len(content) < 100:
                logger.warning(f"Page content too short or empty for: {url}")
                return None

            logger.debug(f"Successfully fetched {len(content)} characters from: {url}")
            return content

        except TimeoutException:
            logger.error(f"Timeout loading page: {url}")
            return None
        except WebDriverException as e:
            logger.error(f"Browser error fetching content: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching content: {e}")
            return None

    def resolve_and_fetch(
        self, google_news_url: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolve a Google News URL and fetch the content from the real article.

        Args:
            google_news_url (str): The Google News URL to process

        Returns:
            Tuple[Optional[str], Optional[str]]: (real_url, content) or (None, None) if failed
        """
        # First resolve the URL
        real_url = self.resolve_google_news_url(google_news_url)

        if not real_url:
            return None, None

        # Then fetch content from the real URL
        content = self.get_page_content(real_url)

        return real_url, content

    def _is_external_link(self, url: str) -> bool:
        """Check if a URL is an external link (not Google domain)."""
        try:
            parsed = urlparse(url)
            google_domains = ["google.com", "googleusercontent.com", "gstatic.com"]
            is_google_domain = any(domain in parsed.netloc for domain in google_domains)
            return (
                parsed.scheme in ["http", "https"]
                and parsed.netloc
                and not is_google_domain
            )
        except Exception:
            return False


def resolve_google_news_url(
    google_news_url: str, headless: bool = True
) -> Optional[str]:
    """
    Convenience function to resolve a single Google News URL.

    Args:
        google_news_url (str): The Google News URL to resolve
        headless (bool): Whether to run browser in headless mode

    Returns:
        str: The resolved article URL, or None if failed
    """
    try:
        with BrowserManager(headless=headless) as browser:
            return browser.resolve_google_news_url(google_news_url)
    except Exception as e:
        logger.error(f"Error in resolve_google_news_url: {e}")
        return None


def fetch_article_content_with_browser(
    url: str, headless: bool = True
) -> Optional[str]:
    """
    Convenience function to fetch article content using browser.

    Args:
        url (str): The URL to fetch content from
        headless (bool): Whether to run browser in headless mode

    Returns:
        str: The page HTML content, or None if failed
    """
    try:
        with BrowserManager(headless=headless) as browser:
            return browser.get_page_content(url)
    except Exception as e:
        logger.error(f"Error in fetch_article_content_with_browser: {e}")
        return None
