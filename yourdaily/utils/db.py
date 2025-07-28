import os
import sqlite3
from typing import Any, Dict, List

from loguru import logger


class DatabaseManager:
    def __init__(self, search_db_path: str, article_db_path: str):
        self.search_db_path = search_db_path
        self.article_db_path = article_db_path
        self._init_databases()

    def _init_databases(self):
        """Initialize both databases with their schemas."""
        # Ensure directories exist
        search_dir = os.path.dirname(self.search_db_path)
        article_dir = os.path.dirname(self.article_db_path)

        if search_dir:
            os.makedirs(search_dir, exist_ok=True)
        if article_dir:
            os.makedirs(article_dir, exist_ok=True)

        # Initialize search_index.db
        with sqlite3.connect(self.search_db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS search_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    source TEXT,
                    gnews_date TEXT,
                    published_date TEXT,
                    inserted_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.commit()

        # Initialize article_data.db
        with sqlite3.connect(self.article_db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS article_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    clean_text TEXT,
                    summarized_text TEXT,
                    audio_path TEXT,
                    summarized_at TEXT,
                    audio_generated BOOLEAN DEFAULT FALSE
                )
            """
            )
            conn.commit()

        logger.info("Databases initialized successfully")

    def article_exists(self, url: str) -> bool:
        """Check if an article with the given URL already exists."""
        try:
            with sqlite3.connect(self.search_db_path) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM search_index WHERE url = ?",
                    (url,)
                )
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logger.error(f"Error checking if article exists: {e}")
            return False

    def insert_search_result(
        self,
        topic: str,
        title: str,
        url: str,
        source: str,
        gnews_date: str,
        published_date: str,
    ) -> bool:
        """Insert a search result into search_index.db."""
        try:
            with sqlite3.connect(self.search_db_path) as conn:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO search_index
                    (topic, title, url, source, gnews_date, published_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (topic, title, url, source, gnews_date, published_date),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error inserting search result: {e}")
            return False

    def get_unprocessed_articles(self) -> List[Dict[str, Any]]:
        """Get articles that haven't been processed yet."""
        try:
            with sqlite3.connect(self.search_db_path) as conn:
                # Attach the article_data database
                conn.execute(f"ATTACH DATABASE '{self.article_db_path}' AS article_db")
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM search_index
                    WHERE url NOT IN (
                        SELECT url FROM article_db.article_data
                    )
                    ORDER BY inserted_at DESC
                """
                )
                result = [dict(row) for row in cursor.fetchall()]
                conn.execute("DETACH DATABASE article_db")
                return result
        except Exception as e:
            logger.error(f"Error getting unprocessed articles: {e}")
            return []

    def insert_article_data(
        self,
        url: str,
        clean_text: str = None,
        summarized_text: str = None,
        audio_path: str = None,
    ) -> bool:
        """Insert or update article data."""
        try:
            with sqlite3.connect(self.article_db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO article_data
                    (url, clean_text, summarized_text, audio_path, summarized_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (url, clean_text, summarized_text, audio_path),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error inserting article data: {e}")
            return False

    def update_audio_generated(self, url: str, audio_path: str) -> bool:
        """Mark audio as generated for an article."""
        try:
            with sqlite3.connect(self.article_db_path) as conn:
                conn.execute(
                    """
                    UPDATE article_data
                    SET audio_generated = TRUE, audio_path = ?
                    WHERE url = ?
                """,
                    (audio_path, url),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating audio status: {e}")
            return False

    def get_articles_for_summarization(self) -> List[Dict[str, Any]]:
        """Get articles that have clean text but no summary."""
        try:
            with sqlite3.connect(self.article_db_path) as conn:
                # Attach the search_index database
                conn.execute(f"ATTACH DATABASE '{self.search_db_path}' AS search_db")
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT ad.*, si.topic, si.title, si.source
                    FROM article_data ad
                    JOIN search_db.search_index si ON ad.url = si.url
                    WHERE ad.clean_text IS NOT NULL
                    AND ad.summarized_text IS NULL
                    ORDER BY si.inserted_at DESC
                """
                )
                result = [dict(row) for row in cursor.fetchall()]
                conn.execute("DETACH DATABASE search_db")
                return result
        except Exception as e:
            logger.error(f"Error getting articles for summarization: {e}")
            return []

    def get_articles_for_audio(self) -> List[Dict[str, Any]]:
        """Get articles that have summaries but no audio."""
        try:
            with sqlite3.connect(self.article_db_path) as conn:
                # Attach the search_index database
                conn.execute(f"ATTACH DATABASE '{self.search_db_path}' AS search_db")
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT ad.*, si.topic, si.title, si.source
                    FROM article_data ad
                    JOIN search_db.search_index si ON ad.url = si.url
                    WHERE ad.summarized_text IS NOT NULL
                    AND ad.audio_generated = FALSE
                    ORDER BY si.inserted_at DESC
                """
                )
                result = [dict(row) for row in cursor.fetchall()]
                conn.execute("DETACH DATABASE search_db")
                return result
        except Exception as e:
            logger.error(f"Error getting articles for audio: {e}")
            return []

    def get_all_audio_files(self) -> List[str]:
        """Get all generated audio file paths."""
        try:
            with sqlite3.connect(self.article_db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT audio_path FROM article_data
                    WHERE audio_path IS NOT NULL
                """
                )
                return [row[0] for row in cursor.fetchall() if row[0]]
        except Exception as e:
            logger.error(f"Error getting audio files: {e}")
            return []

    def cleanup_old_data(self, days_to_keep: int = 7) -> bool:
        """Clean up old data, keeping only search metadata."""
        try:
            with sqlite3.connect(self.article_db_path) as conn:
                conn.execute(
                    """
                    DELETE FROM article_data
                    WHERE summarized_at < datetime('now', '-{} days')
                """.format(
                        days_to_keep
                    )
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            return False
