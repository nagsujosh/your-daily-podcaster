#!/usr/bin/env python3
"""
Test Date-Based Processing

Tests the date-based filtering and cleanup functionality.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from yourdaily.scraper.scrape_articles import ArticleScraper
from yourdaily.summarizer.summarize_articles import ArticleSummarizer
from yourdaily.tts.generate_audio import AudioGenerator
from yourdaily.utils.db import DatabaseManager
from yourdaily.utils.time import get_today_date, get_yesterday_date


class TestDateBasedProcessing(unittest.TestCase):
    """Test date-based processing functionality."""

    def setUp(self):
        """Set up test databases."""
        # Create temporary databases
        self.temp_dir = tempfile.mkdtemp()
        self.search_db_path = os.path.join(self.temp_dir, "test_search_index.db")
        self.article_db_path = os.path.join(self.temp_dir, "test_article_data.db")

        # Initialize database manager
        self.db = DatabaseManager(
            search_db_path=self.search_db_path, article_db_path=self.article_db_path
        )

    def tearDown(self):
        """Clean up test files."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_date_filtering(self):
        """Test that date filtering works correctly."""
        # Insert test data for different dates
        yesterday = get_yesterday_date()
        today = get_today_date()

        # Insert articles for yesterday
        self.db.insert_search_result(
            topic="Test Topic",
            title="Yesterday Article 1",
            rss_url="http://example.com/1",
            source="Test Source",
            rss_date="Mon, 01 Jan 2024 00:00:00 GMT",
            published_date=yesterday,
        )

        self.db.insert_search_result(
            topic="Test Topic",
            title="Yesterday Article 2",
            rss_url="http://example.com/2",
            source="Test Source",
            rss_date="Mon, 01 Jan 2024 00:00:00 GMT",
            published_date=yesterday,
        )

        # Insert article for today
        self.db.insert_search_result(
            topic="Test Topic",
            title="Today Article",
            rss_url="http://example.com/3",
            source="Test Source",
            rss_date="Tue, 02 Jan 2024 00:00:00 GMT",
            published_date=today,
        )

        # Test that only yesterday's articles are returned
        yesterday_articles = self.db.get_unprocessed_articles_from_date(yesterday)
        today_articles = self.db.get_unprocessed_articles_from_date(today)

        self.assertEqual(len(yesterday_articles), 2)
        self.assertEqual(len(today_articles), 1)

        # Verify article titles
        yesterday_titles = [article["title"] for article in yesterday_articles]
        today_titles = [article["title"] for article in today_articles]

        self.assertIn("Yesterday Article 1", yesterday_titles)
        self.assertIn("Yesterday Article 2", yesterday_titles)
        self.assertIn("Today Article", today_titles)

    def test_cleanup_by_date(self):
        """Test cleanup functionality for specific dates."""
        yesterday = get_yesterday_date()
        today = get_today_date()

        # Insert test data
        self.db.insert_search_result(
            topic="Test Topic",
            title="Yesterday Article",
            rss_url="http://example.com/1",
            source="Test Source",
            rss_date="Mon, 01 Jan 2024 00:00:00 GMT",
            published_date=yesterday,
        )

        self.db.insert_search_result(
            topic="Test Topic",
            title="Today Article",
            rss_url="http://example.com/2",
            source="Test Source",
            rss_date="Tue, 02 Jan 2024 00:00:00 GMT",
            published_date=today,
        )

        # Verify data exists
        all_articles = self.db.get_unprocessed_articles()
        self.assertEqual(len(all_articles), 2)

        # Clean yesterday's data
        result = self.db.cleanup_data_from_date(yesterday)
        self.assertEqual(result["search_deleted"], 1)

        # Verify only today's data remains
        remaining_articles = self.db.get_unprocessed_articles()
        self.assertEqual(len(remaining_articles), 1)
        self.assertEqual(remaining_articles[0]["title"], "Today Article")

    def test_cleanup_older_than_days(self):
        """Test cleanup functionality for data older than N days."""
        # Insert test data for different dates
        dates = []
        for i in range(5):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            dates.append(date)

            self.db.insert_search_result(
                topic="Test Topic",
                title=f"Article from {date}",
                rss_url=f"http://example.com/{i}",
                source="Test Source",
                rss_date="Mon, 01 Jan 2024 00:00:00 GMT",
                published_date=date,
            )

        # Verify all data exists
        all_articles = self.db.get_unprocessed_articles()
        self.assertEqual(len(all_articles), 5)

        # Clean data older than 3 days
        result = self.db.cleanup_data_older_than_days(3)
        self.assertEqual(
            result["search_deleted"], 2
        )  # Should delete 2 articles older than 3 days

        # Verify only recent data remains
        remaining_articles = self.db.get_unprocessed_articles()
        self.assertEqual(len(remaining_articles), 3)  # Should have 3 articles remaining

    def test_scraper_date_filtering(self):
        """Test that the scraper uses date filtering."""
        yesterday = get_yesterday_date()

        # Create scraper with specific date
        scraper = ArticleScraper(target_date=yesterday)

        # Verify target date is set correctly
        self.assertEqual(scraper.target_date, yesterday)

        # Test that get_unprocessed_articles uses date filtering
        # (This would require actual data in the database to test fully)

    def test_summarizer_date_filtering(self):
        """Test that the summarizer uses date filtering."""
        yesterday = get_yesterday_date()

        # Create summarizer with specific date
        summarizer = ArticleSummarizer(target_date=yesterday)

        # Verify target date is set correctly
        self.assertEqual(summarizer.target_date, yesterday)

    def test_audio_generator_date_filtering(self):
        """Test that the audio generator uses date filtering."""
        yesterday = get_yesterday_date()

        # Create audio generator with specific date
        generator = AudioGenerator(target_date=yesterday)

        # Verify target date is set correctly
        self.assertEqual(generator.target_date, yesterday)

    def test_data_stats(self):
        """Test data statistics functionality."""
        yesterday = get_yesterday_date()

        # Insert test data
        self.db.insert_search_result(
            topic="Test Topic",
            title="Test Article",
            rss_url="http://example.com/1",
            source="Test Source",
            rss_date="Mon, 01 Jan 2024 00:00:00 GMT",
            published_date=yesterday,
        )

        # Get stats for yesterday
        stats = self.db.get_data_stats_by_date(yesterday)

        # Verify stats structure
        self.assertIn("search_records", stats)
        self.assertIn("article_records", stats)
        self.assertIn("processed_articles", stats)
        self.assertIn("summarized_articles", stats)
        self.assertIn("audio_articles", stats)

        # Verify search records count
        self.assertEqual(stats["search_records"], 1)


if __name__ == "__main__":
    unittest.main()
