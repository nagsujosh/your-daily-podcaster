#!/usr/bin/env python3
"""
Data Management Utility

Provides comprehensive date-based data management functions for the podcast pipeline.
Supports cleaning, statistics, and maintenance operations.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict

from dotenv import load_dotenv

from yourdaily.utils.db import DatabaseManager
from yourdaily.utils.logger import get_logger, setup_logger
from yourdaily.utils.time import get_today_date, get_yesterday_date


class DataManager:
    def __init__(self):
        """Initialize the data manager."""
        load_dotenv()

        # Setup logging
        self.logger = get_logger("DataManager")

        # Initialize database
        self.db = DatabaseManager(
            search_db_path=os.getenv("SEARCH_DB_PATH", "data/db/search_index.db"),
            article_db_path=os.getenv("ARTICLE_DB_PATH", "data/db/article_data.db"),
        )

    def get_data_stats_for_date(self, target_date: str) -> Dict[str, int]:
        """Get comprehensive statistics for a specific date."""
        try:
            stats = self.db.get_data_stats_by_date(target_date)
            self.logger.info(f"Data statistics for {target_date}:")
            for key, value in stats.items():
                self.logger.info(f"  {key}: {value}")
            return stats
        except Exception as e:
            self.logger.error(f"Error getting stats for {target_date}: {e}")
            return {}

    def get_data_stats_for_date_range(
        self, start_date: str, end_date: str
    ) -> Dict[str, Dict[str, int]]:
        """Get statistics for a range of dates."""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            stats = {}
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                stats[date_str] = self.get_data_stats_for_date(date_str)
                current += timedelta(days=1)

            return stats
        except Exception as e:
            self.logger.error(
                f"Error getting stats for date range {start_date} to {end_date}: {e}"
            )
            return {}

    def cleanup_data_from_date(self, target_date: str) -> Dict[str, int]:
        """Clean all data from a specific date."""
        try:
            self.logger.info(f"Cleaning all data from {target_date}")
            result = self.db.cleanup_data_from_date(target_date)

            if result["search_deleted"] > 0 or result["article_deleted"] > 0:
                self.logger.info(
                    f"Cleaned {result['search_deleted']} search records and {result['article_deleted']} article records"
                )
            else:
                self.logger.info(f"No data found to clean from {target_date}")

            return result
        except Exception as e:
            self.logger.error(f"Error cleaning data from {target_date}: {e}")
            return {"search_deleted": 0, "article_deleted": 0}

    def cleanup_data_older_than_days(self, days: int) -> Dict[str, int]:
        """Clean data older than specified days."""
        try:
            self.logger.info(f"Cleaning data older than {days} days")
            result = self.db.cleanup_data_older_than_days(days)

            if result["search_deleted"] > 0 or result["article_deleted"] > 0:
                self.logger.info(
                    f"Cleaned {result['search_deleted']} search records and {result['article_deleted']} article records"
                )
            else:
                self.logger.info(f"No data found to clean older than {days} days")

            return result
        except Exception as e:
            self.logger.error(f"Error cleaning old data: {e}")
            return {"search_deleted": 0, "article_deleted": 0}

    def cleanup_yesterday_data(self) -> Dict[str, int]:
        """Clean all data from yesterday."""
        yesterday = get_yesterday_date()
        return self.cleanup_data_from_date(yesterday)

    def cleanup_old_data_automatic(self, days: int = 3) -> Dict[str, int]:
        """Automatically clean data older than specified days (default: 3 days)."""
        return self.cleanup_data_older_than_days(days)

    def get_database_info(self) -> Dict[str, Any]:
        """Get comprehensive database information."""
        try:
            info = {}

            # Get stats for recent dates
            today = get_today_date()
            yesterday = get_yesterday_date()

            info["today_stats"] = self.get_data_stats_for_date(today)
            info["yesterday_stats"] = self.get_data_stats_for_date(yesterday)

            # Get stats for last 7 days
            info["last_7_days"] = self.get_data_stats_for_date_range(
                (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"), today
            )

            return info
        except Exception as e:
            self.logger.error(f"Error getting database info: {e}")
            return {}

    def run_maintenance(self) -> Dict[str, Any]:
        """Run comprehensive data maintenance."""
        try:
            self.logger.info("Starting data maintenance")

            # Get current database info
            initial_info = self.get_database_info()

            # Clean old data (older than 3 days)
            cleanup_result = self.cleanup_old_data_automatic(3)

            # Get final database info
            final_info = self.get_database_info()

            return {
                "success": True,
                "cleanup_result": cleanup_result,
                "initial_info": initial_info,
                "final_info": final_info,
            }
        except Exception as e:
            self.logger.error(f"Error during maintenance: {e}")
            return {"success": False, "error": str(e)}

    def prepare_for_yesterday_processing(self) -> Dict[str, Any]:
        """Prepare the system for processing yesterday's data by cleaning old data."""
        try:
            self.logger.info("Preparing for yesterday's data processing")

            # Clean data older than 3 days
            cleanup_result = self.cleanup_old_data_automatic(3)

            # Get yesterday's stats
            yesterday_stats = self.get_data_stats_for_date(get_yesterday_date())

            return {
                "success": True,
                "cleanup_result": cleanup_result,
                "yesterday_stats": yesterday_stats,
            }
        except Exception as e:
            self.logger.error(f"Error preparing for yesterday processing: {e}")
            return {"success": False, "error": str(e)}


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Data Management Utility")
    parser.add_argument(
        "--action",
        choices=["stats", "clean", "maintenance", "prepare"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD format)")
    parser.add_argument(
        "--days", type=int, default=3, help="Number of days for cleanup operations"
    )
    parser.add_argument(
        "--start-date", type=str, help="Start date for range operations"
    )
    parser.add_argument("--end-date", type=str, help="End date for range operations")

    args = parser.parse_args()

    # Setup logging
    setup_logger()
    logger = get_logger("main")

    try:
        manager = DataManager()

        if args.action == "stats":
            if args.date:
                stats = manager.get_data_stats_for_date(args.date)
                logger.info(f"Statistics for {args.date}: {stats}")
            elif args.start_date and args.end_date:
                stats = manager.get_data_stats_for_date_range(
                    args.start_date, args.end_date
                )
                logger.info(
                    f"Statistics for range {args.start_date} to {args.end_date}: {stats}"
                )
            else:
                info = manager.get_database_info()
                logger.info(f"Database information: {info}")

        elif args.action == "clean":
            if args.date:
                result = manager.cleanup_data_from_date(args.date)
                logger.info(f"Cleanup result: {result}")
            else:
                result = manager.cleanup_old_data_automatic(args.days)
                logger.info(f"Cleanup result: {result}")

        elif args.action == "maintenance":
            result = manager.run_maintenance()
            logger.info(f"Maintenance result: {result}")

        elif args.action == "prepare":
            result = manager.prepare_for_yesterday_processing()
            logger.info(f"Preparation result: {result}")

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
