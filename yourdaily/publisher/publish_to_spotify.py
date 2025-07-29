#!/usr/bin/env python3
"""
Podcast Publisher

Generates RSS feeds and publishes podcasts to various platforms
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

from yourdaily.cleaner.cleanup import CleanupUtility
from yourdaily.utils.db import DatabaseManager
from yourdaily.utils.logger import get_logger, setup_logger
from yourdaily.utils.time import (
    format_duration,
    get_current_timestamp,
    get_yesterday_date,
)

# RSS feed generation
try:
    from feedgen.feed import FeedGenerator

    RSS_AVAILABLE = True
except ImportError:
    RSS_AVAILABLE = False


class PodcastPublisher:
    def __init__(self):
        """Initialize the podcast publisher."""
        load_dotenv()

        # Setup logging
        self.logger = get_logger("PodcastPublisher")

        # Initialize database
        search_path = os.getenv("SEARCH_DB_PATH", "data/db/search_index.db")
        article_path = os.getenv("ARTICLE_DB_PATH", "data/db/article_data.db")
        self.db = DatabaseManager(
            search_db_path=search_path,
            article_db_path=article_path,
        )

        # Audio directories
        self.audio_dir = Path(os.getenv("AUDIO_OUTPUT_DIR", "data/audio"))
        self.temp_dir = Path(os.getenv("TEMP_AUDIO_DIR", "data/audio/temp"))

        # Podcast configuration
        self.podcast_title = "Your Daily News Digest"
        self.podcast_description = "AI-powered daily news summaries delivered as audio"
        self.podcast_author = "Your Daily Podcaster"
        self.podcast_language = "en-US"
        self.podcast_category = "News"

        # RSS feed configuration
        self.feed_url = os.getenv(
            "PODCAST_FEED_URL", "https://yourdomain.com/podcast.xml"
        )
        self.audio_base_url = os.getenv(
            "AUDIO_BASE_URL", "https://yourdomain.com/audio/"
        )

    def find_latest_audio_file(self) -> Optional[str]:
        """Find the most recent audio file, checking temp directory first."""
        try:
            # First check temp directory
            if self.temp_dir.exists():
                temp_files = list(self.temp_dir.glob("daily_digest_*.mp3"))
                if temp_files:
                    # Sort by modification time (newest first)
                    latest_file = max(temp_files, key=lambda f: f.stat().st_mtime)
                    self.logger.info(
                        f"Found latest audio file in temp: {latest_file.name}"
                    )
                    return str(latest_file)

            # Fall back to main audio directory
            if not self.audio_dir.exists():
                self.logger.warning(f"Audio directory does not exist: {self.audio_dir}")
                return None

            # Look for daily digest files in main directory
            audio_files = list(self.audio_dir.glob("daily_digest_*.mp3"))

            if not audio_files:
                self.logger.warning("No daily digest audio files found")
                return None

            # Sort by modification time (newest first)
            latest_file = max(audio_files, key=lambda f: f.stat().st_mtime)

            self.logger.info(f"Found latest audio file: {latest_file.name}")
            return str(latest_file)

        except Exception as e:
            self.logger.error(f"Error finding latest audio file: {e}")
            return None

    def get_audio_duration(self, audio_path: str) -> Optional[str]:
        """Get the duration of an audio file."""
        try:
            if not os.path.exists(audio_path):
                return None

            # Use ffprobe to get duration
            import subprocess

            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "csv=p=0",
                    audio_path,
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                duration_seconds = float(result.stdout.strip())
                return format_duration(int(duration_seconds))

            return None

        except Exception as e:
            self.logger.warning(f"Could not get audio duration: {e}")
            return None

    def get_audio_size(self, audio_path: str) -> Optional[int]:
        """Get the size of an audio file in bytes."""
        try:
            if os.path.exists(audio_path):
                return os.path.getsize(audio_path)
            return None
        except Exception as e:
            self.logger.warning(f"Could not get audio size: {e}")
            return None

    def create_rss_feed(self, audio_path: str) -> Optional[str]:
        """Create an RSS feed for the podcast."""
        if not RSS_AVAILABLE:
            self.logger.error("RSS feed generation not available (feedgen)")
            return None

        try:
            # Create feed generator
            fg = FeedGenerator()
            fg.load_extension("podcast")

            # Set feed metadata
            fg.title(self.podcast_title)
            fg.description(self.podcast_description)
            fg.author({"name": self.podcast_author})
            fg.language(self.podcast_language)
            fg.link(href=self.feed_url, rel="self")
            fg.logo(f"{self.audio_base_url}logo.png")

            # Set podcast-specific metadata
            fg.podcast.itunes_category(self.podcast_category)
            fg.podcast.itunes_author(self.podcast_author)
            fg.podcast.itunes_summary(self.podcast_description)
            fg.podcast.itunes_explicit("no")

            # Create episode entry
            date = get_yesterday_date()
            episode_title = f"Daily News Digest - {date}"

            # Get audio metadata
            duration = self.get_audio_duration(audio_path)
            size = self.get_audio_size(audio_path)

            # Create episode URL
            episode_url = f"{self.audio_base_url}{Path(audio_path).name}"

            # Create episode entry
            fe = fg.add_entry()
            fe.title(episode_title)
            fe.description(f"Your daily news digest for {date}")
            fe.published(datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc))
            fe.id(episode_url)

            # Add audio enclosure
            if size:
                fe.enclosure(episode_url, str(size), "audio/mpeg")

            # Add podcast-specific metadata
            fe.podcast.itunes_duration(duration or "00:00")
            fe.podcast.itunes_summary(f"Your daily news digest for {date}")

            # Generate RSS feed
            rss_content = fg.rss_str(pretty=True)

            # Save RSS feed
            rss_path = self.audio_dir / "podcast.xml"
            with open(rss_path, "wb") as f:
                f.write(rss_content)

            self.logger.info(f"RSS feed created: {rss_path}")
            return str(rss_path)

        except Exception as e:
            self.logger.error(f"Error creating RSS feed: {e}")
            return None

    def create_github_release_data(self, audio_path: str) -> Dict[str, Any]:
        """Create data for GitHub release."""
        try:
            date = get_yesterday_date()
            duration = self.get_audio_duration(audio_path)

            release_data = {
                "tag_name": f"v{date.replace('-', '.')}",
                "name": f"Daily News Digest - {date}",
                "body": f"""## Daily News Digest - {date}

