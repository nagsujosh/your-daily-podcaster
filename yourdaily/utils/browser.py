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

    def __init__(self, headless: bool = True, timeout: int = 120):
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
        try:
            chrome_options = Options()

            if self.headless:
                chrome_options.add_argument("--headless")

            # Performance and stability options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--disable-javascript")

            # Increase timeouts and add stability options
            chrome_options.add_argument("--page-load-strategy=eager")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-renderer-backgrounding")

            # Add user agent with better error handling
            try:
                from yourdaily.utils.user_agent import get_chrome_user_agent

                user_agent = get_chrome_user_agent()
                chrome_options.add_argument(f"--user-agent={user_agent}")
            except Exception as e:
                logger.warning(f"Could not set custom user agent: {e}")
                # Use a default user agent if the custom one fails
                chrome_options.add_argument(
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )

            # Automatically download and manage ChromeDriver with better error handling
            try:
                service = Service(ChromeDriverManager().install())
            except Exception as e:
                logger.error(f"Failed to setup ChromeDriver: {e}")
                # Try with system chromedriver as fallback
                service = Service()

            driver = webdriver.Chrome(service=service, options=chrome_options)

            # Set timeouts
            driver.set_page_load_timeout(self.timeout)
            driver.implicitly_wait(10)

            return driver

        except Exception as e:
            logger.error(f"Failed to setup browser: {e}")
            raise RuntimeError(f"Browser setup failed: {e}")

    def __enter__(self):
        """Context manager entry."""
        try:
            self.driver = self._setup_browser()
            return self
        except Exception as e:
            logger.error(f"Failed to initialize browser in context manager: {e}")
            raise

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

            # Navigate to the Google News URL with timeout handling
            try:
                self.driver.get(google_news_url)
            except TimeoutException:
                logger.warning(f"Timeout loading Google News URL: {google_news_url}")
                return None

            # Wait for any JavaScript redirects to complete
            time.sleep(5)

            # Try to wait for URL change (redirect)
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.current_url != google_news_url
                )
            except TimeoutException:
                logger.debug("No automatic redirect detected")

            final_url = self.driver.current_url

            # Check if we're still on Google News domain
            try:
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
                            try:
                                href = link.get_attribute("href")
                                if href and self._is_external_link(href):
                                    logger.debug(
                                        f"Found potential article link: {href}"
                                    )
                                    return href
                            except Exception as e:
                                logger.debug(f"Error checking link: {e}")
                                continue

                        # Try clicking the first clickable link to trigger redirect
                        clickable_links = self.driver.find_elements(
                            By.CSS_SELECTOR, "a[href*='http']:not([href*='google'])"
                        )

                        if clickable_links:
                            logger.debug("Attempting to click redirect link")
                            try:
                                clickable_links[0].click()
                                time.sleep(3)

                                new_url = self.driver.current_url
                                if (
                                    new_url != final_url
                                    and "news.google.com" not in new_url
                                ):
                                    return new_url
                            except Exception as e:
                                logger.debug(f"Error clicking redirect link: {e}")

                    except Exception as e:
                        logger.debug(f"Error searching for redirect links: {e}")

                    logger.warning("Could not resolve Google News URL to real article")
                    return None

                logger.debug(f"Successfully resolved to: {final_url}")
                return final_url

            except Exception as e:
                logger.error(f"Error parsing final URL: {e}")
                return None

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

            # Navigate to the URL with timeout handling
            try:
                self.driver.get(url)
            except TimeoutException:
                logger.error(f"Timeout loading page: {url}")
                return None

            # Wait for page to load
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                logger.warning(f"Timeout waiting for page body: {url}")
                # Continue anyway, we might still have some content

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
        real_url = self.resolve_google_news_url(google_news_url)
        if not real_url:
            return None, None

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
        with BrowserManager(headless=headless, timeout=120) as browser:
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
        with BrowserManager(headless=headless, timeout=120) as browser:
            return browser.get_page_content(url)
    except Exception as e:
        logger.error(f"Error in fetch_article_content_with_browser: {e}")
        return None
