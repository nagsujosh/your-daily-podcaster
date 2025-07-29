#!/usr/bin/env python3
"""
Unit tests for yourdaily.run_pipeline module.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from yourdaily.run_pipeline import PipelineOrchestrator, main


class TestPipelineOrchestrator:
    """Test cases for PipelineOrchestrator class."""

    @patch("yourdaily.run_pipeline.load_dotenv")
    def test_init(self, mock_load_dotenv):
        """Test PipelineOrchestrator initialization."""
        orchestrator = PipelineOrchestrator()

        mock_load_dotenv.assert_called_once()

        # Check that modules list is properly initialized
        assert len(orchestrator.modules) == 6
        expected_modules = [
            ("News Fetching", "yourdaily.scraper.fetch_search_results"),
            ("Article Scraping", "yourdaily.scraper.scrape_articles"),
            ("Article Summarization", "yourdaily.summarizer.summarize_articles"),
            ("Audio Generation", "yourdaily.tts.generate_audio"),
            ("Podcast Publishing", "yourdaily.publisher.publish_to_spotify"),
            ("Cleanup", "yourdaily.cleaner.cleanup"),
        ]

        assert orchestrator.modules == expected_modules
        assert orchestrator.start_time is None
        assert orchestrator.results == {}

    @patch("yourdaily.run_pipeline.time.time")
    @patch("yourdaily.run_pipeline.importlib.import_module")
    def test_run_module_success_with_main_function(self, mock_import, mock_time):
        """Test successful module execution with main function."""
        mock_time.side_effect = [1000.0, 1005.0]  # Start and end times

        # Mock module with main function
        mock_module = MagicMock()
        mock_module.main = MagicMock()
        mock_import.return_value = mock_module

        orchestrator = PipelineOrchestrator()

        result = orchestrator.run_module("Test Module", "test.module")

        assert result["success"] is True
        assert result["duration"] == 5.0
        assert result["error"] is None
        mock_module.main.assert_called_once()

    @patch("yourdaily.run_pipeline.time.time")
    @patch("yourdaily.run_pipeline.importlib.import_module")
    def test_run_module_no_main_function(self, mock_import, mock_time):
        """Test module execution when no main function exists."""
        mock_time.side_effect = [1000.0, 1002.0]

        # Mock module without main function
        mock_module = MagicMock()
        del mock_module.main  # Remove main attribute
        mock_import.return_value = mock_module

        orchestrator = PipelineOrchestrator()

        result = orchestrator.run_module("Test Module", "test.module")

        assert result["success"] is False
        assert result["duration"] == 2.0
        assert "No main function found" in result["error"]

    @patch("yourdaily.run_pipeline.time.time")
    @patch("yourdaily.run_pipeline.importlib.import_module")
    def test_run_module_import_error(self, mock_import, mock_time):
        """Test module execution with import error."""
        mock_time.side_effect = [1000.0, 1001.0]
        mock_import.side_effect = ImportError("Module not found")

        orchestrator = PipelineOrchestrator()

        result = orchestrator.run_module("Test Module", "nonexistent.module")

        assert result["success"] is False
        assert result["duration"] == 0
        assert "Module not found" in result["error"]

    @patch("yourdaily.run_pipeline.time.time")
    @patch("yourdaily.run_pipeline.importlib.import_module")
    def test_run_module_execution_error(self, mock_import, mock_time):
        """Test module execution when main function raises exception."""
        mock_time.side_effect = [1000.0, 1003.0]

        # Mock module with main function that raises exception
        mock_module = MagicMock()
        mock_module.main.side_effect = RuntimeError("Execution failed")
        mock_import.return_value = mock_module

        orchestrator = PipelineOrchestrator()

        result = orchestrator.run_module("Test Module", "test.module")

        assert result["success"] is False
        assert result["duration"] == 0
        assert "Execution failed" in result["error"]

    @patch("yourdaily.run_pipeline.time.sleep")
    @patch("yourdaily.run_pipeline.time.time")
    def test_run_complete_success(self, mock_time, mock_sleep):
        """Test complete pipeline run with all modules succeeding."""
        # Mock time for overall duration
        mock_time.side_effect = [1000.0, 1030.0]  # 30 seconds total

        orchestrator = PipelineOrchestrator()

        # Mock successful module execution
        mock_results = {"success": True, "duration": 5.0, "error": None}

        with patch.object(
            orchestrator, "run_module", return_value=mock_results
        ) as mock_run_module:
            result = orchestrator.run()

        # Should call run_module for each of the 6 modules
        assert mock_run_module.call_count == 6

        # Check sleep was called between modules (5 times for 6 modules)
        assert mock_sleep.call_count == 5
        mock_sleep.assert_called_with(1)

        # Check final result
        assert result["success"] is True
        assert result["total_duration"] == 30.0
        assert result["successful_modules"] == 6
        assert result["total_modules"] == 6

    @patch("yourdaily.run_pipeline.time.sleep")
    @patch("yourdaily.run_pipeline.time.time")
    def test_run_with_some_failures(self, mock_time, mock_sleep):
        """Test pipeline run with some module failures."""
        mock_time.side_effect = [1000.0, 1025.0]  # 25 seconds total

        orchestrator = PipelineOrchestrator()

        # Mock mixed success/failure results
        success_result = {"success": True, "duration": 3.0, "error": None}
        failure_result = {"success": False, "duration": 2.0, "error": "Module failed"}

        with patch.object(orchestrator, "run_module") as mock_run_module:
            # Alternate between success and failure
            mock_run_module.side_effect = [
                success_result,
                failure_result,
                success_result,
                failure_result,
                success_result,
                success_result,
            ]

            result = orchestrator.run()

        assert result["success"] is False  # Overall failure due to some failed modules
        assert result["successful_modules"] == 4
        assert result["total_modules"] == 6

    @patch("yourdaily.run_pipeline.time.sleep")
    @patch("yourdaily.run_pipeline.time.time")
    def test_run_all_failures(self, mock_time, mock_sleep):
        """Test pipeline run when all modules fail."""
        mock_time.side_effect = [1000.0, 1015.0]

        orchestrator = PipelineOrchestrator()

        failure_result = {
            "success": False,
            "duration": 1.0,
            "error": "All modules failed",
        }

        with patch.object(orchestrator, "run_module", return_value=failure_result):
            result = orchestrator.run()

        assert result["success"] is False
        assert result["successful_modules"] == 0
        assert result["total_modules"] == 6

    def test_module_list_completeness(self):
        """Test that all expected modules are in the pipeline."""
        orchestrator = PipelineOrchestrator()

        module_names = [name for name, _ in orchestrator.modules]

        expected_names = [
            "News Fetching",
            "Article Scraping",
            "Article Summarization",
            "Audio Generation",
            "Podcast Publishing",
            "Cleanup",
        ]

        assert module_names == expected_names

    def test_module_paths_correctness(self):
        """Test that module paths are correct."""
        orchestrator = PipelineOrchestrator()

        module_paths = [path for _, path in orchestrator.modules]

        expected_paths = [
            "yourdaily.scraper.fetch_search_results",
            "yourdaily.scraper.scrape_articles",
            "yourdaily.summarizer.summarize_articles",
            "yourdaily.tts.generate_audio",
            "yourdaily.publisher.publish_to_spotify",
            "yourdaily.cleaner.cleanup",
        ]

        assert module_paths == expected_paths


class TestMainFunction:
    """Test cases for the main function."""

    @patch("yourdaily.run_pipeline.setup_logger")
    @patch("yourdaily.run_pipeline.get_logger")
    @patch("yourdaily.run_pipeline.sys.exit")
    def test_main_success(self, mock_exit, mock_get_logger, mock_setup_logger):
        """Test main function with successful pipeline execution."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.run_pipeline.PipelineOrchestrator"
        ) as mock_orchestrator_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator.run.return_value = {"success": True}
            mock_orchestrator_class.return_value = mock_orchestrator

            main()

            mock_setup_logger.assert_called_once()
            mock_orchestrator.run.assert_called_once()
            mock_exit.assert_called_with(0)

    @patch("yourdaily.run_pipeline.setup_logger")
    @patch("yourdaily.run_pipeline.get_logger")
    @patch("yourdaily.run_pipeline.sys.exit")
    def test_main_pipeline_failure(self, mock_exit, mock_get_logger, mock_setup_logger):
        """Test main function with pipeline failure."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.run_pipeline.PipelineOrchestrator"
        ) as mock_orchestrator_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator.run.return_value = {"success": False}
            mock_orchestrator_class.return_value = mock_orchestrator

            main()

            mock_exit.assert_called_with(1)

    @patch("yourdaily.run_pipeline.setup_logger")
    @patch("yourdaily.run_pipeline.get_logger")
    @patch("yourdaily.run_pipeline.sys.exit")
    def test_main_unexpected_exception(
        self, mock_exit, mock_get_logger, mock_setup_logger
    ):
        """Test main function with unexpected exception."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.run_pipeline.PipelineOrchestrator"
        ) as mock_orchestrator_class:
            mock_orchestrator_class.side_effect = Exception("Unexpected error")

            main()

            mock_logger.error.assert_called()
            mock_exit.assert_called_with(1)

    @patch("yourdaily.run_pipeline.setup_logger")
    @patch("yourdaily.run_pipeline.get_logger")
    def test_main_logging_setup(self, mock_get_logger, mock_setup_logger):
        """Test that main function sets up logging correctly."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.run_pipeline.PipelineOrchestrator"
        ) as mock_orchestrator_class, patch("yourdaily.run_pipeline.sys.exit"):
            mock_orchestrator = MagicMock()
            mock_orchestrator.run.return_value = {"success": True}
            mock_orchestrator_class.return_value = mock_orchestrator

            main()

            mock_setup_logger.assert_called_once()
            mock_get_logger.assert_called_with("main")

    @patch("yourdaily.run_pipeline.setup_logger")
    @patch("yourdaily.run_pipeline.get_logger")
    @patch("yourdaily.run_pipeline.sys.exit")
    def test_main_orchestrator_initialization(
        self, mock_exit, mock_get_logger, mock_setup_logger
    ):
        """Test that main function initializes orchestrator correctly."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch(
            "yourdaily.run_pipeline.PipelineOrchestrator"
        ) as mock_orchestrator_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator.run.return_value = {"success": True}
            mock_orchestrator_class.return_value = mock_orchestrator

            main()

            mock_orchestrator_class.assert_called_once()
            mock_orchestrator.run.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