Your AI-powered daily news summary is ready!

**Duration:** {duration or "Unknown"}
**Topics Covered:** {self.get_topics_summary()}

### How to Listen
- Download the MP3 file below
- Add to your podcast player using the RSS feed
- Stream directly from the audio file

### RSS Feed
Add this URL to your podcast app: `{self.feed_url}`

---
*Generated by Your Daily Podcaster*""",
                "draft": False,
                "prerelease": False,
            }

            return release_data

        except Exception as e:
            self.logger.error(f"Error creating GitHub release data: {e}")
            return {}

    def get_topics_summary(self) -> str:
        """Get a summary of topics covered in this episode."""
        try:
            # Get articles from yesterday
            articles = self.db.get_articles_for_audio()

            if not articles:
                return "No topics available"

            # Get unique topics
            topics = set()
            for article in articles:
                topic = article.get("topic", "General")
                topics.add(topic)

            return ", ".join(sorted(topics))

        except Exception as e:
            self.logger.warning(f"Could not get topics summary: {e}")
            return "Various topics"

    def create_metadata_file(self, audio_path: str) -> Optional[str]:
        """Create a metadata file for the episode."""
        try:
            date = get_yesterday_date()
            duration = self.get_audio_duration(audio_path)
            size = self.get_audio_size(audio_path)
            topics = self.get_topics_summary()

            metadata = {
                "episode_date": date,
                "title": f"Daily News Digest - {date}",
                "description": f"Your daily news digest for {date}",
                "duration": duration,
                "file_size": size,
                "topics_covered": topics,
                "generated_at": get_current_timestamp(),
                "audio_file": Path(audio_path).name,
            }

            # Save metadata
            metadata_path = self.audio_dir / f"metadata_{date}.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            self.logger.info(f"Metadata file created: {metadata_path}")
            return str(metadata_path)

        except Exception as e:
            self.logger.error(f"Error creating metadata file: {e}")
            return None

    def cleanup_temp_files_after_publish(self, audio_path: str) -> Tuple[str, bool]:
        """Clean up temporary audio files after successful publishing."""
        try:
            final_audio_path = audio_path

            # Move the final audio file from temp to permanent location if it's in temp
            if str(self.temp_dir) in audio_path:
                # Move to permanent location
                permanent_path = self.audio_dir / Path(audio_path).name
                self.audio_dir.mkdir(parents=True, exist_ok=True)

                # Copy the file to permanent location
                import shutil

                shutil.copy2(audio_path, permanent_path)
                self.logger.info(
                    f"Moved audio file to permanent location: {permanent_path}"
                )

                final_audio_path = str(permanent_path)

            # Clean up all temp files
            cleanup = CleanupUtility()
            removed_count = cleanup.cleanup_temp_audio_files()

            self.logger.info(
                f"Cleaned up {removed_count} temporary audio files after publishing"
            )
            return final_audio_path, True

        except Exception as e:
            self.logger.error(f"Error cleaning up temp files: {e}")
            return audio_path, False

    def run(self) -> Dict[str, Any]:
        """Run the complete publishing process."""
        self.logger.info("Starting podcast publishing process")

        # Find latest audio file
        audio_path = self.find_latest_audio_file()

        if not audio_path:
            self.logger.error("No audio file found to publish")
            return {"success": False, "error": "No audio file found"}

        self.logger.info(f"Publishing audio file: {audio_path}")

        # Create RSS feed
        rss_path = self.create_rss_feed(audio_path)

        # Create metadata file
        metadata_path = self.create_metadata_file(audio_path)

        # Create GitHub release data
        release_data = self.create_github_release_data(audio_path)

        # Clean up temporary files after successful publishing
        final_audio_path, cleanup_success = self.cleanup_temp_files_after_publish(
            audio_path
        )

        # Summary
        self.logger.info("Publishing complete")

        return {
            "success": True,
            "audio_file": final_audio_path,
            "rss_feed": rss_path,
            "metadata_file": metadata_path,
            "github_release_data": release_data,
            "cleanup_performed": cleanup_success,
        }


def main():
    """Main entry point."""
    # Setup logging
    setup_logger()
    logger = get_logger("main")

    logger.info("=" * 50)
    logger.info("Starting Podcast Publisher")
    logger.info("=" * 50)

    try:
        publisher = PodcastPublisher()
        result = publisher.run()

        if result["success"]:
            logger.info("Podcast publishing completed successfully")
            logger.info(f"Audio file: {result['audio_file']}")
            if result.get("rss_feed"):
                logger.info(f"RSS feed: {result['rss_feed']}")
            if result.get("metadata_file"):
                logger.info(f"Metadata: {result['metadata_file']}")
        else:
            logger.error(
                f"Podcast publishing failed: " f"{result.get('error', 'Unknown error')}"
            )
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
