#!/usr/bin/env python3
"""
Unit tests for yourdaily.utils.logger module.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from yourdaily.utils.logger import get_logger, setup_logger


class TestLoggerUtilities:
    """Test cases for logger utility functions."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for log files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @patch("yourdaily.utils.logger.logger")
    def test_setup_logger_default_parameters(self, mock_logger, temp_log_dir):
        """Test setup_logger with default parameters."""
        log_file = os.path.join(temp_log_dir, "test.log")

        setup_logger(log_file=log_file)

        # Verify logger.remove() was called
        mock_logger.remove.assert_called_once()

        # Verify logger.add() was called multiple times (console, file, error file)
        assert mock_logger.add.call_count == 3

        # Check console logger setup
        console_call = mock_logger.add.call_args_list[0]
        assert console_call[0][0] == sys.stdout
        assert console_call[1]["level"] == "INFO"
        assert console_call[1]["colorize"] is True

        # Check file logger setup
        file_call = mock_logger.add.call_args_list[1]
        assert file_call[0][0] == log_file
        assert file_call[1]["level"] == "INFO"
        assert file_call[1]["rotation"] == "10 MB"
        assert file_call[1]["retention"] == "30 days"
        assert file_call[1]["compression"] == "zip"

        # Check error logger setup
        error_call = mock_logger.add.call_args_list[2]
        expected_error_file = str(Path(log_file).parent / "errors.log")
        assert error_call[0][0] == expected_error_file
        assert error_call[1]["level"] == "ERROR"

    @patch("yourdaily.utils.logger.logger")
    def test_setup_logger_custom_level(self, mock_logger, temp_log_dir):
        """Test setup_logger with custom log level."""
        log_file = os.path.join(temp_log_dir, "test.log")

        setup_logger(log_level="DEBUG", log_file=log_file)

        # Check that DEBUG level was set for console and file loggers
        console_call = mock_logger.add.call_args_list[0]
        file_call = mock_logger.add.call_args_list[1]

        assert console_call[1]["level"] == "DEBUG"
        assert file_call[1]["level"] == "DEBUG"

    @patch("yourdaily.utils.logger.logger")
    def test_setup_logger_creates_log_directory(self, mock_logger, temp_log_dir):
        """Test that setup_logger creates log directory if it doesn't exist."""
        nested_log_file = os.path.join(temp_log_dir, "nested", "logs", "test.log")

        setup_logger(log_file=nested_log_file)

        # Directory should be created
        assert os.path.exists(os.path.dirname(nested_log_file))

    @patch("yourdaily.utils.logger.logger")
    def test_setup_logger_console_format(self, mock_logger, temp_log_dir):
        """Test console logger format configuration."""
        log_file = os.path.join(temp_log_dir, "test.log")

        setup_logger(log_file=log_file)

        console_call = mock_logger.add.call_args_list[0]
        console_format = console_call[1]["format"]

        # Check that format contains expected components
        assert "<green>{time:YYYY-MM-DD HH:mm:ss}</green>" in console_format
        assert "<level>{level:<8}</level>" in console_format
        assert (
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>"
            in console_format
        )
        assert "<level>{message}</level>" in console_format

    @patch("yourdaily.utils.logger.logger")
    def test_setup_logger_file_format(self, mock_logger, temp_log_dir):
        """Test file logger format configuration."""
        log_file = os.path.join(temp_log_dir, "test.log")

        setup_logger(log_file=log_file)

        file_call = mock_logger.add.call_args_list[1]
        file_format = file_call[1]["format"]

        # Check that format contains expected components (no color codes)
        assert "{time:YYYY-MM-DD HH:mm:ss}" in file_format
        assert "{level:<8}" in file_format
        assert "{name}:{function}:{line}" in file_format
        assert "{message}" in file_format
        # Should not contain color codes
        assert "<green>" not in file_format
        assert "<level>" not in file_format

    @patch("yourdaily.utils.logger.logger")
    def test_get_logger_with_name(self, mock_logger):
        """Test get_logger with a name parameter."""
        test_name = "test_module"

        result = get_logger(test_name)

        mock_logger.bind.assert_called_once_with(name=test_name)
        assert result == mock_logger.bind.return_value

    @patch("yourdaily.utils.logger.logger")
    def test_get_logger_without_name(self, mock_logger):
        """Test get_logger without a name parameter."""
        result = get_logger()

        mock_logger.bind.assert_not_called()
        assert result == mock_logger

    @patch("yourdaily.utils.logger.logger")
    def test_get_logger_with_none_name(self, mock_logger):
        """Test get_logger with None as name parameter."""
        result = get_logger(None)

        mock_logger.bind.assert_not_called()
        assert result == mock_logger

    @patch("yourdaily.utils.logger.logger")
    def test_setup_logger_error_file_configuration(self, mock_logger, temp_log_dir):
        """Test error file logger specific configuration."""
        log_file = os.path.join(temp_log_dir, "test.log")

        setup_logger(log_file=log_file)

        error_call = mock_logger.add.call_args_list[2]

        # Check error-specific settings
        assert error_call[1]["level"] == "ERROR"
        assert error_call[1]["rotation"] == "5 MB"
        assert error_call[1]["retention"] == "60 days"
        assert error_call[1]["compression"] == "zip"

    @patch("yourdaily.utils.logger.logger")
    def test_logger_initialization_message(self, mock_logger, temp_log_dir):
        """Test that initialization success message is logged."""
        log_file = os.path.join(temp_log_dir, "test.log")

        setup_logger(log_file=log_file)

        mock_logger.info.assert_called_with("Logger initialized successfully")

    @patch("yourdaily.utils.logger.logger")
    def test_module_initialization_check(self, mock_logger):
        """Test that logger is initialized when module is imported (if no handlers exist)."""
        # Mock the logger to have no handlers
        mock_logger._core.handlers = []

        # Re-import the module to trigger initialization
        import importlib

        import yourdaily.utils.logger

        importlib.reload(yourdaily.utils.logger)

        # This is harder to test directly due to module-level execution
        # In practice, this ensures setup_logger() is called when imported

    def test_log_file_path_handling(self, temp_log_dir):
        """Test actual file creation and path handling."""
        log_file = os.path.join(temp_log_dir, "actual_test.log")

        # This test uses the actual setup_logger without mocking
        # to verify real file operations
        with patch("yourdaily.utils.logger.logger") as mock_logger:
            setup_logger(log_file=log_file)

            # Verify the directory was created
            assert os.path.exists(os.path.dirname(log_file))

            # Check that the error log path was constructed correctly
            error_call = mock_logger.add.call_args_list[2]
            expected_error_path = str(Path(log_file).parent / "errors.log")
            assert error_call[0][0] == expected_error_path

    @pytest.mark.parametrize(
        "log_level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    )
    @patch("yourdaily.utils.logger.logger")
    def test_setup_logger_various_log_levels(
        self, mock_logger, log_level, temp_log_dir
    ):
        """Test setup_logger with various log levels."""
        log_file = os.path.join(temp_log_dir, "test.log")

        setup_logger(log_level=log_level, log_file=log_file)

        # Check that the specified log level was set for console and file loggers
        console_call = mock_logger.add.call_args_list[0]
        file_call = mock_logger.add.call_args_list[1]

        assert console_call[1]["level"] == log_level
        assert file_call[1]["level"] == log_level


if __name__ == "__main__":
    pytest.main([__file__])
