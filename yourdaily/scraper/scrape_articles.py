#!/usr/bin/env python3
"""
Article Content Scraper

Fetches article content from URLs in search_index.db using headless browser
for both URL resolution and content scraping. Cleans content using trafilatura.
Stores cleaned content in article_data.db

Now supports multiprocessing for faster processing and date-based filtering.
"""

import multiprocessing as mp
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import trafilatura
from dotenv import load_dotenv

from yourdaily.utils.browser import BrowserManager
from yourdaily.utils.db import DatabaseManager
from yourdaily.utils.logger import get_logger, setup_logger
from yourdaily.utils.time import get_yesterday_date


def process_single_article(
    article_data: Tuple[Dict[str, Any], str, str, int]
) -> Dict[str, Any]:
    """
    Process a single article in a separate process.

    Args:
        article_data: Tuple containing (article_dict, search_db_path, article_db_path, request_delay)

    Returns:
        Dict with processing results
    """
    article, search_db_path, article_db_path, request_delay = article_data

    # Initialize components for this process
    load_dotenv()

    # Create a separate logger for this process
    logger = get_logger(f"ArticleScraper-{mp.current_process().pid}")

    # Initialize database for this process
    db = DatabaseManager(search_db_path=search_db_path, article_db_path=article_db_path)

    try:
        result = _scrape_single_article(article, db, logger, request_delay)
        return result
    except Exception as e:
        logger.error(f"Error in process {mp.current_process().pid}: {e}")
        return {
            "success": False,
            "article_title": article.get("title", "Unknown"),
            "error": str(e),
        }


def _scrape_single_article(
    article: Dict[str, Any], db: DatabaseManager, logger, request_delay: int
) -> Dict[str, Any]:
    """Helper function to scrape a single article."""
    rss_url = article.get("rss_url", article.get("url"))
    title = article["title"]
    existing_real_url = article.get("real_url")

    logger.info(f"Processing: {title[:60]}...")

    # Validate RSS URL
    if not _is_valid_url(rss_url):
        logger.error(f"Invalid RSS URL: {rss_url}")
        return {"success": False, "article_title": title, "error": "Invalid RSS URL"}

    # Resolve to real URL if not already done
    real_url = existing_real_url
    if not real_url:
        real_url = _resolve_rss_url_to_real_url(rss_url, logger)
        if not real_url:
            logger.error(f"Failed to resolve real URL for: {rss_url}")
            return {
                "success": False,
                "article_title": title,
                "error": "Failed to resolve real URL",
            }

        # Update the search index with the real URL
        db.update_real_url(rss_url, real_url)

    # Validate real URL
    if not _is_valid_url(real_url):
        logger.error(f"Invalid real URL: {real_url}")
        return {"success": False, "article_title": title, "error": "Invalid real URL"}

    # Fetch content using browser
    html_content = _fetch_article_content_with_browser(real_url, logger)
    if not html_content:
        logger.error(f"Failed to fetch content from: {real_url}")
        return {
            "success": False,
            "article_title": title,
            "error": "Failed to fetch content",
        }

    # Clean content
    clean_text = _clean_article_content(html_content, real_url, logger)
    if not clean_text:
        logger.error(f"Failed to extract clean text from: {real_url}")
        return {
            "success": False,
            "article_title": title,
            "error": "Failed to extract clean text",
        }

    # Store in database
    try:
        success = db.insert_article_data(
            rss_url=rss_url, real_url=real_url, clean_text=clean_text
        )

        if success:
            logger.info(f"Successfully processed: {title[:60]}...")
            return {"success": True, "article_title": title}
        else:
            logger.error(f"Failed to store article data for: {real_url}")
            return {
                "success": False,
                "article_title": title,
                "error": "Failed to store data",
            }

    except Exception as e:
        logger.error(f"Error storing article data: {e}")
        return {
            "success": False,
            "article_title": title,
            "error": f"Database error: {str(e)}",
        }


