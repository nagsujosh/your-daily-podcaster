#!/usr/bin/env python3
"""
Article Summarizer

Uses Gemini API to summarize articles by topic and stores results in article_data.db
"""

import os
import sys
import time
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from yourdaily.utils.db import DatabaseManager
from yourdaily.utils.logger import get_logger, setup_logger
from yourdaily.utils.time import get_yesterday_date


class ArticleSummarizer:
    def __init__(self, target_date: Optional[str] = None):
        """Initialize the article summarizer."""
        load_dotenv()

        # Setup logging
        self.logger = get_logger("ArticleSummarizer")

        # Initialize database
        self.db = DatabaseManager(
            search_db_path=os.getenv("SEARCH_DB_PATH", "data/db/search_index.db"),
            article_db_path=os.getenv("ARTICLE_DB_PATH", "data/db/article_data.db"),
        )

        # Date filtering - default to yesterday if not specified
        self.target_date = target_date or get_yesterday_date()
        self.logger.info(f"Target date for summarization: {self.target_date}")

        # Gemini API configuration
        self.gemini_api_key = os.getenv("GEMINI_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_KEY not found in environment variables")

        self.gemini_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-2.0-flash:generateContent"
        )

        # Rate limiting
        self.request_delay = 1  # seconds between requests

    def get_articles_for_summarization(self) -> List[Dict[str, Any]]:
        """Get articles that have clean text but no summary from the target date only."""
        return self.db.get_articles_for_summarization_from_date(self.target_date)

    def group_articles_by_topic(
        self, articles: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group articles by topic."""
        grouped = {}

        for article in articles:
            topic = article.get("topic", "General")
            if topic not in grouped:
                grouped[topic] = []
            grouped[topic].append(article)

        return grouped

    def create_summary_prompt(
        self, topic: str, articles: List[Dict[str, Any]], date: str
    ) -> str:
        """Create a prompt for summarizing articles on a specific topic."""

        # Combine all article content with source tracking
        combined_content = ""
        source_count = {}

        for i, article in enumerate(articles, 1):
            title = article.get("title", "Unknown Title")
            source = article.get("source", "Unknown Source")
            content = article.get("clean_text", "")

            # Track source frequency for deduplication insights
            source_count[source] = source_count.get(source, 0) + 1

            combined_content += f"\n\n--- Article {i} ---\n"
            combined_content += f"Title: {title}\n"
            combined_content += f"Source: {source}\n"
            combined_content += f"Content: {content}\n"

        # Create source summary for the prompt
        sources_summary = ", ".join(
            [
                f"{source} ({count} article{'s' if count > 1 else ''})"
                for source, count in source_count.items()
            ]
        )

        prompt = (
            f"You are a professional broadcast news reporter creating a comprehensive "
            f"news segment for '{topic}' on {date}. You have {len(articles)} articles "
            f"from the following sources: {sources_summary}.\n\n"
            f"ARTICLES TO ANALYZE:\n{combined_content}\n\n"
            f"INSTRUCTIONS:\n"
            f"Create a professional news report following broadcast journalism standards:\n\n"
            f"**{topic.upper()} REPORT - {date}**\n\n"
            f"📺 LEAD STORY:\n"
            f"• Start with the most significant breaking news or development\n"
            f"• Include WHO, WHAT, WHEN, WHERE, WHY in the opening\n\n"
            f"📊 KEY DEVELOPMENTS:\n"
            f"• [Development 1 with specific facts, figures, and verified information]\n"
            f"• [Development 2 with quotes from officials, experts, or witnesses]\n"
            f"• [Development 3 with market data, statistics, or measurable impacts]\n"
            f"• [Development 4 with geographic specifics and affected populations]\n\n"
            f"🎯 IMPACT ANALYSIS:\n"
            f"• Economic implications and market effects\n"
            f"• Social and political consequences\n"
            f"• Future outlook and expert predictions\n\n"
            f"📍 REGIONAL FOCUS:\n"
            f"• Highlight location-specific impacts and developments\n"
            f"• Include relevant demographic or geographic context\n\n"
            f"CRITICAL REQUIREMENTS:\n"
            f"1. DEDUPLICATION: If multiple sources report the same story, synthesize into ONE coherent narrative citing 'multiple sources confirm' or 'according to several reports'\n"
            f"2. SOURCE ATTRIBUTION: Use phrases like 'according to [Source Name]', 'reports indicate', '[Source] confirms'\n"
            f"3. VERIFICATION LANGUAGE: Use 'confirmed', 'reported', 'alleged', 'unverified' appropriately\n"
            f"4. NUMBERS & DATES: Include specific figures, percentages, dates, and timeframes\n"
            f"5. QUOTES: Incorporate direct quotes when available\n"
            f"6. CONTEXT: Provide background information for complex stories\n"
            f"7. BROADCAST STYLE: Write as if reading aloud for radio/podcast audience\n\n"
            f"TONE: Professional, authoritative, balanced, and engaging for audio consumption.\n"
            f"LENGTH: Aim for 90-120 seconds of spoken content (approximately 225-300 words).\n\n"
            f"Format as a continuous narrative suitable for text-to-speech conversion, "
            f"avoiding bullet points in the final output. Use natural speech patterns and "
            f"clear transitions between topics."
        )

        return prompt

    def call_gemini_api(self, prompt: str) -> Optional[str]:
        """Call Gemini API to generate summary."""
        try:
            # Use fake user agent for API calls
            from yourdaily.utils.user_agent import get_random_user_agent

            headers = {
                "Content-Type": "application/json",
                "X-goog-api-key": self.gemini_api_key,
                "User-Agent": get_random_user_agent(),
            }

            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 1024,
                },
            }

            self.logger.debug("Calling Gemini API...")
            response = requests.post(
                self.gemini_url, headers=headers, json=data, timeout=60
            )
            response.raise_for_status()

            result = response.json()

            # Extract the generated text
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        return parts[0]["text"]

            self.logger.error(f"Unexpected response format from Gemini API: {result}")
            return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Gemini API request failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error calling Gemini API: {e}")
            return None

    def summarize_topic_articles(
        self, topic: str, articles: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Summarize articles for a specific topic."""
        try:
            self.logger.info(f"Summarizing {len(articles)} articles for topic: {topic}")

            # Log source breakdown for this topic
            source_breakdown = {}
            for article in articles:
                source = article.get("source", "Unknown Source")
                source_breakdown[source] = source_breakdown.get(source, 0) + 1

            sources_info = ", ".join(
                [f"{source}: {count}" for source, count in source_breakdown.items()]
            )
            self.logger.info(f"Sources for {topic}: {sources_info}")

            # Get date for the prompt
            date = self.target_date

            # Create prompt
            prompt = self.create_summary_prompt(topic, articles, date)

            # Call Gemini API
            summary = self.call_gemini_api(prompt)

            if summary:
                self.logger.info(f"Successfully generated summary for topic: {topic}")
                # Log summary length for quality control
                word_count = len(summary.split())
                self.logger.debug(f"Summary word count for {topic}: {word_count} words")
                return summary
            else:
                self.logger.error(f"Failed to generate summary for topic: {topic}")
                return None

        except Exception as e:
            self.logger.error(f"Error summarizing topic '{topic}': {e}")
            return None

    def store_summaries(self, topic_summaries: Dict[str, str]) -> int:
        """Store summaries in the database."""
        stored_count = 0

        for topic, summary in topic_summaries.items():
            try:
                # Get all articles for this topic that need summaries from target date
                articles = self.db.get_articles_for_summarization_from_date(
                    self.target_date
                )
                topic_articles = [a for a in articles if a.get("topic") == topic]

                if not topic_articles:
                    self.logger.warning(
                        f"No articles found for topic '{topic}' on {self.target_date}"
                    )
                    continue

                self.logger.info(
                    f"Storing summary for {len(topic_articles)} articles in topic: {topic}"
                )

                # Store summary for each article in this topic
                for article in topic_articles:
                    real_url = article.get("real_url")
                    if not real_url:
                        self.logger.warning(
                            f"No real_url found for article: {article.get('title', 'Unknown')}"
                        )
                        continue

                    success = self.db.insert_article_data(
                        rss_url=article.get("rss_url"),
                        real_url=real_url,
                        clean_text=article.get("clean_text"),
                        summarized_text=summary,
                    )

                    if success:
                        stored_count += 1
                        self.logger.debug(
                            f"Stored summary for article: "
                            f"{article.get('title', 'Unknown')[:50]}..."
                        )
                    else:
                        self.logger.warning(
                            f"Failed to store summary for article: "
                            f"{article.get('real_url', 'Unknown URL')}"
                        )

            except Exception as e:
                self.logger.error(f"Error storing summaries for topic '{topic}': {e}")

        self.logger.info(
            f"Summary storage complete: {stored_count} total summaries stored"
        )
        return stored_count

    def run(self) -> Dict[str, Any]:
        """Run the complete summarization process."""
        self.logger.info("Starting article summarization process")

        # Get articles that need summarization
        articles = self.get_articles_for_summarization()

        if not articles:
            self.logger.info("No articles found for summarization")
            return {
                "success": True,
                "topics_processed": 0,
                "topics_successful": 0,
                "topics_failed": 0,
                "summaries_generated": 0,
                "summaries_stored": 0,
            }

        self.logger.info(f"Found {len(articles)} articles to summarize")

        # Group articles by topic
        grouped_articles = self.group_articles_by_topic(articles)
        self.logger.info(f"Grouped into {len(grouped_articles)} topics")

        # Summarize each topic
        topic_summaries = {}
        successful_topics = 0
        failed_topics = 0

        for i, (topic, topic_articles) in enumerate(grouped_articles.items(), 1):
            self.logger.info(f"Processing topic {i}/{len(grouped_articles)}: {topic}")

            try:
                summary = self.summarize_topic_articles(topic, topic_articles)

                if summary:
                    topic_summaries[topic] = summary
                    successful_topics += 1
                else:
                    failed_topics += 1

                # Rate limiting
                if i < len(grouped_articles):  # Don't delay after the last topic
                    time.sleep(self.request_delay)

            except Exception as e:
                self.logger.error(f"Error processing topic '{topic}': {e}")
                failed_topics += 1

        # Store summaries in database
        stored_count = self.store_summaries(topic_summaries)

        # Summary
        self.logger.info(
            f"Summarization complete: {successful_topics} topics successful, "
            f"{failed_topics} failed"
        )
        self.logger.info(f"Stored {stored_count} summaries in database")

        return {
            "success": True,
            "topics_processed": len(grouped_articles),
            "topics_successful": successful_topics,
            "topics_failed": failed_topics,
            "summaries_stored": stored_count,
        }


def main():
    """Main entry point."""
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Summarize articles using Gemini API")
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
    logger.info("Starting Article Summarizer")
    logger.info("=" * 50)

    try:
        summarizer = ArticleSummarizer(target_date=args.date)
        result = summarizer.run()

        if result["success"]:
            logger.info("Article summarization completed successfully")
            logger.info(
                f"Results: {result['summaries_stored']} summaries stored from "
                f"{result['topics_successful']} topics"
            )
        else:
            logger.error("Article summarization failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
