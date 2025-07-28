#!/usr/bin/env python3
"""
Article Content Scraper

Fetches article content from URLs in search_index.db and cleans it using trafilatura.
Stores cleaned content in article_data.db
"""

import hashlib
import os
import sys
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
import trafilatura
from dotenv import load_dotenv

from yourdaily.utils.db import DatabaseManager
from yourdaily.utils.logger import get_logger, setup_logger


class ArticleScraper:
    def __init__(self):
        """Initialize the article scraper."""
        load_dotenv()

        # Setup logging
        self.logger = get_logger("ArticleScraper")

        # Initialize database
        self.db = DatabaseManager(
            search_db_path=os.getenv("SEARCH_DB_PATH", "data/db/search_index.db"),
            article_db_path=os.getenv("ARTICLE_DB_PATH", "data/db/article_data.db"),
        )

        # HTTP session for requests
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                )
            }
        )

        # Rate limiting
        self.request_delay = 1  # seconds between requests

    def get_unprocessed_articles(self) -> List[Dict[str, Any]]:
        """Get articles that haven't been processed yet."""
        return self.db.get_unprocessed_articles()

    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and accessible."""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    def fetch_article_content(self, url: str) -> Optional[str]:
        """Fetch raw HTML content from URL."""
        try:
            self.logger.debug(f"Fetching content from: {url}")

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Check if content is HTML
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                self.logger.warning(f"Non-HTML content type: {content_type}")
                return None

            return response.text

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error fetching {url}: {e}")
            return None

    def clean_article_content(self, html_content: str, url: str) -> Optional[str]:
        """Clean article content using trafilatura."""
        try:
            # Extract main content
            extracted_text = trafilatura.extract(
                html_content, include_comments=False, include_tables=False
            )

            if not extracted_text:
                self.logger.warning(f"No content extracted from {url}")
                return None

            # Basic cleaning
            cleaned_text = self.post_process_text(extracted_text)

            if len(cleaned_text.strip()) < 100:  # Too short to be meaningful
                self.logger.warning(
                    f"Extracted content too short from {url}: "
                    f"{len(cleaned_text)} chars"
                )
                return None

            return cleaned_text

        except Exception as e:
            self.logger.error(f"Error cleaning content from {url}: {e}")
            return None

    def post_process_text(self, text: str) -> str:
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

    def generate_content_hash(self, content: str) -> str:
        """Generate a hash of the content for deduplication."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def scrape_article(self, article: Dict[str, Any]) -> bool:
        """Scrape a single article."""
        url = article["url"]
        title = article["title"]

        self.logger.info(f"Scraping article: {title[:60]}...")

        # Validate URL
        if not self.is_valid_url(url):
            self.logger.error(f"Invalid URL: {url}")
            return False

        # Fetch content
        html_content = self.fetch_article_content(url)
        if not html_content:
            return False

        # Clean content
        clean_text = self.clean_article_content(html_content, url)
        if not clean_text:
            return False

        # Store in database
        try:
            success = self.db.insert_article_data(url=url, clean_text=clean_text)

            if success:
                self.logger.info(f"Successfully scraped and stored: {title[:60]}...")
                return True
            else:
                self.logger.error(f"Failed to store article data for: {url}")
                return False

        except Exception as e:
            self.logger.error(f"Error storing article data: {e}")
            return False

    def run(self) -> Dict[str, Any]:
        """Run the complete article scraping process."""
        self.logger.info("Starting article scraping process")

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

        # Process each article
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

        # Summary
        self.logger.info(f"Scraping complete: {successful} successful, {failed} failed")

        return {
            "success": True,
            "articles_processed": len(articles),
            "articles_successful": successful,
            "articles_failed": failed,
        }


def main():
    """Main entry point."""
    # Setup logging
    setup_logger()
    logger = get_logger("main")

    logger.info("=" * 50)
    logger.info("Starting Article Content Scraper")
    logger.info("=" * 50)

    try:
        scraper = ArticleScraper()
        result = scraper.run()

        if result["success"]:
            logger.info("Article scraping completed successfully")
            logger.info(
                f"Results: {result['articles_successful']}/"
                f"{result['articles_processed']} articles processed"
            )
        else:
            logger.error("Article scraping failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
