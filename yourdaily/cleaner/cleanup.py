#!/usr/bin/env python3
"""
Cleanup Utility

Removes temporary audio files and cleans article data while preserving metadata.
Now supports date-based cleanup and yesterday-only processing.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from yourdaily.utils.db import DatabaseManager
from yourdaily.utils.logger import get_logger, setup_logger
from yourdaily.utils.time import get_yesterday_date


class CleanupUtility:
    def __init__(self):
        """Initialize the cleanup utility."""
        load_dotenv()

        # Setup logging
        self.logger = get_logger("CleanupUtility")

        # Initialize database
        search_path = os.getenv("SEARCH_DB_PATH", "data/db/search_index.db")
        article_path = os.getenv("ARTICLE_DB_PATH", "data/db/article_data.db")
        self.db = DatabaseManager(
            search_db_path=search_path,
            article_db_path=article_path,
        )

        # Directories
        self.audio_dir = Path(os.getenv("AUDIO_OUTPUT_DIR", "data/audio"))
        self.temp_dir = Path(os.getenv("TEMP_AUDIO_DIR", "data/audio/temp"))
        self.logs_dir = Path("logs")

        # Cleanup settings
        self.keep_final_audio_days = 7  # Keep final podcasts for 7 days
        self.cleanup_old_data_days = (
            3  # Clean article data older than 3 days (reduced from 7)
        )

    def cleanup_temp_audio_files(self) -> int:
        """Remove temporary audio files."""
        try:
            if not self.temp_dir.exists():
                self.logger.info("Temp audio directory does not exist")
                return 0

            removed_count = 0

            # Remove all files in temp directory
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        removed_count += 1
                        self.logger.debug(f"Removed temp file: {file_path.name}")
                    except Exception as e:
                        self.logger.warning(
                            f"Could not remove temp file {file_path.name}: " f"{e}"
                        )

            self.logger.info(f"Removed {removed_count} temporary audio files")
            return removed_count

        except Exception as e:
            self.logger.error(f"Error cleaning temp audio files: {e}")
            return 0

    def cleanup_old_final_audio(self) -> int:
        """Remove old final audio files (keep recent ones)."""
        try:
            if not self.audio_dir.exists():
                self.logger.info("Audio directory does not exist")
                return 0

            cutoff_date = datetime.now() - timedelta(days=self.keep_final_audio_days)
            removed_count = 0

            # Find daily digest files
            for file_path in self.audio_dir.glob("daily_digest_*.mp3"):
                try:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                    if mtime < cutoff_date:
                        file_path.unlink()
                        removed_count += 1
                        self.logger.info(f"Removed old audio file: {file_path.name}")

                except Exception as e:
                    self.logger.warning(f"Could not process file {file_path.name}: {e}")

            self.logger.info(f"Removed {removed_count} old final audio files")
            return removed_count

        except Exception as e:
            self.logger.error(f"Error cleaning old final audio: {e}")
            return 0

    def cleanup_old_metadata_files(self) -> int:
        """Remove old metadata files."""
        try:
            if not self.audio_dir.exists():
                return 0

            cutoff_date = datetime.now() - timedelta(days=self.keep_final_audio_days)
            removed_count = 0

            # Find metadata files
            for file_path in self.audio_dir.glob("metadata_*.json"):
                try:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                    if mtime < cutoff_date:
                        file_path.unlink()
                        removed_count += 1
                        self.logger.info(f"Removed old metadata file: {file_path.name}")

                except Exception as e:
                    self.logger.warning(
                        f"Could not process metadata file {file_path.name}: " f"{e}"
                    )

            self.logger.info(f"Removed {removed_count} old metadata files")
            return removed_count

        except Exception as e:
            self.logger.error(f"Error cleaning old metadata files: {e}")
            return 0

    def cleanup_database_content(self) -> Dict[str, int]:
        """Clean old content from database while preserving metadata."""
        try:
            # Clean old article data (keep search metadata)
            success = self.db.cleanup_old_data(self.cleanup_old_data_days)

            if success:
                self.logger.info(
                    f"Cleaned article data older than "
                    f"{self.cleanup_old_data_days} days"
                )
                return {"cleaned_articles": 1}
            else:
                self.logger.warning("Failed to clean old article data")
                return {"cleaned_articles": 0}

        except Exception as e:
            self.logger.error(f"Error cleaning database content: {e}")
            return {"cleaned_articles": 0}

    def cleanup_old_logs(self) -> int:
        """Remove old log files."""
        try:
            if not self.logs_dir.exists():
                return 0

            cutoff_date = datetime.now() - timedelta(days=30)  # Keep logs for 30 days
            removed_count = 0

            # Find log files
            for file_path in self.logs_dir.glob("*.log*"):
                try:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                    if mtime < cutoff_date:
                        file_path.unlink()
                        removed_count += 1
                        self.logger.info(f"Removed old log file: {file_path.name}")

                except Exception as e:
                    self.logger.warning(
                        f"Could not process log file {file_path.name}: " f"{e}"
                    )

            self.logger.info(f"Removed {removed_count} old log files")
            return removed_count

        except Exception as e:
            self.logger.error(f"Error cleaning old logs: {e}")
            return 0

    def cleanup_data_from_date(self, target_date: str) -> Dict[str, int]:
        """Clean all data from a specific date from both databases."""
        try:
            self.logger.info(f"Cleaning all data from {target_date}")
            result = self.db.cleanup_data_from_date(target_date)

            if result["search_deleted"] > 0 or result["article_deleted"] > 0:
                self.logger.info(
                    f"Cleaned {result['search_deleted']} search records and "
                    f"{result['article_deleted']} article records from {target_date}"
                )
            else:
                self.logger.info(f"No data found to clean from {target_date}")

            return result

        except Exception as e:
            self.logger.error(f"Error cleaning data from date {target_date}: {e}")
            return {"search_deleted": 0, "article_deleted": 0}

    def cleanup_old_data_by_days(self, days: int) -> Dict[str, int]:
        """Clean data older than specified days from both databases."""
        try:
            self.logger.info(f"Cleaning data older than {days} days")
            result = self.db.cleanup_data_older_than_days(days)

            if result["search_deleted"] > 0 or result["article_deleted"] > 0:
                self.logger.info(
                    f"Cleaned {result['search_deleted']} search records and "
                    f"{result['article_deleted']} article records older than "
                    f"{days} days"
                )
            else:
                self.logger.info(f"No data found to clean older than {days} days")

            return result

        except Exception as e:
            self.logger.error(f"Error cleaning old data: {e}")
            return {"search_deleted": 0, "article_deleted": 0}

    def get_data_stats_for_date(self, target_date: str) -> Dict[str, int]:
        """Get statistics about data for a specific date."""
        try:
            stats = self.db.get_data_stats_by_date(target_date)
            self.logger.info(f"Data stats for {target_date}: {stats}")
            return stats
        except Exception as e:
            self.logger.error(f"Error getting stats for date {target_date}: {e}")
            return {}

    def cleanup_yesterday_data(self) -> Dict[str, int]:
        """Clean all data from yesterday (useful for fresh start)."""
        yesterday = get_yesterday_date()
        return self.cleanup_data_from_date(yesterday)

    def cleanup_old_data_automatic(self) -> Dict[str, int]:
        """Automatically clean data older than the configured threshold."""
        return self.cleanup_old_data_by_days(self.cleanup_old_data_days)

    def get_disk_usage_info(self) -> Dict[str, Any]:
        """Get information about disk usage."""
        try:
            info = {}

            # Audio directory size
            if self.audio_dir.exists():
                total_size = sum(
                    f.stat().st_size for f in self.audio_dir.rglob("*") if f.is_file()
                )
                info["audio_dir_size_mb"] = round(total_size / (1024 * 1024), 2)
                info["audio_files_count"] = len(list(self.audio_dir.rglob("*.mp3")))

            # Temp directory size
            if self.temp_dir.exists():
                total_size = sum(
                    f.stat().st_size for f in self.temp_dir.rglob("*") if f.is_file()
                )
                info["temp_dir_size_mb"] = round(total_size / (1024 * 1024), 2)
                info["temp_files_count"] = len(list(self.temp_dir.rglob("*")))

            # Database sizes
            search_db_path = Path(
                os.getenv("SEARCH_DB_PATH", "data/db/search_index.db")
            )
            article_db_path = Path(
                os.getenv("ARTICLE_DB_PATH", "data/db/article_data.db")
            )

            if search_db_path.exists():
                info["search_db_size_mb"] = round(
                    search_db_path.stat().st_size / (1024 * 1024), 2
                )

            if article_db_path.exists():
                info["article_db_size_mb"] = round(
                    article_db_path.stat().st_size / (1024 * 1024), 2
                )

            return info

        except Exception as e:
            self.logger.error(f"Error getting disk usage info: {e}")
            return {}

    def run(self) -> Dict[str, Any]:
        """Run the complete cleanup process."""
        self.logger.info("Starting cleanup process")

        # Get initial disk usage
        initial_usage = self.get_disk_usage_info()
        self.logger.info(f"Initial disk usage: {initial_usage}")

        # Perform cleanup tasks
        results = {
            "temp_audio_files_removed": self.cleanup_temp_audio_files(),
            "old_final_audio_removed": self.cleanup_old_final_audio(),
            "old_metadata_files_removed": self.cleanup_old_metadata_files(),
            "old_logs_removed": self.cleanup_old_logs(),
            "database_cleaned": self.cleanup_database_content(),
            "old_data_cleaned": self.cleanup_old_data_automatic(),
        }

        # Get final disk usage
        final_usage = self.get_disk_usage_info()
        self.logger.info(f"Final disk usage: {final_usage}")

        # Calculate space saved
        space_saved = 0
        if "temp_dir_size_mb" in initial_usage and "temp_dir_size_mb" in final_usage:
            space_saved += (
                initial_usage["temp_dir_size_mb"] - final_usage["temp_dir_size_mb"]
            )

        self.logger.info(f"Cleanup complete. Space saved: {space_saved:.2f} MB")

        return {
            "success": True,
            "results": results,
            "space_saved_mb": round(space_saved, 2),
            "initial_usage": initial_usage,
            "final_usage": final_usage,
        }


def main():
    """Main entry point."""
    # Setup logging
    setup_logger()
    logger = get_logger("main")

    logger.info("=" * 50)
    logger.info("Starting Cleanup Utility")
    logger.info("=" * 50)

    try:
        cleanup = CleanupUtility()
        result = cleanup.run()

        if result["success"]:
            logger.info("Cleanup completed successfully")
            logger.info(f"Space saved: {result['space_saved_mb']} MB")

            # Log detailed results
            for key, value in result["results"].items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        logger.info(f"  {key}.{sub_key}: {sub_value}")
                else:
                    logger.info(f"  {key}: {value}")
        else:
            logger.error("Cleanup failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
