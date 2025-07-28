import sys
from pathlib import Path

from loguru import logger


def setup_logger(log_level: str = "INFO", log_file: str = "logs/podcaster.log"):
    """Setup standardized logging configuration."""

    # Remove default logger
    logger.remove()

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Console logger with colors
    logger.add(
        sys.stdout,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        level=log_level,
        colorize=True,
    )

    # File logger with rotation
    logger.add(
        log_file,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | "
            "{name}:{function}:{line} - {message}"
        ),
        level=log_level,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
    )

    # Error file logger
    error_log_file = log_path.parent / "errors.log"
    logger.add(
        str(error_log_file),
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | "
            "{name}:{function}:{line} - {message}"
        ),
        level="ERROR",
        rotation="5 MB",
        retention="60 days",
        compression="zip",
    )

    logger.info("Logger initialized successfully")


def get_logger(name: str = None):
    """Get a logger instance with the specified name."""
    if name:
        return logger.bind(name=name)
    return logger


# Initialize logger when module is imported
if not logger._core.handlers:
    setup_logger()
