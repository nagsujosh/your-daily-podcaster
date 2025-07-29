#!/usr/bin/env python3
"""
News Search Results Fetcher

Fetches news articles from Google News RSS feeds based on topics defined in Topics.md
and stores metadata in search_index.db
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote

import feedparser
import requests
from dotenv import load_dotenv

from yourdaily.utils.db import DatabaseManager
from yourdaily.utils.logger import get_logger, setup_logger
from yourdaily.utils.time import get_yesterday_date


class NewsFetcher:
    def __init__(self):
        """Initialize the news fetcher with configuration."""
        load_dotenv()

        # Setup logging
        self.logger = get_logger("NewsFetcher")

        # Initialize database
        self.db = DatabaseManager(
            search_db_path=os.getenv("SEARCH_DB_PATH", "data/db/search_index.db"),
            article_db_path=os.getenv("ARTICLE_DB_PATH", "data/db/article_data.db"),
        )

        # RSS feed configuration
        self.base_rss_url = "https://news.google.com/rss/search"
        self.rss_params = {"hl": "en-US", "gl": "US", "ceid": "US:en"}

        # Request configuration
        self.session = requests.Session()
        # Try to use a fake user agent, fall back to a default if unavailable
        try:
            from fake_useragent import UserAgent

            ua = UserAgent()
            user_agent = ua.random
            self.logger.debug(f"Using fake user agent: {user_agent}")
        except Exception as e:
            user_agent = (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            self.logger.warning(
                f"Failed to get fake user agent, using default: {user_agent} ({e})"
            )

        self.session.headers.update({"User-Agent": user_agent})

    def load_topics(self) -> List[str]:
        """Load topics from Topics.md file."""
        topics_path = Path("data/Topics.md")

        if not topics_path.exists():
            self.logger.error(f"Topics file not found: {topics_path}")
            return []

        try:
            with open(topics_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract topics from markdown content
            topics = []
            lines = content.split("\n")

            for line in lines:
                line = line.strip()

                # Skip frontmatter
                if line.startswith("---"):
                    continue

                # Look for topic sections (lines starting with -)
                if line.startswith("- ") and not line.startswith("---"):
                    topic = line[2:].strip()  # Remove "- " prefix
                    # Remove quotes if present
                    topic = topic.strip("\"'")
                    if topic:
                        topics.append(topic)
                        self.logger.debug(f"Found topic: {topic}")

            self.logger.info(f"Loaded {len(topics)} topics from Topics.md")
            return topics

        except Exception as e:
            self.logger.error(f"Error loading topics: {e}")
            return []

    def parse_rss_date(self, rss_date: str) -> str:
        """Parse RSS pubDate to YYYY-MM-DD format."""
        try:
            # RSS dates are in RFC 2822 format: "Mon, 28 Jul 2025 09:00:06 GMT"
            dt = datetime.strptime(rss_date, "%a, %d %b %Y %H:%M:%S %Z")
            return dt.strftime("%Y-%m-%d")
        except Exception as e:
            self.logger.warning(f"Failed to parse RSS date '{rss_date}': {e}")
            return ""

    def build_rss_url(self, topic: str) -> str:
        """Build Google News RSS URL for a topic."""
        encoded_topic = quote(topic)
        params = "&".join([f"{k}={v}" for k, v in self.rss_params.items()])
        return f"{self.base_rss_url}?q={encoded_topic}&{params}"

    def search_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Search for articles on a specific topic using RSS."""
        try:
            self.logger.info(f"Searching for articles on: {topic}")

            # Build RSS URL
            rss_url = self.build_rss_url(topic)
            self.logger.debug(f"RSS URL: {rss_url}")

            # Fetch RSS feed
            response = self.session.get(rss_url, timeout=30)
            response.raise_for_status()

            # Parse RSS feed
            feed = feedparser.parse(response.content)

            if not feed.entries:
                self.logger.warning(f"No articles found for topic: {topic}")
                return []

            # Filter articles from yesterday
            yesterday = get_yesterday_date()
            filtered_articles = []

            for entry in feed.entries:
                # Parse publication date
                rss_date = getattr(entry, "published", "")
                pub_date = self.parse_rss_date(rss_date)

                if pub_date == yesterday:
                    # Extract source from entry
                    source = ""
                    if hasattr(entry, "source") and hasattr(entry.source, "href"):
                        source = getattr(entry.source, "title", entry.source.href)
                    elif hasattr(entry, "tags") and entry.tags:
                        source = entry.tags[0].term

                    filtered_articles.append(
                        {
                            "topic": topic,
                            "title": getattr(entry, "title", ""),
                            "url": getattr(entry, "link", ""),
                            "source": source,
                            "rss_date": rss_date,
                            "published_date": pub_date,
                        }
                    )

            self.logger.info(
                f"Found {len(filtered_articles)} articles from yesterday "
                f"for topic: {topic}"
            )
            return filtered_articles

        except Exception as e:
            self.logger.error(f"Error searching topic '{topic}': {e}")
            return []

    def store_articles(self, articles: List[Dict[str, Any]]) -> int:
        """Store articles in the database."""
        stored_count = 0
        skipped_count = 0

        for article in articles:
            try:
                # Check if article already exists
                if self.db.article_exists(article["url"]):
                    self.logger.debug(
                        f"Article already exists, skipping: {article['title'][:50]}..."
                    )
                    skipped_count += 1
                    continue

                success = self.db.insert_search_result(
                    topic=article["topic"],
                    title=article["title"],
                    rss_url=article["url"],
                    source=article["source"],
                    rss_date=article["rss_date"],
                    published_date=article["published_date"],
                )

                if success:
                    stored_count += 1
                    self.logger.debug(f"Stored article: {article['title'][:50]}...")
                else:
                    self.logger.warning(
                        f"Failed to store article: {article['title'][:50]}..."
                    )

            except Exception as e:
                self.logger.error(f"Error storing article: {e}")

        self.logger.info(
            f"Storage complete: {stored_count} new articles stored, "
            f"{skipped_count} duplicates skipped"
        )
        return stored_count

    def run(self) -> Dict[str, Any]:
        """Run the complete news fetching process."""
        self.logger.info("Starting news search process")

        # Load topics
        topics = self.load_topics()
        if not topics:
            self.logger.error("No topics found - exiting")
            return {"success": False, "error": "No topics found"}

        # Search each topic
        total_articles = 0
        total_stored = 0

        for topic in topics:
            articles = self.search_topic(topic)
            total_articles += len(articles)

            if articles:
                stored = self.store_articles(articles)
                total_stored += stored

        # Summary
        self.logger.info(
            f"Search complete: {total_articles} articles found, {total_stored} stored"
        )

        return {
            "success": True,
            "topics_searched": len(topics),
            "articles_found": total_articles,
            "articles_stored": total_stored,
        }


def main():
    """Main entry point."""
    # Setup logging
    setup_logger()
    logger = get_logger("main")

    logger.info("=" * 50)
    logger.info("Starting News RSS Fetcher")
    logger.info("=" * 50)

    try:
        fetcher = NewsFetcher()
        result = fetcher.run()

        if result["success"]:
            logger.info("News search completed successfully")
            logger.info(
                f"Results: {result['articles_stored']} articles stored from "
                f"{result['topics_searched']} topics"
            )
        else:
            logger.error(f"News search failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
