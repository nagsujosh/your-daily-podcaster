#!/usr/bin/env python3
"""
Main Pipeline Orchestrator

Runs the complete podcast generation pipeline from start to finish
"""

import sys
import time
from typing import Any, Dict

from dotenv import load_dotenv

from yourdaily.utils.logger import get_logger, setup_logger


class PipelineOrchestrator:
    def __init__(self):
        """Initialize the pipeline orchestrator."""
        load_dotenv()

        # Setup logging
        self.logger = get_logger("PipelineOrchestrator")

        # Pipeline modules
        self.modules = [
            ("News Fetching", "yourdaily.scraper.fetch_search_results"),
            ("Article Scraping", "yourdaily.scraper.scrape_articles"),
            (
                "Article Summarization",
                "yourdaily.summarizer.summarize_articles",
            ),
            ("Audio Generation", "yourdaily.tts.generate_audio"),
            ("Podcast Publishing", "yourdaily.publisher.publish_to_spotify"),
            ("Cleanup", "yourdaily.cleaner.cleanup"),
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

            # Run the main function
            if hasattr(module, "main"):
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

            # Small delay between modules
            time.sleep(1)

        # Calculate total duration
        total_duration = time.time() - self.start_time

        # Generate summary
        successful_modules = sum(1 for r in self.results.values() if r["success"])
        failed_modules = len(self.results) - successful_modules

        self.logger.info("=" * 60)
        self.logger.info("Pipeline Summary")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Duration: {round(total_duration, 2)}s")
        self.logger.info(
            f"Successful Modules: {successful_modules}/{len(self.modules)}"
        )
        self.logger.info(f"Failed Modules: {failed_modules}")

        # Log individual module results
        for module_name, result in self.results.items():
            status = "✅" if result["success"] else "❌"
            self.logger.info(f"{status} {module_name}: {result['duration']}s")
            if result.get("error"):
                self.logger.error(f"   Error: {result['error']}")

        # Overall success (all modules succeeded)
        overall_success = all(r["success"] for r in self.results.values())

        if overall_success:
            self.logger.info("Pipeline completed successfully!")
        else:
            self.logger.warning("Pipeline completed with some failures")

        return {
            "success": overall_success,
            "total_duration": round(total_duration, 2),
            "successful_modules": successful_modules,
            "total_modules": len(self.modules),
            "results": self.results,
        }


def main():
    """Main entry point."""
    # Setup logging
    setup_logger()
    logger = get_logger("main")

    try:
        orchestrator = PipelineOrchestrator()
        result = orchestrator.run()

        if result["success"]:
            logger.info("Complete pipeline executed successfully!")
            sys.exit(0)
        else:
            logger.warning("Pipeline completed with some failures")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Pipeline failed with unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
