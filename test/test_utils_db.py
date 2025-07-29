#!/usr/bin/env python3
"""
Unit tests for yourdaily.utils.db module.
"""

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yourdaily.utils.db import DatabaseManager


class TestDatabaseManager:
    """Test cases for DatabaseManager class."""

    @pytest.fixture
    def temp_db_paths(self):
        """Create temporary database file paths for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            search_db = os.path.join(temp_dir, "test_search.db")
            article_db = os.path.join(temp_dir, "test_articles.db")
            yield search_db, article_db

    @pytest.fixture
    def db_manager(self, temp_db_paths):
        """Create a DatabaseManager instance with temporary databases."""
        search_db, article_db = temp_db_paths
        return DatabaseManager(search_db, article_db)

    def test_init_creates_directories(self, temp_db_paths):
        """Test that DatabaseManager creates necessary directories."""
        search_db, article_db = temp_db_paths

        # Create nested directory structure
        nested_search_db = os.path.join(
            os.path.dirname(search_db), "nested", "search.db"
        )
        nested_article_db = os.path.join(
            os.path.dirname(article_db), "nested", "articles.db"
        )

        db_manager = DatabaseManager(nested_search_db, nested_article_db)

        assert os.path.exists(os.path.dirname(nested_search_db))
        assert os.path.exists(os.path.dirname(nested_article_db))

    def test_init_creates_search_index_table(self, db_manager, temp_db_paths):
        """Test that search_index table is created with correct schema."""
        search_db, _ = temp_db_paths

        with sqlite3.connect(search_db) as conn:
            cursor = conn.execute("PRAGMA table_info(search_index)")
            columns = [row[1] for row in cursor.fetchall()]

            expected_columns = [
                "id",
                "topic",
                "title",
                "rss_url",
                "real_url",
                "source",
                "rss_date",
                "published_date",
                "inserted_at",
            ]

            for col in expected_columns:
                assert col in columns

    def test_init_creates_article_data_table(self, db_manager, temp_db_paths):
        """Test that article_data table is created with correct schema."""
        _, article_db = temp_db_paths

        with sqlite3.connect(article_db) as conn:
            cursor = conn.execute("PRAGMA table_info(article_data)")
            columns = [row[1] for row in cursor.fetchall()]

            expected_columns = [
                "id",
                "rss_url",
                "real_url",
                "clean_text",
                "summarized_text",
                "audio_path",
                "summarized_at",
                "audio_generated",
            ]

            for col in expected_columns:
                assert col in columns

    def test_article_exists_true(self, db_manager):
        """Test article_exists returns True for existing article."""
        # Insert a test article
        success = db_manager.insert_search_result(
            topic="Test",
            title="Test Article",
            rss_url="https://example.com/test",
            source="Test Source",
            rss_date="2024-01-15",
            published_date="2024-01-15",
        )
        assert success

        # Check if it exists
        exists = db_manager.article_exists("https://example.com/test")
        assert exists is True

    def test_article_exists_false(self, db_manager):
        """Test article_exists returns False for non-existing article."""
        exists = db_manager.article_exists("https://nonexistent.com/article")
        assert exists is False

    @patch("yourdaily.utils.db.logger")
    def test_article_exists_error_handling(self, mock_logger, temp_db_paths):
        """Test article_exists handles database errors gracefully."""
        search_db, article_db = temp_db_paths

        # Create DatabaseManager with invalid path to cause error
        db_manager = DatabaseManager("/invalid/path/search.db", article_db)

        result = db_manager.article_exists("https://example.com/test")
        assert result is False
        mock_logger.error.assert_called()

    def test_insert_search_result_success(self, db_manager):
        """Test successful insertion of search result."""
        success = db_manager.insert_search_result(
            topic="Technology",
            title="AI Breakthrough",
            rss_url="https://example.com/ai-news",
            source="Tech News",
            rss_date="2024-01-15",
            published_date="2024-01-15",
            real_url="https://realnews.com/ai-breakthrough",
        )

        assert success is True

    def test_insert_search_result_duplicate_ignored(self, db_manager):
        """Test that duplicate RSS URLs are ignored."""
        # Insert first article
        success1 = db_manager.insert_search_result(
            topic="Tech",
            title="Article 1",
            rss_url="https://example.com/duplicate",
            source="Source 1",
            rss_date="2024-01-15",
            published_date="2024-01-15",
        )

        # Insert duplicate RSS URL
        success2 = db_manager.insert_search_result(
            topic="Tech",
            title="Article 2",
            rss_url="https://example.com/duplicate",  # Same RSS URL
            source="Source 2",
            rss_date="2024-01-15",
            published_date="2024-01-15",
        )

        assert success1 is True
        assert success2 is True  # Operation succeeds but doesn't insert duplicate

    def test_update_real_url_success(self, db_manager):
        """Test successful real URL update."""
        # Insert article first
        db_manager.insert_search_result(
            topic="Test",
            title="Test Article",
            rss_url="https://example.com/rss",
            source="Test Source",
            rss_date="2024-01-15",
            published_date="2024-01-15",
        )

        # Update real URL
        success = db_manager.update_real_url(
            "https://example.com/rss", "https://real-site.com/article"
        )

        assert success is True

    def test_get_unprocessed_articles(self, db_manager):
        """Test getting unprocessed articles."""
        # Insert search result but no article data
        db_manager.insert_search_result(
            topic="Test",
            title="Unprocessed Article",
            rss_url="https://example.com/unprocessed",
            source="Test Source",
            rss_date="2024-01-15",
            published_date="2024-01-15",
        )

        unprocessed = db_manager.get_unprocessed_articles()

        assert len(unprocessed) == 1
        assert unprocessed[0]["title"] == "Unprocessed Article"

    def test_insert_article_data_success(self, db_manager):
        """Test successful article data insertion."""
        success = db_manager.insert_article_data(
            rss_url="https://example.com/rss",
            real_url="https://real-site.com/article",
            clean_text="This is the cleaned article content.",
            summarized_text="This is a summary.",
            audio_path="/path/to/audio.mp3",
        )

        assert success is True

    def test_insert_article_data_requires_real_url(self, db_manager):
        """Test that article data insertion requires real_url."""
        success = db_manager.insert_article_data(
            rss_url="https://example.com/rss",
            clean_text="This is the cleaned article content."
            # Missing real_url
        )

        assert success is False

    def test_update_audio_generated_success(self, db_manager):
        """Test successful audio generation status update."""
        # Insert article data first
        db_manager.insert_article_data(
            real_url="https://real-site.com/article", clean_text="Test content"
        )

        # Update audio status
        success = db_manager.update_audio_generated(
            "https://real-site.com/article", "/path/to/audio.mp3"
        )

        assert success is True

    def test_get_articles_for_summarization(self, db_manager):
        """Test getting articles that need summarization."""
        # Insert article with clean text but no summary
        db_manager.insert_article_data(
            real_url="https://real-site.com/article",
            clean_text="This needs summarization",
        )

        articles = db_manager.get_articles_for_summarization()

        assert len(articles) == 1
        assert articles[0]["clean_text"] == "This needs summarization"
        assert articles[0]["summarized_text"] is None

    def test_get_articles_for_audio(self, db_manager):
        """Test getting articles that need audio generation."""
        # Insert article with summary but no audio
        db_manager.insert_article_data(
            real_url="https://real-site.com/article",
            clean_text="Test content",
            summarized_text="Test summary",
        )

        articles = db_manager.get_articles_for_audio()

        assert len(articles) == 1
        assert articles[0]["summarized_text"] == "Test summary"
        assert articles[0]["audio_generated"] == 0  # SQLite boolean as integer

    def test_get_all_audio_files(self, db_manager):
        """Test getting all audio file paths."""
        # Insert articles with and without audio
        db_manager.insert_article_data(
            real_url="https://site1.com/article", audio_path="/path/to/audio1.mp3"
        )

        db_manager.insert_article_data(
            real_url="https://site2.com/article", audio_path="/path/to/audio2.mp3"
        )

        db_manager.insert_article_data(
            real_url="https://site3.com/article"
            # No audio path
        )

        audio_files = db_manager.get_all_audio_files()

        assert len(audio_files) == 2
        assert "/path/to/audio1.mp3" in audio_files
        assert "/path/to/audio2.mp3" in audio_files

    def test_cleanup_old_data(self, db_manager):
        """Test cleanup of old data."""
        # This test would need to mock datetime to test properly
        success = db_manager.cleanup_old_data(days_to_keep=7)
        assert success is True

    @patch("yourdaily.utils.db.logger")
    def test_error_handling_in_methods(self, mock_logger, temp_db_paths):
        """Test error handling in various methods."""
        # Create DatabaseManager with invalid paths
        db_manager = DatabaseManager("/invalid/search.db", "/invalid/article.db")

        # Test various methods handle errors gracefully
        assert db_manager.insert_search_result("", "", "", "", "", "") is False
        assert db_manager.update_real_url("", "") is False
        assert db_manager.get_unprocessed_articles() == []
        assert db_manager.insert_article_data(real_url="test") is False
        assert db_manager.update_audio_generated("", "") is False
        assert db_manager.get_articles_for_summarization() == []
        assert db_manager.get_articles_for_audio() == []
        assert db_manager.get_all_audio_files() == []
        assert db_manager.cleanup_old_data() is False

        # Verify error logging occurred
        assert mock_logger.error.call_count > 0


if __name__ == "__main__":
    pytest.main([__file__])
