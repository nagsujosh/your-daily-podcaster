#!/usr/bin/env python3
"""
Text-to-Speech Audio Generator

Converts article summaries to audio using Google Cloud TTS and merges into final podcast
"""

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from yourdaily.utils.db import DatabaseManager
from yourdaily.utils.logger import get_logger, setup_logger
from yourdaily.utils.time import get_yesterday_date

# Google Cloud TTS imports
try:
    from google.cloud import texttospeech
    from google.oauth2 import service_account

    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# Audio processing imports
try:
    from pydub import AudioSegment

    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


class AudioGenerator:
    def __init__(self, target_date: Optional[str] = None):
        """Initialize the audio generator."""
        load_dotenv()

        # Setup logging
        self.logger = get_logger("AudioGenerator")

        # Initialize database
        self.db = DatabaseManager(
            search_db_path=os.getenv("SEARCH_DB_PATH", "data/db/search_index.db"),
            article_db_path=os.getenv("ARTICLE_DB_PATH", "data/db/article_data.db"),
        )

        # Date filtering - default to yesterday if not specified
        self.target_date = target_date or get_yesterday_date()
        self.logger.info(f"Target date for audio generation: {self.target_date}")

        # Audio output directories
        self.audio_dir = Path(os.getenv("AUDIO_OUTPUT_DIR", "data/audio"))
        self.temp_dir = Path(os.getenv("TEMP_AUDIO_DIR", "data/audio/temp"))

        # Create directories
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Initialize TTS client
        self.tts_client = None
        self.init_tts_client()

        # Audio settings
        self.voice_name = "en-US-Neural2-F"  # Female neural voice
        self.speaking_rate = 0.9  # Slightly slower for clarity
        self.audio_encoding = texttospeech.AudioEncoding.MP3

    def init_tts_client(self):
        """Initialize Google Cloud TTS client."""
        if not TTS_AVAILABLE:
            self.logger.error("Google Cloud TTS not available")
            return

        try:
            creds_path = os.getenv("GCLOUD_TTS_CREDS")
            if creds_path and os.path.exists(creds_path):
                credentials = service_account.Credentials.from_service_account_file(
                    creds_path
                )
                self.tts_client = texttospeech.TextToSpeechClient(
                    credentials=credentials
                )
                self.logger.info(
                    "Google Cloud TTS client initialized with service account"
                )
            else:
                # Try default credentials
                self.tts_client = texttospeech.TextToSpeechClient()
                self.logger.info(
                    "Google Cloud TTS client initialized with default credentials"
                )

        except Exception as e:
            self.logger.error(f"Failed to initialize TTS client: {e}")
            self.tts_client = None

    def get_articles_for_audio(self) -> List[Dict[str, Any]]:
        """Get articles that have summaries but no audio from the target date only."""
        return self.db.get_articles_for_audio_from_date(self.target_date)

    def group_summaries_by_topic(
        self, articles: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Group summaries by topic, taking the first summary for each topic."""
        topic_summaries = {}

        for article in articles:
            topic = article.get("topic", "General")
            summary = article.get("summarized_text", "")

            if topic not in topic_summaries and summary:
                topic_summaries[topic] = summary

        return topic_summaries

    def create_intro_text(self, date: str) -> str:
        """Create introduction text for the podcast."""
        return (
            f"Here is your news digest for {date}. "
            f"Today's top stories cover the following topics."
        )

    def create_outro_text(self) -> str:
        """Create outro text for the podcast."""
        return (
            "Thank you for listening to your daily news digest. "
            "Stay informed and have a great day."
        )

    def text_to_speech(self, text: str, filename: str) -> Optional[str]:
        """Convert text to speech using Google Cloud TTS."""
        if not self.tts_client:
            self.logger.error("TTS client not available")
            return None

        try:
            # Configure the voice
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US", name=self.voice_name
            )

            # Configure the audio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=self.audio_encoding,
                speaking_rate=self.speaking_rate,
            )

            # Create the synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Perform the text-to-speech request
            response = self.tts_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            # Save the audio to a file
            output_path = self.temp_dir / filename
            with open(output_path, "wb") as out:
                out.write(response.audio_content)

            self.logger.info(f"Generated audio: {filename}")
            return str(output_path)

        except Exception as e:
            self.logger.error(f"Error generating audio for {filename}: {e}")
            return None

    def merge_audio_files(
        self, audio_files: List[str], output_filename: str
    ) -> Optional[str]:
        """Merge multiple audio files into one."""
        if not AUDIO_AVAILABLE:
            self.logger.error("Audio processing not available (pydub)")
            return None

        try:
            # Load and combine audio files
            combined = AudioSegment.empty()

            for audio_file in audio_files:
                if os.path.exists(audio_file):
                    audio = AudioSegment.from_mp3(audio_file)
                    combined += audio

                    # Add a short pause between segments
                    pause = AudioSegment.silent(duration=500)  # 0.5 seconds
                    combined += pause

            # Export the combined audio
            output_path = self.audio_dir / output_filename
            combined.export(str(output_path), format="mp3")

            self.logger.info(f"Created final audio: {output_filename}")
            return str(output_path)

        except Exception as e:
            self.logger.error(f"Error merging audio files: {e}")
            return None

    def generate_topic_audio(self, topic: str, summary: str) -> Optional[str]:
        """Generate audio for a specific topic summary."""
        try:
            # Clean filename
            safe_topic = "".join(
                c for c in topic if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            safe_topic = safe_topic.replace(" ", "_")
            filename = f"{safe_topic}_summary.mp3"

            # Generate audio
            audio_path = self.text_to_speech(summary, filename)

            if audio_path:
                # Update database to mark audio as generated
                articles = self.db.get_articles_for_audio()
                topic_articles = [a for a in articles if a.get("topic") == topic]

                for article in topic_articles:
                    self.db.update_audio_generated(article["url"], audio_path)

                return audio_path
            else:
                return None

        except Exception as e:
            self.logger.error(f"Error generating audio for topic '{topic}': {e}")
            return None

    def run(self) -> Dict[str, Any]:
        """Run the complete audio generation process."""
        self.logger.info("Starting audio generation process")

        # Check if TTS is available
        if not self.tts_client:
            self.logger.error("TTS client not available - cannot generate audio")
            return {"success": False, "error": "TTS client not available"}

        # Get articles that need audio generation
        articles = self.get_articles_for_audio()

        if not articles:
            self.logger.info("No articles found for audio generation")
            return {
                "success": True,
                "topics_processed": 0,
                "audio_files_generated": 0,
            }

        self.logger.info(f"Found {len(articles)} articles to generate audio for")

        # Group summaries by topic
        topic_summaries = self.group_summaries_by_topic(articles)
        self.logger.info(f"Grouped into {len(topic_summaries)} topics")

        # Generate audio for each topic
        audio_files = []
        successful_topics = 0
        failed_topics = 0

        for i, (topic, summary) in enumerate(topic_summaries.items(), 1):
            self.logger.info(
                f"Generating audio for topic {i}/{len(topic_summaries)}: {topic}"
            )

            try:
                audio_path = self.generate_topic_audio(topic, summary)

                if audio_path:
                    audio_files.append(audio_path)
                    successful_topics += 1
                else:
                    failed_topics += 1

                # Rate limiting
                if i < len(topic_summaries):
                    time.sleep(1)

            except Exception as e:
                self.logger.error(f"Error processing topic '{topic}': {e}")
                failed_topics += 1

        # Generate intro and outro
        date = self.target_date
        intro_text = self.create_intro_text(date)
        outro_text = self.create_outro_text()

        intro_path = self.text_to_speech(intro_text, "intro.mp3")
        outro_path = self.text_to_speech(outro_text, "outro.mp3")

        if intro_path:
            audio_files.insert(0, intro_path)
        if outro_path:
            audio_files.append(outro_path)

        # Merge all audio files
        final_audio_path = None
        if audio_files:
            date_str = date.replace("-", "_")
            output_filename = f"daily_digest_{date_str}.mp3"
            final_audio_path = self.merge_audio_files(audio_files, output_filename)

        # Summary
        self.logger.info(
            f"Audio generation complete: {successful_topics} topics successful, "
            f"{failed_topics} failed"
        )

        if final_audio_path:
            self.logger.info(f"Final podcast created: {final_audio_path}")

        return {
            "success": True,
            "topics_processed": len(topic_summaries),
            "topics_successful": successful_topics,
            "topics_failed": failed_topics,
            "audio_files_generated": len(audio_files),
            "final_audio_path": final_audio_path,
        }


def main():
    """Main entry point."""
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Generate audio from article summaries"
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

    logger.info("=" * 50)
    logger.info("Starting Audio Generator")
    logger.info("=" * 50)

    try:
        generator = AudioGenerator(target_date=args.date)
        result = generator.run()

        if result["success"]:
            logger.info("Audio generation completed successfully")
            logger.info(
                f"Results: {result['audio_files_generated']} audio files "
                f"generated from {result['topics_successful']} topics"
            )
            if result.get("final_audio_path"):
                logger.info(f"Final podcast: {result['final_audio_path']}")
        else:
            logger.error(
                f"Audio generation failed: {result.get('error', 'Unknown error')}"
            )
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
