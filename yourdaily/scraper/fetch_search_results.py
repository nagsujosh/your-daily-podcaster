#!/usr/bin/env python3
"""
News Search Results Fetcher

Fetches news articles from GNews based on topics defined in Topics.md
and stores metadata in search_index.db
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from gnews import GNews

from yourdaily.utils.db import DatabaseManager
from yourdaily.utils.logger import get_logger, setup_logger
from yourdaily.utils.time import get_yesterday_date, parse_gnews_date


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

        # Initialize GNews client
        self.gnews = GNews(
            language="en",
            country="US",
            max_results=20,
            period="7d",
            start_date=None,
            end_date=None,
        )

        # Set API key if available
        api_key = os.getenv("GNEWS_API_KEY")
        if api_key:
            self.gnews.api_key = api_key
            self.logger.info("Using GNews API key")
        else:
            self.logger.info("No GNews API key found - using free tier")

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
                    if topic:
                        topics.append(topic)
                        self.logger.debug(f"Found topic: {topic}")

            self.logger.info(f"Loaded {len(topics)} topics from Topics.md")
            return topics

        except Exception as e:
            self.logger.error(f"Error loading topics: {e}")
            return []

    def search_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Search for articles on a specific topic."""
        try:
            self.logger.info(f"Searching for articles on: {topic}")

            # Search GNews
            articles = self.gnews.get_news(topic)

            if not articles:
                self.logger.warning(f"No articles found for topic: {topic}")
                return []

            # Filter articles from yesterday
            yesterday = get_yesterday_date()
            filtered_articles = []

            for article in articles:
                # Parse publication date
                pub_date = parse_gnews_date(article.get("published date", ""))

                if pub_date == yesterday:
                    filtered_articles.append(
                        {
                            "topic": topic,
                            "title": article.get("title", ""),
                            "url": article.get("url", ""),
                            "source": article.get("publisher", {}).get("title", ""),
                            "gnews_date": article.get("published date", ""),
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
                    self.logger.debug(f"Article already exists, skipping: {article['title'][:50]}...")
                    skipped_count += 1
                    continue

                success = self.db.insert_search_result(
                    topic=article["topic"],
                    title=article["title"],
                    url=article["url"],
                    source=article["source"],
                    gnews_date=article["gnews_date"],
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

        self.logger.info(f"Storage complete: {stored_count} new articles stored, {skipped_count} duplicates skipped")
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
            f"Search complete: {total_articles} articles found, "
            f"{total_stored} stored"
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
    logger.info("Starting News Search Results Fetcher")
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
