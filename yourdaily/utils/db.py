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

        # Initialize search_index.db with updated schema
        with sqlite3.connect(self.search_db_path) as conn:
            # First create the table with old schema if it doesn't exist
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS search_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    source TEXT,
                    rss_date TEXT,
                    published_date TEXT,
                    inserted_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Check if we need to migrate from old schema
            cursor = conn.execute("PRAGMA table_info(search_index)")
            columns = [row[1] for row in cursor.fetchall()]

            if "url" in columns and "rss_url" not in columns:
                logger.info("Migrating search_index table to new schema...")

                # Add new columns
                try:
                    conn.execute("ALTER TABLE search_index ADD COLUMN rss_url TEXT")
                    conn.execute("ALTER TABLE search_index ADD COLUMN real_url TEXT")

                    # Copy url data to rss_url
                    conn.execute(
                        "UPDATE search_index SET rss_url = url WHERE rss_url IS NULL"
                    )

                    # Create a new table with the updated schema
                    conn.execute(
                        """
                        CREATE TABLE search_index_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            topic TEXT NOT NULL,
                            title TEXT NOT NULL,
                            rss_url TEXT UNIQUE NOT NULL,
                            real_url TEXT,
                            source TEXT,
                            rss_date TEXT,
                            published_date TEXT,
                            inserted_at TEXT DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )

                    # Copy data to new table
                    conn.execute(
                        """
                        INSERT INTO search_index_new
                        (id, topic, title, rss_url, real_url, source, rss_date, published_date, inserted_at)
                        SELECT id, topic, title, rss_url, real_url, source, rss_date, published_date, inserted_at
                        FROM search_index
                        """
                    )

                    # Drop old table and rename new one
                    conn.execute("DROP TABLE search_index")
                    conn.execute("ALTER TABLE search_index_new RENAME TO search_index")

                    logger.info("Migration completed successfully")

                except sqlite3.Error as e:
                    logger.error(f"Migration failed: {e}")
                    # If migration fails, create new table structure
                    conn.execute("DROP TABLE IF EXISTS search_index_new")

            elif "rss_url" not in columns:
                # Create table with new schema
                conn.execute("DROP TABLE IF EXISTS search_index")
                conn.execute(
                    """
                    CREATE TABLE search_index (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        topic TEXT NOT NULL,
                        title TEXT NOT NULL,
                        rss_url TEXT UNIQUE NOT NULL,
                        real_url TEXT,
                        source TEXT,
                        rss_date TEXT,
                        published_date TEXT,
                        inserted_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

            conn.commit()

        # Initialize article_data.db with updated schema
        with sqlite3.connect(self.article_db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS article_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rss_url TEXT,
                    real_url TEXT UNIQUE NOT NULL,
                    clean_text TEXT,
                    summarized_text TEXT,
                    audio_path TEXT,
                    summarized_at TEXT,
                    audio_generated BOOLEAN DEFAULT FALSE
                )
            """
            )

            # Check if we need to migrate article_data table
            cursor = conn.execute("PRAGMA table_info(article_data)")
            columns = [row[1] for row in cursor.fetchall()]

            if "url" in columns and "real_url" not in columns:
                logger.info("Migrating article_data table to new schema...")

                try:
                    # Add new columns
                    conn.execute("ALTER TABLE article_data ADD COLUMN rss_url TEXT")
                    conn.execute("ALTER TABLE article_data ADD COLUMN real_url TEXT")

                    # Copy url to real_url (assuming current urls are real urls)
                    conn.execute(
                        "UPDATE article_data SET real_url = url WHERE real_url IS NULL"
                    )

                    # Create new table with updated schema
                    conn.execute(
                        """
                        CREATE TABLE article_data_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            rss_url TEXT,
                            real_url TEXT UNIQUE NOT NULL,
                            clean_text TEXT,
                            summarized_text TEXT,
                            audio_path TEXT,
                            summarized_at TEXT,
                            audio_generated BOOLEAN DEFAULT FALSE
                        )
                        """
                    )

                    # Copy data
                    conn.execute(
                        """
                        INSERT INTO article_data_new
                        (id, rss_url, real_url, clean_text, summarized_text, audio_path, summarized_at, audio_generated)
                        SELECT id, rss_url, real_url, clean_text, summarized_text, audio_path, summarized_at, audio_generated
                        FROM article_data
                        """
                    )

                    # Replace table
                    conn.execute("DROP TABLE article_data")
                    conn.execute("ALTER TABLE article_data_new RENAME TO article_data")

                    logger.info("Article data migration completed successfully")

                except sqlite3.Error as e:
                    logger.error(f"Article data migration failed: {e}")
                    conn.execute("DROP TABLE IF EXISTS article_data_new")

            conn.commit()

        logger.info("Databases initialized successfully")

    def article_exists(self, rss_url: str) -> bool:
        """Check if an article with the given RSS URL already exists."""
        try:
            with sqlite3.connect(self.search_db_path) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM search_index WHERE rss_url = ?", (rss_url,)
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
        rss_url: str,
        source: str,
        rss_date: str,
        published_date: str,
        real_url: str = None,
    ) -> bool:
        """Insert a search result into search_index.db."""
        try:
            with sqlite3.connect(self.search_db_path) as conn:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO search_index
                    (topic, title, rss_url, real_url, source, rss_date, published_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (topic, title, rss_url, real_url, source, rss_date, published_date),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error inserting search result: {e}")
            return False

    def update_real_url(self, rss_url: str, real_url: str) -> bool:
        """Update the real URL for an existing search result."""
        try:
            with sqlite3.connect(self.search_db_path) as conn:
                conn.execute(
                    "UPDATE search_index SET real_url = ? WHERE rss_url = ?",
                    (real_url, rss_url),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating real URL: {e}")
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
                    WHERE rss_url NOT IN (
                        SELECT COALESCE(rss_url, '')
                        FROM article_db.article_data
                        WHERE rss_url IS NOT NULL
                    )
                    AND (real_url IS NULL OR real_url NOT IN (
                        SELECT COALESCE(real_url, '')
                        FROM article_db.article_data
                        WHERE real_url IS NOT NULL
                    ))
                    ORDER BY inserted_at DESC
                """
                )
                result = [dict(row) for row in cursor.fetchall()]
                conn.execute("DETACH DATABASE article_db")
                return result
        except Exception as e:
            logger.error(f"Error getting unprocessed articles: {e}")
            return []

    def get_unprocessed_articles_from_date(
        self, target_date: str
    ) -> List[Dict[str, Any]]:
        """Get unprocessed articles from a specific date only."""
        try:
            with sqlite3.connect(self.search_db_path) as conn:
                # Attach the article_data database
                conn.execute(f"ATTACH DATABASE '{self.article_db_path}' AS article_db")
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM search_index
                    WHERE published_date = ?
                    AND rss_url NOT IN (
                        SELECT COALESCE(rss_url, '')
                        FROM article_db.article_data
                        WHERE rss_url IS NOT NULL
                    )
                    AND (real_url IS NULL OR real_url NOT IN (
                        SELECT COALESCE(real_url, '')
                        FROM article_db.article_data
                        WHERE real_url IS NOT NULL
                    ))
                    ORDER BY inserted_at DESC
                """,
                    (target_date,),
                )
                result = [dict(row) for row in cursor.fetchall()]
                conn.execute("DETACH DATABASE article_db")
                return result
        except Exception as e:
            logger.error(
                f"Error getting unprocessed articles from date {target_date}: {e}"
            )
            return []

    def get_articles_for_summarization_from_date(
        self, target_date: str
    ) -> List[Dict[str, Any]]:
        """Get articles that have clean text but no summary from a specific date."""
        try:
            with sqlite3.connect(self.article_db_path) as conn:
                # Attach the search_index database
                conn.execute(f"ATTACH DATABASE '{self.search_db_path}' AS search_db")
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT ad.*, si.topic, si.title, si.source
                    FROM article_data ad
                    LEFT JOIN search_db.search_index si ON (
                        ad.rss_url = si.rss_url OR ad.real_url = si.real_url
                    )
                    WHERE ad.clean_text IS NOT NULL
                    AND ad.summarized_text IS NULL
                    AND si.published_date = ?
                    ORDER BY ad.summarized_at DESC
                """,
                    (target_date,),
                )
                result = [dict(row) for row in cursor.fetchall()]
                conn.execute("DETACH DATABASE search_db")
                return result
        except Exception as e:
            logger.error(
                f"Error getting articles for summarization from date {target_date}: {e}"
            )
            return []

    def get_articles_for_audio_from_date(
        self, target_date: str
    ) -> List[Dict[str, Any]]:
        """Get articles that have summaries but no audio from a specific date."""
        try:
            with sqlite3.connect(self.article_db_path) as conn:
                # Attach the search_index database
                conn.execute(f"ATTACH DATABASE '{self.search_db_path}' AS search_db")
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT ad.*, si.topic, si.title, si.source
                    FROM article_data ad
                    LEFT JOIN search_db.search_index si ON (
                        ad.rss_url = si.rss_url OR ad.real_url = si.real_url
                    )
                    WHERE ad.summarized_text IS NOT NULL
                    AND ad.audio_path IS NULL
                    AND si.published_date = ?
                    ORDER BY ad.summarized_at DESC
                """,
                    (target_date,),
                )
                result = [dict(row) for row in cursor.fetchall()]
                conn.execute("DETACH DATABASE search_db")
                return result
        except Exception as e:
            logger.error(
                f"Error getting articles for audio from date {target_date}: {e}"
            )
            return []

    def insert_article_data(
        self,
        rss_url: str = None,
        real_url: str = None,
        clean_text: str = None,
        summarized_text: str = None,
        audio_path: str = None,
    ) -> bool:
        """Insert or update article data."""
        if not real_url:
            logger.error("real_url is required for article data")
            return False

        try:
            with sqlite3.connect(self.article_db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO article_data
                    (rss_url, real_url, clean_text, summarized_text, audio_path, summarized_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (rss_url, real_url, clean_text, summarized_text, audio_path),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error inserting article data: {e}")
            return False

    def update_audio_generated(self, real_url: str, audio_path: str) -> bool:
        """Mark audio as generated for an article."""
        try:
            with sqlite3.connect(self.article_db_path) as conn:
                conn.execute(
                    """
                    UPDATE article_data
                    SET audio_generated = TRUE, audio_path = ?
                    WHERE real_url = ?
                """,
                    (audio_path, real_url),
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
                    LEFT JOIN search_db.search_index si ON (
                        ad.rss_url = si.rss_url OR ad.real_url = si.real_url
                    )
                    WHERE ad.clean_text IS NOT NULL
                    AND ad.summarized_text IS NULL
                    ORDER BY ad.summarized_at DESC
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
                    LEFT JOIN search_db.search_index si ON (
                        ad.rss_url = si.rss_url OR ad.real_url = si.real_url
                    )
                    WHERE ad.summarized_text IS NOT NULL
                    AND ad.audio_generated = FALSE
                    ORDER BY ad.summarized_at DESC
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

    def cleanup_data_older_than_days(self, days: int) -> Dict[str, int]:
        """Clean data older than specified days from both databases."""
        try:
            from datetime import datetime, timedelta

            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            search_deleted = 0
            article_deleted = 0

            # Clean search_index database - check if table exists first
            try:
                with sqlite3.connect(self.search_db_path) as conn:
                    # Check if search_index table exists
                    cursor = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='search_index'"
                    )
                    if cursor.fetchone():
                        cursor = conn.execute(
                            "DELETE FROM search_index WHERE published_date < ?",
                            (cutoff_date,),
                        )
                        search_deleted = cursor.rowcount
                        conn.commit()
                    else:
                        logger.warning(
                            "search_index table does not exist, skipping search cleanup"
                        )
            except sqlite3.Error as e:
                logger.warning(f"Could not clean search_index table: {e}")

            # Clean article_data database
            try:
                with sqlite3.connect(self.article_db_path) as conn:
                    # Check if we can reference search_index for cleanup
                    try:
                        with sqlite3.connect(self.search_db_path) as search_conn:
                            # Check if search_index table exists
                            cursor = search_conn.execute(
                                "SELECT name FROM sqlite_master WHERE type='table' AND name='search_index'"
                            )
                            search_table_exists = cursor.fetchone() is not None

                        if search_table_exists:
                            # First get the URLs to delete based on search_index
                            cursor = conn.execute(
                                """
                                SELECT rss_url, real_url FROM article_data
                                WHERE id IN (
                                    SELECT ad.id FROM article_data ad
                                    LEFT JOIN (
                                        SELECT rss_url, real_url, published_date
                                        FROM search_index
                                        WHERE published_date >= ?
                                    ) si ON (ad.rss_url = si.rss_url OR ad.real_url = si.real_url)
                                    WHERE si.published_date IS NULL
                                )
                                """,
                                (cutoff_date,),
                            )
                            urls_to_delete = cursor.fetchall()

                            # Delete the article data
                            for rss_url, real_url in urls_to_delete:
                                if rss_url:
                                    cursor = conn.execute(
                                        "DELETE FROM article_data WHERE rss_url = ?",
                                        (rss_url,),
                                    )
                                    article_deleted += cursor.rowcount
                                if real_url:
                                    cursor = conn.execute(
                                        "DELETE FROM article_data WHERE real_url = ?",
                                        (real_url,),
                                    )
                                    article_deleted += cursor.rowcount
                        else:
                            # Fallback: clean based on date in article_data if we have date info
                            logger.info(
                                "search_index table not available, using fallback cleanup method"
                            )
                            # Check if article_data has date columns we can use
                            cursor = conn.execute("PRAGMA table_info(article_data)")
                            columns = [row[1] for row in cursor.fetchall()]

                            if "inserted_at" in columns:
                                cursor = conn.execute(
                                    "DELETE FROM article_data WHERE inserted_at < ?",
                                    (cutoff_date,),
                                )
                                article_deleted = cursor.rowcount
                            else:
                                logger.warning(
                                    "No date column available for article cleanup"
                                )

                        conn.commit()

                    except sqlite3.Error as e:
                        logger.warning(
                            f"Could not access search_index for article cleanup: {e}"
                        )

            except sqlite3.Error as e:
                logger.warning(f"Could not clean article_data table: {e}")

            logger.info(
                f"Cleaned {search_deleted} search records and {article_deleted} article records older than {days} days"
            )
            return {
                "search_deleted": search_deleted,
                "article_deleted": article_deleted,
            }

        except Exception as e:
            logger.error(f"Error cleaning old data: {e}")
            return {"search_deleted": 0, "article_deleted": 0}

    def cleanup_data_from_date(self, target_date: str) -> Dict[str, int]:
        """Clean all data from a specific date from both databases."""
        try:
            search_deleted = 0
            article_deleted = 0

            # Clean search_index database
            with sqlite3.connect(self.search_db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM search_index WHERE published_date = ?", (target_date,)
                )
                search_deleted = cursor.rowcount
                conn.commit()

            # Clean article_data database for articles from that date
            with sqlite3.connect(self.article_db_path) as conn:
                # Get URLs to delete
                cursor = conn.execute(
                    """
                    SELECT ad.rss_url, ad.real_url
                    FROM article_data ad
                    LEFT JOIN search_db.search_index si ON (ad.rss_url = si.rss_url OR ad.real_url = si.real_url)
                    WHERE si.published_date = ?
                    """,
                    (target_date,),
                )
                urls_to_delete = cursor.fetchall()

                # Delete the article data
                for rss_url, real_url in urls_to_delete:
                    if rss_url:
                        cursor = conn.execute(
                            "DELETE FROM article_data WHERE rss_url = ?", (rss_url,)
                        )
                        article_deleted += cursor.rowcount
                    if real_url:
                        cursor = conn.execute(
                            "DELETE FROM article_data WHERE real_url = ?", (real_url,)
                        )
                        article_deleted += cursor.rowcount

                conn.commit()

            logger.info(
                f"Cleaned {search_deleted} search records and {article_deleted} article records from {target_date}"
            )
            return {
                "search_deleted": search_deleted,
                "article_deleted": article_deleted,
            }

        except Exception as e:
            logger.error(f"Error cleaning data from date {target_date}: {e}")
            return {"search_deleted": 0, "article_deleted": 0}

    def get_data_stats_by_date(self, target_date: str) -> Dict[str, int]:
        """Get statistics about data for a specific date."""
        try:
            search_count = 0
            article_count = 0
            processed_count = 0
            summarized_count = 0
            audio_count = 0

            # Count search records
            with sqlite3.connect(self.search_db_path) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM search_index WHERE published_date = ?",
                    (target_date,),
                )
                search_count = cursor.fetchone()[0]

            # Count article records
            with sqlite3.connect(self.article_db_path) as conn:
                conn.execute(f"ATTACH DATABASE '{self.search_db_path}' AS search_db")

                # Total articles for this date
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM article_data ad
                    LEFT JOIN search_db.search_index si ON (
                        ad.rss_url = si.rss_url OR ad.real_url = si.real_url
                    )
                    WHERE si.published_date = ?
                    """,
                    (target_date,),
                )
                article_count = cursor.fetchone()[0]

                # Articles with clean text (processed)
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM article_data ad
                    LEFT JOIN search_db.search_index si ON (
                        ad.rss_url = si.rss_url OR ad.real_url = si.real_url
                    )
                    WHERE si.published_date = ? AND ad.clean_text IS NOT NULL
                    """,
                    (target_date,),
                )
                processed_count = cursor.fetchone()[0]

                # Articles with summaries
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM article_data ad
                    LEFT JOIN search_db.search_index si ON (
                        ad.rss_url = si.rss_url OR ad.real_url = si.real_url
                    )
                    WHERE si.published_date = ? AND ad.summarized_text IS NOT NULL
                    """,
                    (target_date,),
                )
                summarized_count = cursor.fetchone()[0]

                # Articles with audio
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM article_data ad
                    LEFT JOIN search_db.search_index si ON (
                        ad.rss_url = si.rss_url OR ad.real_url = si.real_url
                    )
                    WHERE si.published_date = ? AND ad.audio_path IS NOT NULL
                    """,
                    (target_date,),
                )
                audio_count = cursor.fetchone()[0]

                conn.execute("DETACH DATABASE search_db")

            return {
                "search_records": search_count,
                "article_records": article_count,
                "processed_articles": processed_count,
                "summarized_articles": summarized_count,
                "audio_articles": audio_count,
            }

        except Exception as e:
            logger.error(f"Error getting stats for date {target_date}: {e}")
            return {}

    def get_source_statistics(self, target_date: str) -> Dict[str, int]:
        """Get statistics on article count by source for a given date."""
        try:
            with sqlite3.connect(self.search_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT source, COUNT(*) as article_count
                    FROM search_index
                    WHERE DATE(published_date) = ?
                    GROUP BY source
                    ORDER BY article_count DESC
                """,
                    (target_date,),
                )
                result = {
                    row["source"]: row["article_count"] for row in cursor.fetchall()
                }
                return result
        except Exception as e:
            logger.error(f"Error getting source statistics: {e}")
            return {}

    def get_topic_source_breakdown(self, target_date: str) -> Dict[str, Dict[str, int]]:
        """Get breakdown of sources by topic for a given date."""
        try:
            with sqlite3.connect(self.search_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT topic, source, COUNT(*) as article_count
                    FROM search_index
                    WHERE DATE(published_date) = ?
                    GROUP BY topic, source
                    ORDER BY topic, article_count DESC
                """,
                    (target_date,),
                )

                result = {}
                for row in cursor.fetchall():
                    topic = row["topic"]
                    source = row["source"]
                    count = row["article_count"]

                    if topic not in result:
                        result[topic] = {}
                    result[topic][source] = count

                return result
        except Exception as e:
            logger.error(f"Error getting topic source breakdown: {e}")
            return {}