def _is_valid_url(url: str) -> bool:
    """Check if URL is valid and accessible."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def _resolve_rss_url_to_real_url(rss_url: str, logger) -> Optional[str]:
    """Resolve RSS/Google News URL to real article URL using headless browser."""
    try:
        logger.debug(f"Resolving RSS URL: {rss_url}")

        # Check if this is a Google News URL that needs resolution
        parsed = urlparse(rss_url)
        if "news.google.com" in parsed.netloc:
            # Use browser to resolve Google News URL
            with BrowserManager(headless=True) as browser:
                real_url = browser.resolve_google_news_url(rss_url)

            if real_url:
                logger.info(f"Resolved Google News URL to: {real_url}")
                return real_url
            else:
                logger.warning(f"Failed to resolve Google News URL: {rss_url}")
                return None
        else:
            # For non-Google News URLs, assume it's already the real URL
            logger.debug(f"Non-Google News URL, using directly: {rss_url}")
            return rss_url

    except Exception as e:
        logger.error(f"Error resolving RSS URL {rss_url}: {e}")
        return None


def _fetch_article_content_with_browser(url: str, logger) -> Optional[str]:
    """Fetch raw HTML content from URL using headless browser."""
    try:
        logger.debug(f"Fetching content with browser from: {url}")

        with BrowserManager(headless=True) as browser:
            html_content = browser.get_page_content(url)

        if not html_content:
            logger.warning(f"No content retrieved from: {url}")
            return None

        logger.debug(f"Successfully fetched {len(html_content)} characters from: {url}")
        return html_content

    except Exception as e:
        logger.error(f"Error fetching content from {url}: {e}")
        return None


def _clean_article_content(html_content: str, url: str, logger) -> Optional[str]:
    """Clean article content using trafilatura."""
    try:
        # Extract main content
        extracted_text = trafilatura.extract(
            html_content,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
            favor_recall=False,
        )

        if not extracted_text:
            logger.warning(f"No content extracted from {url}")
            return None

        # Basic cleaning
        cleaned_text = _post_process_text(extracted_text)

        if len(cleaned_text.strip()) < 100:  # Too short to be meaningful
            logger.warning(
                f"Extracted content too short from {url}: " f"{len(cleaned_text)} chars"
            )
            return None

        return cleaned_text

    except Exception as e:
        logger.error(f"Error cleaning content from {url}: {e}")
        return None


def _post_process_text(text: str) -> str:
    """Post-process extracted text."""
    if not text:
        return ""

    # Remove excessive whitespace
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if line:  # Keep non-empty lines
            cleaned_lines.append(line)

    # Join with single newlines
    cleaned_text = "\n".join(cleaned_lines)

    # Remove excessive newlines
    while "\n\n\n" in cleaned_text:
        cleaned_text = cleaned_text.replace("\n\n\n", "\n\n")

    return cleaned_text.strip()


class ArticleScraper:
    def __init__(
        self, max_workers: Optional[int] = None, target_date: Optional[str] = None
    ):
        """Initialize the article scraper."""
        load_dotenv()

        # Setup logging
        self.logger = get_logger("ArticleScraper")

        # Initialize database
        self.db = DatabaseManager(
            search_db_path=os.getenv("SEARCH_DB_PATH", "data/db/search_index.db"),
            article_db_path=os.getenv("ARTICLE_DB_PATH", "data/db/article_data.db"),
        )

        # Date filtering - default to yesterday if not specified
        self.target_date = target_date or get_yesterday_date()
        self.logger.info(f"Target date for processing: {self.target_date}")

        # Multiprocessing configuration
        self.max_workers = max_workers or min(
            mp.cpu_count(), 4
        )  # Limit to 4 to avoid overwhelming
        self.logger.info(f"Using {self.max_workers} worker processes")

        # Rate limiting (reduced since we're using multiple processes)
        self.request_delay = 1  # seconds between requests per process

    def get_unprocessed_articles(self) -> List[Dict[str, Any]]:
        """Get articles that haven't been processed yet from the target date only."""
        return self.db.get_unprocessed_articles_from_date(self.target_date)

    def scrape_articles_multiprocessing(
        self, articles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process articles using multiprocessing for better performance."""
        if not articles:
            return {
                "success": True,
                "articles_processed": 0,
                "articles_successful": 0,
                "articles_failed": 0,
            }

        self.logger.info(
            f"Processing {len(articles)} articles with {self.max_workers} workers"
        )

        # Prepare data for worker processes
        worker_data = [
            (
                article,
                self.db.search_db_path,
                self.db.article_db_path,
                self.request_delay,
            )
            for article in articles
        ]

        successful = 0
        failed = 0
        results = []

        try:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_article = {
                    executor.submit(process_single_article, data): data[0]
                    for data in worker_data
                }

                # Process completed tasks
                for future in as_completed(future_to_article):
                    article = future_to_article[future]
                    try:
                        result = future.result()
                        results.append(result)

                        if result["success"]:
                            successful += 1
                            self.logger.info(f"✓ {result['article_title'][:60]}...")
                        else:
                            failed += 1
                            self.logger.error(
                                f"✗ {result['article_title'][:60]}... - "
                                f"{result.get('error', 'Unknown error')}"
                            )

                    except Exception as e:
                        failed += 1
                        title = article.get("title", "Unknown")
                        self.logger.error(f"✗ {title[:60]}... - Process exception: {e}")

        except Exception as e:
            self.logger.error(f"Multiprocessing execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "articles_processed": len(articles),
                "articles_successful": successful,
                "articles_failed": failed,
            }

        return {
            "success": True,
            "articles_processed": len(articles),
            "articles_successful": successful,
            "articles_failed": failed,
            "results": results,
        }

    def scrape_article(self, article: Dict[str, Any]) -> bool:
        """Scrape a single article using headless browser (legacy single-threaded
        method).
        """
        rss_url = article.get("rss_url", article.get("url"))
        # Handle both field names during transition
        title = article["title"]
        existing_real_url = article.get("real_url")

        self.logger.info(f"Scraping article: {title[:60]}...")

        # Validate RSS URL
        if not _is_valid_url(rss_url):
            self.logger.error(f"Invalid RSS URL: {rss_url}")
            return False

        # Resolve to real URL if not already done
        real_url = existing_real_url
        if not real_url:
            real_url = _resolve_rss_url_to_real_url(rss_url, self.logger)
            if not real_url:
                self.logger.error(f"Failed to resolve real URL for: {rss_url}")
                return False

            # Update the search index with the real URL
            self.db.update_real_url(rss_url, real_url)

        # Validate real URL
        if not _is_valid_url(real_url):
            self.logger.error(f"Invalid real URL: {real_url}")
            return False

        # Fetch content using browser
        html_content = _fetch_article_content_with_browser(real_url, self.logger)
        if not html_content:
            self.logger.error(f"Failed to fetch content from: {real_url}")
            return False

        # Clean content
        clean_text = _clean_article_content(html_content, real_url, self.logger)
        if not clean_text:
            self.logger.error(f"Failed to extract clean text from: {real_url}")
            return False

        # Store in database
        try:
            success = self.db.insert_article_data(
                rss_url=rss_url, real_url=real_url, clean_text=clean_text
            )

            if success:
                self.logger.info(f"Successfully scraped and stored: {title[:60]}...")
                return True
            else:
                self.logger.error(f"Failed to store article data for: {real_url}")
                return False

        except Exception as e:
            self.logger.error(f"Error storing article data: {e}")
            return False

    def run(self, use_multiprocessing: bool = True) -> Dict[str, Any]:
        """Run the complete article scraping process."""
        self.logger.info("Starting article scraping process with headless browser")

        # Get unprocessed articles
        articles = self.get_unprocessed_articles()

        if not articles:
            self.logger.info("No unprocessed articles found")
            return {
                "success": True,
                "articles_processed": 0,
                "articles_successful": 0,
            }

        self.logger.info(f"Found {len(articles)} articles to process")

        if use_multiprocessing and len(articles) > 1:
            # Use multiprocessing for better performance
            self.logger.info("Using multiprocessing mode for faster processing")
            result = self.scrape_articles_multiprocessing(articles)
        else:
            # Use single-threaded processing
            self.logger.info("Using single-threaded mode")
            successful = 0
            failed = 0

            for i, article in enumerate(articles, 1):
                self.logger.info(f"Processing article {i}/{len(articles)}")

                try:
                    if self.scrape_article(article):
                        successful += 1
                    else:
                        failed += 1

                    # Rate limiting
                    if i < len(articles):  # Don't delay after the last article
                        time.sleep(self.request_delay)

                except Exception as e:
                    self.logger.error(f"Error processing article: {e}")
                    failed += 1

            result = {
                "success": True,
                "articles_processed": len(articles),
                "articles_successful": successful,
                "articles_failed": failed,
            }

        # Summary
        self.logger.info(
            f"Scraping complete: {result['articles_successful']} successful, "
            f"{result.get('articles_failed', 0)} failed"
        )

        return result


def main():
    """Main entry point."""
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Scrape articles using headless browser with multiprocessing"
    )
    parser.add_argument(
        "--no-multiprocessing",
        action="store_true",
        help="Disable multiprocessing and use single-threaded mode",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum number of worker processes (default: min(cpu_count, 4))",
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Target date for processing (YYYY-MM-DD format, defaults to yesterday)",
    )
    args = parser.parse_args()

    # Setup logging
    setup_logger()
    logger = get_logger("main")

    logger.info("=" * 50)
    logger.info("Starting Article Content Scraper (Browser-based with Multiprocessing)")
    logger.info("=" * 50)

    try:
        scraper = ArticleScraper(max_workers=args.max_workers, target_date=args.date)
        use_multiprocessing = not args.no_multiprocessing

        if use_multiprocessing:
            logger.info(f"Multiprocessing enabled with {scraper.max_workers} workers")
        else:
            logger.info("Single-threaded mode enabled")

        result = scraper.run(use_multiprocessing=use_multiprocessing)

        if result["success"]:
            logger.info("Article scraping completed successfully")
            logger.info(
                f"Results: {result['articles_successful']}/"
                f"{result['articles_processed']} articles processed"
            )

            if result.get("articles_failed", 0) > 0:
                logger.warning(
                    f"Failed to process {result['articles_failed']} articles"
                )
        else:
            logger.error("Article scraping failed")
            if "error" in result:
                logger.error(f"Error: {result['error']}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
