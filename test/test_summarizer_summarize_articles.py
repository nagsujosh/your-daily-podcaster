#!/usr/bin/env python3
"""
Unit tests for yourdaily.summarizer.summarize_articles module.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from yourdaily.summarizer.summarize_articles import ArticleSummarizer


class TestArticleSummarizer:
    """Test cases for ArticleSummarizer class."""

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
            os.environ,
            {
                "SEARCH_DB_PATH": search_db,
                "ARTICLE_DB_PATH": article_db,
                "GEMINI_KEY": "test_api_key",
            },
        ):
            yield

    @patch("yourdaily.summarizer.summarize_articles.DatabaseManager")
    @patch("yourdaily.summarizer.summarize_articles.load_dotenv")
    def test_init_success(self, mock_load_dotenv, mock_db_manager, mock_env_vars):
        """Test successful ArticleSummarizer initialization."""
        summarizer = ArticleSummarizer()

        mock_load_dotenv.assert_called_once()
        mock_db_manager.assert_called_once()

        assert summarizer.gemini_api_key == "test_api_key"
        assert summarizer.request_delay == 1
        assert "gemini-pro:generateContent" in summarizer.gemini_url

    @patch("yourdaily.summarizer.summarize_articles.DatabaseManager")
    @patch("yourdaily.summarizer.summarize_articles.load_dotenv")
    def test_init_missing_api_key(self, mock_load_dotenv, mock_db_manager):
        """Test initialization failure when GEMINI_KEY is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GEMINI_KEY not found"):
                ArticleSummarizer()

    def test_get_articles_for_summarization(self):
        """Test getting articles for summarization."""
        mock_db = MagicMock()
        mock_articles = [{"id": 1, "title": "Test Article", "clean_text": "Content"}]
        mock_db.get_articles_for_summarization.return_value = mock_articles

        summarizer = ArticleSummarizer()
        summarizer.db = mock_db

        result = summarizer.get_articles_for_summarization()

        assert result == mock_articles
        mock_db.get_articles_for_summarization.assert_called_once()

    def test_group_articles_by_topic(self):
        """Test grouping articles by topic."""
        articles = [
            {"topic": "Technology", "title": "Tech Article 1"},
            {"topic": "Business", "title": "Business Article 1"},
            {"topic": "Technology", "title": "Tech Article 2"},
            {"title": "No Topic Article"},  # Should default to "General"
        ]

        summarizer = ArticleSummarizer()
        result = summarizer.group_articles_by_topic(articles)

        assert len(result) == 3
        assert len(result["Technology"]) == 2
        assert len(result["Business"]) == 1
        assert len(result["General"]) == 1

    @patch("yourdaily.summarizer.summarize_articles.get_yesterday_date")
    def test_create_summary_prompt(self, mock_yesterday):
        """Test creation of summary prompt."""
        mock_yesterday.return_value = "2024-01-15"

        articles = [
            {
                "title": "Test Article 1",
                "source": "Test Source 1",
                "clean_text": "This is test content 1",
            },
            {
                "title": "Test Article 2",
                "source": "Test Source 2",
                "clean_text": "This is test content 2",
            },
        ]

        summarizer = ArticleSummarizer()
        prompt = summarizer.create_summary_prompt("Technology", articles, "2024-01-15")

        assert "Technology" in prompt
        assert "2024-01-15" in prompt
        assert "Test Article 1" in prompt
        assert "Test Article 2" in prompt
        assert "This is test content 1" in prompt
        assert "This is test content 2" in prompt
        assert "--- Article 1 ---" in prompt
        assert "--- Article 2 ---" in prompt

    @patch("yourdaily.summarizer.summarize_articles.requests.post")
    def test_call_gemini_api_success(self, mock_post):
        """Test successful Gemini API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Generated summary text"}]}}]
        }
        mock_post.return_value = mock_response

        summarizer = ArticleSummarizer()
        summarizer.gemini_api_key = "test_key"

        result = summarizer.call_gemini_api("Test prompt")

        assert result == "Generated summary text"
        mock_post.assert_called_once()

        # Check request parameters
        call_args = mock_post.call_args
        assert "key=test_key" in call_args[1]["url"]
        assert call_args[1]["json"]["contents"][0]["parts"][0]["text"] == "Test prompt"

    @patch("yourdaily.summarizer.summarize_articles.requests.post")
    def test_call_gemini_api_request_exception(self, mock_post):
        """Test Gemini API call with request exception."""
        mock_post.side_effect = Exception("Network error")

        summarizer = ArticleSummarizer()
        summarizer.gemini_api_key = "test_key"

        result = summarizer.call_gemini_api("Test prompt")

        assert result is None

    @patch("yourdaily.summarizer.summarize_articles.requests.post")
    def test_call_gemini_api_unexpected_response(self, mock_post):
        """Test Gemini API call with unexpected response format."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"unexpected": "format"}
        mock_post.return_value = mock_response

        summarizer = ArticleSummarizer()
        summarizer.gemini_api_key = "test_key"

        result = summarizer.call_gemini_api("Test prompt")

        assert result is None

    def test_summarize_topic_articles_success(self):
        """Test successful topic summarization."""
        articles = [{"title": "Test Article", "clean_text": "Test content"}]

        summarizer = ArticleSummarizer()

        with patch.object(
            summarizer, "create_summary_prompt", return_value="Test prompt"
        ), patch.object(
            summarizer, "call_gemini_api", return_value="Generated summary"
        ):
            result = summarizer.summarize_topic_articles("Technology", articles)

        assert result == "Generated summary"

    def test_summarize_topic_articles_api_failure(self):
        """Test topic summarization when API call fails."""
        articles = [{"title": "Test Article", "clean_text": "Test content"}]

        summarizer = ArticleSummarizer()

        with patch.object(
            summarizer, "create_summary_prompt", return_value="Test prompt"
        ), patch.object(summarizer, "call_gemini_api", return_value=None):
            result = summarizer.summarize_topic_articles("Technology", articles)

        assert result is None

    def test_summarize_topic_articles_exception(self):
        """Test topic summarization with exception."""
        articles = [{"title": "Test Article", "clean_text": "Test content"}]

        summarizer = ArticleSummarizer()

        with patch.object(
            summarizer, "create_summary_prompt", side_effect=Exception("Test error")
        ):
            result = summarizer.summarize_topic_articles("Technology", articles)

        assert result is None

    def test_store_summaries_success(self):
        """Test successful summary storage."""
        mock_db = MagicMock()
        mock_db.get_articles_for_summarization.return_value = [
            {
                "url": "https://example.com/1",
                "topic": "Technology",
                "clean_text": "Content 1",
            },
            {
                "url": "https://example.com/2",
                "topic": "Technology",
                "clean_text": "Content 2",
            },
            {
                "url": "https://example.com/3",
                "topic": "Business",
                "clean_text": "Content 3",
            },
        ]
        mock_db.insert_article_data.return_value = True

        summarizer = ArticleSummarizer()
        summarizer.db = mock_db

        topic_summaries = {"Technology": "Tech summary", "Business": "Business summary"}

        stored_count = summarizer.store_summaries(topic_summaries)

        assert stored_count == 3
        assert mock_db.insert_article_data.call_count == 3

    def test_store_summaries_database_error(self):
        """Test summary storage with database errors."""
        mock_db = MagicMock()
        mock_db.get_articles_for_summarization.return_value = [
            {
                "url": "https://example.com/1",
                "topic": "Technology",
                "clean_text": "Content",
            }
        ]
        mock_db.insert_article_data.side_effect = Exception("DB Error")

        summarizer = ArticleSummarizer()
        summarizer.db = mock_db

        topic_summaries = {"Technology": "Tech summary"}

        stored_count = summarizer.store_summaries(topic_summaries)

        assert stored_count == 0

    def test_run_no_articles(self):
        """Test run method when no articles need summarization."""
        summarizer = ArticleSummarizer()

        with patch.object(
            summarizer, "get_articles_for_summarization", return_value=[]
        ):
            result = summarizer.run()

        assert result["success"] is True
        assert result["topics_processed"] == 0
        assert result["summaries_generated"] == 0

    @patch("yourdaily.summarizer.summarize_articles.time.sleep")
    def test_run_success(self, mock_sleep):
        """Test successful run of the summarizer."""
        mock_articles = [
            {
                "topic": "Technology",
                "title": "Tech Article",
                "clean_text": "Tech content",
            },
            {
                "topic": "Business",
                "title": "Business Article",
                "clean_text": "Business content",
            },
        ]

        summarizer = ArticleSummarizer()

        with patch.object(
            summarizer, "get_articles_for_summarization", return_value=mock_articles
        ), patch.object(
            summarizer, "summarize_topic_articles", return_value="Generated summary"
        ), patch.object(
            summarizer, "store_summaries", return_value=2
        ):
            result = summarizer.run()

        assert result["success"] is True
        assert result["topics_processed"] == 2
        assert result["topics_successful"] == 2
        assert result["topics_failed"] == 0
        assert result["summaries_stored"] == 2

        # Check rate limiting (sleep called once for 2 topics)
        mock_sleep.assert_called_once_with(1)

    @patch("yourdaily.summarizer.summarize_articles.time.sleep")
    def test_run_with_failures(self, mock_sleep):
        """Test run with some topic failures."""
        mock_articles = [
            {
                "topic": "Technology",
                "title": "Tech Article",
                "clean_text": "Tech content",
            },
            {
                "topic": "Business",
                "title": "Business Article",
                "clean_text": "Business content",
            },
            {
                "topic": "Science",
                "title": "Science Article",
                "clean_text": "Science content",
            },
        ]

        summarizer = ArticleSummarizer()

        with patch.object(
            summarizer, "get_articles_for_summarization", return_value=mock_articles
        ), patch.object(
            summarizer, "summarize_topic_articles"
        ) as mock_summarize, patch.object(
            summarizer, "store_summaries", return_value=2
        ):
            # First succeeds, second fails, third succeeds
            mock_summarize.side_effect = ["Summary 1", None, "Summary 3"]

            result = summarizer.run()

        assert result["success"] is True
        assert result["topics_processed"] == 3
        assert result["topics_successful"] == 2
        assert result["topics_failed"] == 1

    @patch("yourdaily.summarizer.summarize_articles.time.sleep")
    def test_run_with_exception(self, mock_sleep):
        """Test run method when topic processing raises exception."""
        mock_articles = [
            {
                "topic": "Technology",
                "title": "Tech Article",
                "clean_text": "Tech content",
            }
        ]

        summarizer = ArticleSummarizer()

        with patch.object(
            summarizer, "get_articles_for_summarization", return_value=mock_articles
        ), patch.object(
            summarizer,
            "summarize_topic_articles",
            side_effect=Exception("Processing error"),
        ), patch.object(
            summarizer, "store_summaries", return_value=0
        ):
            result = summarizer.run()

        assert result["success"] is True
        assert result["topics_processed"] == 1
        assert result["topics_successful"] == 0
        assert result["topics_failed"] == 1

    @patch("yourdaily.summarizer.summarize_articles.setup_logger")
    @patch("yourdaily.summarizer.summarize_articles.get_logger")
    def test_main_function_success(self, mock_get_logger, mock_setup_logger):
        """Test main function successful execution."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.summarizer.summarize_articles.ArticleSummarizer"
        ) as mock_summarizer_class:
            mock_summarizer = MagicMock()
            mock_summarizer.run.return_value = {
                "success": True,
                "summaries_stored": 5,
                "topics_successful": 3,
            }
            mock_summarizer_class.return_value = mock_summarizer

            from yourdaily.summarizer.summarize_articles import main

            # Should not raise SystemExit
            try:
                main()
                success = True
            except SystemExit as e:
                success = e.code == 0

            assert success
            mock_setup_logger.assert_called_once()

    @patch("yourdaily.summarizer.summarize_articles.setup_logger")
    @patch("yourdaily.summarizer.summarize_articles.get_logger")
    @patch("yourdaily.summarizer.summarize_articles.sys.exit")
    def test_main_function_failure(self, mock_exit, mock_get_logger, mock_setup_logger):
        """Test main function with summarizer failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.summarizer.summarize_articles.ArticleSummarizer"
        ) as mock_summarizer_class:
            mock_summarizer = MagicMock()
            mock_summarizer.run.return_value = {"success": False}
            mock_summarizer_class.return_value = mock_summarizer

            from yourdaily.summarizer.summarize_articles import main

            main()

            mock_exit.assert_called_with(1)

    @patch("yourdaily.summarizer.summarize_articles.setup_logger")
    @patch("yourdaily.summarizer.summarize_articles.get_logger")
    @patch("yourdaily.summarizer.summarize_articles.sys.exit")
    def test_main_function_exception(
        self, mock_exit, mock_get_logger, mock_setup_logger
    ):
        """Test main function with unexpected exception."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.summarizer.summarize_articles.ArticleSummarizer"
        ) as mock_summarizer_class:
            mock_summarizer_class.side_effect = Exception("Unexpected error")

            from yourdaily.summarizer.summarize_articles import main

            main()

            mock_exit.assert_called_with(1)
            mock_logger.error.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])
