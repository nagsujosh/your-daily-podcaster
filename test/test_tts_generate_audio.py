#!/usr/bin/env python3
"""
Unit tests for yourdaily.tts.generate_audio module.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from yourdaily.tts.generate_audio import AudioGenerator


class TestAudioGenerator:
    """Test cases for AudioGenerator class."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_dir = os.path.join(temp_dir, "audio")
            temp_audio_dir = os.path.join(temp_dir, "audio", "temp")
            search_db = os.path.join(temp_dir, "search.db")
            article_db = os.path.join(temp_dir, "articles.db")
            yield {
                "audio_dir": audio_dir,
                "temp_audio_dir": temp_audio_dir,
                "search_db": search_db,
                "article_db": article_db,
            }

    @pytest.fixture
    def mock_env_vars(self, temp_dirs):
        """Mock environment variables."""
        with patch.dict(
            os.environ,
            {
                "AUDIO_OUTPUT_DIR": temp_dirs["audio_dir"],
                "TEMP_AUDIO_DIR": temp_dirs["temp_audio_dir"],
                "SEARCH_DB_PATH": temp_dirs["search_db"],
                "ARTICLE_DB_PATH": temp_dirs["article_db"],
                "GCLOUD_TTS_CREDS": "/path/to/credentials.json",
            },
        ):
            yield

    @patch("yourdaily.tts.generate_audio.DatabaseManager")
    @patch("yourdaily.tts.generate_audio.load_dotenv")
    def test_init_success(self, mock_load_dotenv, mock_db_manager, mock_env_vars):
        """Test successful AudioGenerator initialization."""
        with patch.object(AudioGenerator, "init_tts_client"):
            generator = AudioGenerator()

            mock_load_dotenv.assert_called_once()
            mock_db_manager.assert_called_once()

            assert generator.voice_name == "en-US-Neural2-F"
            assert generator.speaking_rate == 0.9
            assert Path(generator.audio_dir).exists()
            assert Path(generator.temp_dir).exists()

    @patch("yourdaily.tts.generate_audio.TTS_AVAILABLE", False)
    def test_init_tts_client_unavailable(self):
        """Test TTS client initialization when TTS is unavailable."""
        with patch.object(AudioGenerator, "__init__", lambda x: None):
            generator = AudioGenerator()
            generator.logger = MagicMock()
            generator.tts_client = None

            generator.init_tts_client()

            generator.logger.error.assert_called_with("Google Cloud TTS not available")
            assert generator.tts_client is None

    @patch("yourdaily.tts.generate_audio.TTS_AVAILABLE", True)
    @patch("yourdaily.tts.generate_audio.texttospeech")
    @patch("yourdaily.tts.generate_audio.service_account")
    def test_init_tts_client_with_credentials(
        self, mock_service_account, mock_tts, mock_env_vars
    ):
        """Test TTS client initialization with service account credentials."""
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = (
            mock_credentials
        )
        mock_client = MagicMock()
        mock_tts.TextToSpeechClient.return_value = mock_client

        with patch("os.path.exists", return_value=True), patch.object(
            AudioGenerator, "__init__", lambda x: None
        ):
            generator = AudioGenerator()
            generator.logger = MagicMock()
            generator.tts_client = None

            generator.init_tts_client()

            assert generator.tts_client == mock_client
            mock_service_account.Credentials.from_service_account_file.assert_called_once()

    @patch("yourdaily.tts.generate_audio.TTS_AVAILABLE", True)
    @patch("yourdaily.tts.generate_audio.texttospeech")
    def test_init_tts_client_default_credentials(self, mock_tts):
        """Test TTS client initialization with default credentials."""
        mock_client = MagicMock()
        mock_tts.TextToSpeechClient.return_value = mock_client

        with patch.dict(os.environ, {}, clear=True), patch.object(
            AudioGenerator, "__init__", lambda x: None
        ):
            generator = AudioGenerator()
            generator.logger = MagicMock()
            generator.tts_client = None

            generator.init_tts_client()

            assert generator.tts_client == mock_client

    @patch("yourdaily.tts.generate_audio.TTS_AVAILABLE", True)
    @patch("yourdaily.tts.generate_audio.texttospeech")
    def test_init_tts_client_exception(self, mock_tts):
        """Test TTS client initialization with exception."""
        mock_tts.TextToSpeechClient.side_effect = Exception("TTS Error")

        with patch.object(AudioGenerator, "__init__", lambda x: None):
            generator = AudioGenerator()
            generator.logger = MagicMock()
            generator.tts_client = None

            generator.init_tts_client()

            assert generator.tts_client is None
            generator.logger.error.assert_called()

    def test_get_articles_for_audio(self):
        """Test getting articles for audio generation."""
        mock_db = MagicMock()
        mock_articles = [
            {"id": 1, "title": "Test Article", "summarized_text": "Summary"}
        ]
        mock_db.get_articles_for_audio.return_value = mock_articles

        generator = AudioGenerator()
        generator.db = mock_db

        result = generator.get_articles_for_audio()

        assert result == mock_articles
        mock_db.get_articles_for_audio.assert_called_once()

    def test_group_summaries_by_topic(self):
        """Test grouping summaries by topic."""
        articles = [
            {"topic": "Technology", "summarized_text": "Tech summary 1"},
            {"topic": "Business", "summarized_text": "Business summary"},
            {
                "topic": "Technology",
                "summarized_text": "Tech summary 2",
            },  # Should be ignored (duplicate topic)
            {
                "topic": "Science",
                "summarized_text": "",
            },  # Should be ignored (empty summary)
        ]

        generator = AudioGenerator()
        result = generator.group_summaries_by_topic(articles)

        assert len(result) == 2
        assert result["Technology"] == "Tech summary 1"
        assert result["Business"] == "Business summary"
        assert "Science" not in result

    @patch("yourdaily.tts.generate_audio.get_yesterday_date")
    def test_create_intro_text(self, mock_yesterday):
        """Test creation of intro text."""
        mock_yesterday.return_value = "2024-01-15"

        generator = AudioGenerator()
        result = generator.create_intro_text("2024-01-15")

        assert "2024-01-15" in result
        assert "news digest" in result.lower()

    def test_create_outro_text(self):
        """Test creation of outro text."""
        generator = AudioGenerator()
        result = generator.create_outro_text()

        assert "thank you" in result.lower()
        assert "daily news digest" in result.lower()

    @patch("yourdaily.tts.generate_audio.TTS_AVAILABLE", True)
    @patch("yourdaily.tts.generate_audio.texttospeech")
    def test_text_to_speech_success(self, mock_tts):
        """Test successful text-to-speech conversion."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.audio_content = b"audio_data"
        mock_client.synthesize_speech.return_value = mock_response

        generator = AudioGenerator()
        generator.tts_client = mock_client
        generator.temp_dir = Path("/tmp/test")

        with patch("builtins.open", mock_open()) as mock_file:
            result = generator.text_to_speech("Test text", "test.mp3")

        assert result is not None
        mock_client.synthesize_speech.assert_called_once()
        mock_file.assert_called_once()

    def test_text_to_speech_no_client(self):
        """Test text-to-speech when client is not available."""
        generator = AudioGenerator()
        generator.tts_client = None
        generator.logger = MagicMock()

        result = generator.text_to_speech("Test text", "test.mp3")

        assert result is None
        generator.logger.error.assert_called_with("TTS client not available")

    @patch("yourdaily.tts.generate_audio.TTS_AVAILABLE", True)
    @patch("yourdaily.tts.generate_audio.texttospeech")
    def test_text_to_speech_exception(self, mock_tts):
        """Test text-to-speech with exception."""
        mock_client = MagicMock()
        mock_client.synthesize_speech.side_effect = Exception("TTS Error")

        generator = AudioGenerator()
        generator.tts_client = mock_client
        generator.logger = MagicMock()

        result = generator.text_to_speech("Test text", "test.mp3")

        assert result is None
        generator.logger.error.assert_called()

    @patch("yourdaily.tts.generate_audio.AUDIO_AVAILABLE", True)
    @patch("yourdaily.tts.generate_audio.AudioSegment")
    def test_merge_audio_files_success(self, mock_audio_segment):
        """Test successful audio file merging."""
        mock_audio = MagicMock()
        mock_combined = MagicMock()
        mock_pause = MagicMock()

        mock_audio_segment.empty.return_value = mock_combined
        mock_audio_segment.from_mp3.return_value = mock_audio
        mock_audio_segment.silent.return_value = mock_pause

        generator = AudioGenerator()
        generator.audio_dir = Path("/tmp/audio")
        generator.logger = MagicMock()

        with patch("os.path.exists", return_value=True):
            result = generator.merge_audio_files(
                ["file1.mp3", "file2.mp3"], "output.mp3"
            )

        assert result is not None
        mock_combined.export.assert_called_once()

    @patch("yourdaily.tts.generate_audio.AUDIO_AVAILABLE", False)
    def test_merge_audio_files_unavailable(self):
        """Test audio merging when audio processing is unavailable."""
        generator = AudioGenerator()
        generator.logger = MagicMock()

        result = generator.merge_audio_files(["file1.mp3"], "output.mp3")

        assert result is None
        generator.logger.error.assert_called_with(
            "Audio processing not available (pydub)"
        )

    @patch("yourdaily.tts.generate_audio.AUDIO_AVAILABLE", True)
    @patch("yourdaily.tts.generate_audio.AudioSegment")
    def test_merge_audio_files_exception(self, mock_audio_segment):
        """Test audio merging with exception."""
        mock_audio_segment.empty.side_effect = Exception("Audio error")

        generator = AudioGenerator()
        generator.logger = MagicMock()

        result = generator.merge_audio_files(["file1.mp3"], "output.mp3")

        assert result is None
        generator.logger.error.assert_called()

    def test_generate_topic_audio_success(self):
        """Test successful topic audio generation."""
        mock_db = MagicMock()
        mock_articles = [{"url": "https://example.com/1", "topic": "Technology"}]
        mock_db.get_articles_for_audio.return_value = mock_articles
        mock_db.update_audio_generated.return_value = True

        generator = AudioGenerator()
        generator.db = mock_db

        with patch.object(
            generator, "text_to_speech", return_value="/path/to/audio.mp3"
        ):
            result = generator.generate_topic_audio("Technology", "Tech summary")

        assert result == "/path/to/audio.mp3"
        mock_db.update_audio_generated.assert_called_once()

    def test_generate_topic_audio_tts_failure(self):
        """Test topic audio generation when TTS fails."""
        generator = AudioGenerator()

        with patch.object(generator, "text_to_speech", return_value=None):
            result = generator.generate_topic_audio("Technology", "Tech summary")

        assert result is None

    def test_generate_topic_audio_exception(self):
        """Test topic audio generation with exception."""
        generator = AudioGenerator()
        generator.logger = MagicMock()

        with patch.object(
            generator, "text_to_speech", side_effect=Exception("Audio error")
        ):
            result = generator.generate_topic_audio("Technology", "Tech summary")

        assert result is None
        generator.logger.error.assert_called()

    def test_run_no_tts_client(self):
        """Test run method when TTS client is not available."""
        generator = AudioGenerator()
        generator.tts_client = None
        generator.logger = MagicMock()

        result = generator.run()

        assert result["success"] is False
        assert "TTS client not available" in result["error"]

    def test_run_no_articles(self):
        """Test run method when no articles need audio generation."""
        generator = AudioGenerator()
        generator.tts_client = MagicMock()

        with patch.object(generator, "get_articles_for_audio", return_value=[]):
            result = generator.run()

        assert result["success"] is True
        assert result["topics_processed"] == 0
        assert result["audio_files_generated"] == 0

    @patch("yourdaily.tts.generate_audio.time.sleep")
    @patch("yourdaily.tts.generate_audio.get_yesterday_date")
    def test_run_success(self, mock_yesterday, mock_sleep):
        """Test successful run of audio generator."""
        mock_yesterday.return_value = "2024-01-15"

        mock_articles = [
            {"topic": "Technology", "summarized_text": "Tech summary"},
            {"topic": "Business", "summarized_text": "Business summary"},
        ]

        generator = AudioGenerator()
        generator.tts_client = MagicMock()

        with patch.object(
            generator, "get_articles_for_audio", return_value=mock_articles
        ), patch.object(
            generator, "generate_topic_audio", return_value="/path/to/audio.mp3"
        ), patch.object(
            generator, "text_to_speech", return_value="/path/to/intro.mp3"
        ), patch.object(
            generator, "merge_audio_files", return_value="/path/to/final.mp3"
        ):
            result = generator.run()

        assert result["success"] is True
        assert result["topics_processed"] == 2
        assert result["topics_successful"] == 2
        assert result["topics_failed"] == 0
        assert result["final_audio_path"] == "/path/to/final.mp3"

        # Check rate limiting (sleep called once for 2 topics)
        mock_sleep.assert_called_once_with(1)

    @patch("yourdaily.tts.generate_audio.time.sleep")
    @patch("yourdaily.tts.generate_audio.get_yesterday_date")
    def test_run_with_failures(self, mock_yesterday, mock_sleep):
        """Test run with some topic failures."""
        mock_yesterday.return_value = "2024-01-15"

        mock_articles = [
            {"topic": "Technology", "summarized_text": "Tech summary"},
            {"topic": "Business", "summarized_text": "Business summary"},
        ]

        generator = AudioGenerator()
        generator.tts_client = MagicMock()

        with patch.object(
            generator, "get_articles_for_audio", return_value=mock_articles
        ), patch.object(
            generator, "generate_topic_audio"
        ) as mock_generate, patch.object(
            generator, "text_to_speech", return_value="/path/to/intro.mp3"
        ), patch.object(
            generator, "merge_audio_files", return_value="/path/to/final.mp3"
        ):
            # First succeeds, second fails
            mock_generate.side_effect = ["/path/to/audio.mp3", None]

            result = generator.run()

        assert result["success"] is True
        assert result["topics_processed"] == 2
        assert result["topics_successful"] == 1
        assert result["topics_failed"] == 1

    @patch("yourdaily.tts.generate_audio.setup_logger")
    @patch("yourdaily.tts.generate_audio.get_logger")
    def test_main_function_success(self, mock_get_logger, mock_setup_logger):
        """Test main function successful execution."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.tts.generate_audio.AudioGenerator"
        ) as mock_generator_class:
            mock_generator = MagicMock()
            mock_generator.run.return_value = {
                "success": True,
                "audio_files_generated": 3,
                "topics_successful": 2,
                "final_audio_path": "/path/to/final.mp3",
            }
            mock_generator_class.return_value = mock_generator

            from yourdaily.tts.generate_audio import main

            # Should not raise SystemExit
            try:
                main()
                success = True
            except SystemExit as e:
                success = e.code == 0

            assert success
            mock_setup_logger.assert_called_once()

    @patch("yourdaily.tts.generate_audio.setup_logger")
    @patch("yourdaily.tts.generate_audio.get_logger")
    @patch("yourdaily.tts.generate_audio.sys.exit")
    def test_main_function_failure(self, mock_exit, mock_get_logger, mock_setup_logger):
        """Test main function with generator failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.tts.generate_audio.AudioGenerator"
        ) as mock_generator_class:
            mock_generator = MagicMock()
            mock_generator.run.return_value = {
                "success": False,
                "error": "TTS client not available",
            }
            mock_generator_class.return_value = mock_generator

            from yourdaily.tts.generate_audio import main

            main()

            mock_exit.assert_called_with(1)

    @patch("yourdaily.tts.generate_audio.setup_logger")
    @patch("yourdaily.tts.generate_audio.get_logger")
    @patch("yourdaily.tts.generate_audio.sys.exit")
    def test_main_function_exception(
        self, mock_exit, mock_get_logger, mock_setup_logger
    ):
        """Test main function with unexpected exception."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.tts.generate_audio.AudioGenerator"
        ) as mock_generator_class:
            mock_generator_class.side_effect = Exception("Unexpected error")

            from yourdaily.tts.generate_audio import main

            main()

            mock_exit.assert_called_with(1)
            mock_logger.error.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])
