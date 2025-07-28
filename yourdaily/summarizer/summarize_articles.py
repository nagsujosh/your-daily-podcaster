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
    def __init__(self):
        """Initialize the article summarizer."""
        load_dotenv()

        # Setup logging
        self.logger = get_logger("ArticleSummarizer")

        # Initialize database
        self.db = DatabaseManager(
            search_db_path=os.getenv("SEARCH_DB_PATH", "data/db/search_index.db"),
            article_db_path=os.getenv("ARTICLE_DB_PATH", "data/db/article_data.db"),
        )

        # Gemini API configuration
        self.gemini_api_key = os.getenv("GEMINI_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_KEY not found in environment variables")

        self.gemini_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-pro:generateContent"
        )

        # Rate limiting
        self.request_delay = 1  # seconds between requests

    def get_articles_for_summarization(self) -> List[Dict[str, Any]]:
        """Get articles that have clean text but no summary."""
        return self.db.get_articles_for_summarization()

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

        # Combine all article content
        combined_content = ""
        for i, article in enumerate(articles, 1):
            title = article.get("title", "Unknown Title")
            source = article.get("source", "Unknown Source")
            content = article.get("clean_text", "")

            combined_content += f"\n\n--- Article {i} ---\n"
            combined_content += f"Title: {title}\n"
            combined_content += f"Source: {source}\n"
            combined_content += f"Content: {content}\n"

        prompt = (
            f"You are a professional news summarizer. Please analyze the following "
            f"articles about '{topic}' from {date} and create a concise summary.\n\n"
            f"{combined_content}\n\n"
            f"Please provide a summary with the following format:\n\n"
            f"**{topic} Summary for {date}**\n\n"
            f"• [Key point 1 with specific facts, locations, events, and people]\n"
            f"• [Key point 2 with specific facts, locations, events, and people]\n"
            f"• [Key point 3 with specific facts, locations, events, and people]\n"
            f"• [Key point 4 with specific facts, locations, events, and people]\n"
            f"• [Key point 5 with specific facts, locations, events, and people]\n\n"
            f"Focus on:\n"
            f"- The most important developments and news\n"
            f"- Specific names, locations, and dates mentioned\n"
            f"- Key facts and figures\n"
            f"- Major events or announcements\n"
            f"- Impact and implications\n\n"
            f"Keep each bullet point concise but informative. Avoid generic statements "
            f"and focus on concrete details from the articles."
        )

        return prompt

    def call_gemini_api(self, prompt: str) -> Optional[str]:
        """Call Gemini API to generate summary."""
        try:
            headers = {
                "Content-Type": "application/json",
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

            url = f"{self.gemini_url}?key={self.gemini_api_key}"

            self.logger.debug("Calling Gemini API...")
            response = requests.post(url, headers=headers, json=data, timeout=60)
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

            # Get date for the prompt
            date = get_yesterday_date()

            # Create prompt
            prompt = self.create_summary_prompt(topic, articles, date)

            # Call Gemini API
            summary = self.call_gemini_api(prompt)

            if summary:
                self.logger.info(f"Successfully generated summary for topic: {topic}")
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
                # Get all articles for this topic that need summaries
                articles = self.db.get_articles_for_summarization()
                topic_articles = [a for a in articles if a.get("topic") == topic]

                # Store summary for each article in this topic
                for article in topic_articles:
                    success = self.db.insert_article_data(
                        url=article["url"],
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
                            f"{article.get('url', 'Unknown URL')}"
                        )

            except Exception as e:
                self.logger.error(f"Error storing summaries for topic '{topic}': {e}")

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
                "summaries_generated": 0,
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
    # Setup logging
    setup_logger()
    logger = get_logger("main")

    logger.info("=" * 50)
    logger.info("Starting Article Summarizer")
    logger.info("=" * 50)

    try:
        summarizer = ArticleSummarizer()
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
