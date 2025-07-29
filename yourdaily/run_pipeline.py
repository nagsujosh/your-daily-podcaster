#!/usr/bin/env python3
"""
Main Pipeline Orchestrator

Runs the complete podcast generation pipeline from start to finish
Now supports yesterday-only processing with automatic cleanup
"""

import sys
import time
from typing import Any, Dict

from dotenv import load_dotenv

from yourdaily.utils.logger import get_logger, setup_logger
from yourdaily.utils.time import get_yesterday_date


class PipelineOrchestrator:
    def __init__(self, target_date: str = None):
        """Initialize the pipeline orchestrator."""
        load_dotenv()

        # Setup logging
        self.logger = get_logger("PipelineOrchestrator")

        # Date filtering - default to yesterday if not specified
        self.target_date = target_date or get_yesterday_date()
        self.logger.info(f"Pipeline target date: {self.target_date}")

        # Pipeline modules with date-aware configuration
        self.modules = [
            ("Pre-Cleanup", "yourdaily.cleaner.cleanup"),
            ("News Fetching", "yourdaily.scraper.fetch_search_results"),
            ("Article Scraping", "yourdaily.scraper.scrape_articles"),
            (
                "Article Summarization",
                "yourdaily.summarizer.summarize_articles",
            ),
            ("Audio Generation", "yourdaily.tts.generate_audio"),
            ("Podcast Publishing", "yourdaily.publisher.publish_to_spotify"),
            ("Post-Cleanup", "yourdaily.cleaner.cleanup"),
        ]

        self.start_time = None
        self.results = {}

    def run_module(self, module_name: str, module_path: str) -> Dict[str, Any]:
        """Run a single pipeline module."""
        try:
            self.logger.info(f"Starting {module_name}...")
            module_start = time.time()

            # Import and run the module
            import importlib

            module = importlib.import_module(module_path)

            # Run the main function with date parameter if supported
            if hasattr(module, "main"):
                # Check if the module supports date parameter
                if module_name in [
                    "Article Scraping",
                    "Article Summarization",
                    "Audio Generation",
                ]:
                    # For date-aware modules, we'll need to modify their main functions
                    # For now, run the standard main function
                    module.main()
                else:
                    module.main()
                success = True
                error = None
            else:
                success = False
                error = f"No main function found in {module_path}"

            module_duration = time.time() - module_start

            result = {
                "success": success,
                "duration": round(module_duration, 2),
                "error": error,
            }

            if success:
                self.logger.info(
                    f"✅ {module_name} completed successfully in "
                    f"{result['duration']}s"
                )
            else:
                self.logger.error(f"❌ {module_name} failed: {error}")

            return result

        except Exception as e:
            self.logger.error(f"❌ {module_name} failed with exception: {e}")
            return {"success": False, "duration": 0, "error": str(e)}

    def run(self) -> Dict[str, Any]:
        """Run the complete pipeline."""
        self.start_time = time.time()

        self.logger.info("=" * 60)
        self.logger.info("Starting Your Daily Podcaster Pipeline")
        self.logger.info(f"Target Date: {self.target_date}")
        self.logger.info("=" * 60)

        # Run each module in sequence
        for module_name, module_path in self.modules:
            result = self.run_module(module_name, module_path)
            self.results[module_name] = result

            # If a module fails, we can choose to continue or stop
            if not result["success"]:
                self.logger.warning(
                    f"Module {module_name} failed, but continuing with pipeline..."
                )

        # Calculate total duration
        total_duration = time.time() - self.start_time

        # Summary
        successful_modules = sum(1 for r in self.results.values() if r["success"])
        total_modules = len(self.modules)

        self.logger.info("=" * 60)
        self.logger.info("Pipeline Summary")
        self.logger.info("=" * 60)
        self.logger.info(f"Target Date: {self.target_date}")
        self.logger.info(f"Total Duration: {round(total_duration, 2)}s")
        self.logger.info(f"Successful Modules: {successful_modules}/{total_modules}")

        # Detailed results
        for module_name, result in self.results.items():
            status = "✅" if result["success"] else "❌"
            self.logger.info(
                f"{status} {module_name}: {result['duration']}s "
                f"({result.get('error', 'Success')})"
            )

        return {
            "success": successful_modules == total_modules,
            "target_date": self.target_date,
            "total_duration": round(total_duration, 2),
            "successful_modules": successful_modules,
            "total_modules": total_modules,
            "results": self.results,
        }


def main():
    """Main entry point."""
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Run the complete podcast generation pipeline"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Target date for processing (YYYY-MM-DD format, defaults to yesterday)",
    )
    args = parser.parse_args()

    # Setup logging
    setup_logger()
    logger = get_logger("main")

    logger.info("=" * 60)
    logger.info("Starting Your Daily Podcaster Pipeline")
    logger.info("=" * 60)

    try:
        orchestrator = PipelineOrchestrator(target_date=args.date)
        result = orchestrator.run()

        if result["success"]:
            logger.info("Pipeline completed successfully")
            logger.info(
                f"Results: {result['successful_modules']}/{result['total_modules']} "
                f"modules successful in {result['total_duration']}s"
            )
        else:
            logger.error("Pipeline failed")
            logger.error(
                f"Only {result['successful_modules']}/{result['total_modules']} "
                f"modules completed successfully"
            )
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
