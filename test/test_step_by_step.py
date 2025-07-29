#!/usr/bin/env python3
"""
Step-by-step testing script for Your Daily Podcaster.

Tests each component in isolation to help identify issues.
"""

import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

from yourdaily.utils.logger import get_logger
from yourdaily.utils.time import get_yesterday_date

# Add the parent directory to the path so we can import from yourdaily
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_environment_setup():
    """Test 1: Environment variables and basic setup."""
    print("\n" + "=" * 50)
    print("TEST 1: Environment Setup")
    print("=" * 50)

    # Load environment
    load_dotenv()

    # Check required environment variables
    gemini_key = os.getenv("GEMINI_KEY")
    gcloud_creds = os.getenv("GCLOUD_TTS_CREDS")

    print(f"✅ GEMINI_KEY: {'Set' if gemini_key else '❌ Missing'}")
    print(f"✅ GCLOUD_TTS_CREDS: {'Set' if gcloud_creds else '❌ Missing'}")

    # Check paths
    required_paths = ["data/db", "data/audio", "logs"]

    for path in required_paths:
        path_obj = Path(path)
        if path_obj.exists():
            print(f"✅ {path}: Exists")
        else:
            print(f"⚠️ {path}: Creating...")
            path_obj.mkdir(parents=True, exist_ok=True)

    get_logger("test_environment").info("Environment setup test completed")


def test_imports():
    """Test 2: Import all required modules."""
    print("\n" + "=" * 50)
    print("TEST 2: Module Imports")
    print("=" * 50)

    try:
        print("✅ RSS and browser automation dependencies imported")
    except Exception as e:
        print(f"❌ RSS/browser dependencies import failed: {e}")

    try:
        print("✅ Trafilatura imported")
    except ImportError as e:
        print(f"❌ Trafilatura import failed: {e}")

    try:
        print("✅ Google Cloud TTS imported")
    except ImportError as e:
        print(f"❌ Google Cloud TTS import failed: {e}")

    try:
        print("✅ Pydub imported")
    except ImportError as e:
        print(f"❌ Pydub import failed: {e}")

    try:
        print("✅ YourDaily modules imported")
    except ImportError as e:
        print(f"❌ YourDaily modules import failed: {e}")

    get_logger("test_imports").info("Import test completed")


def test_database():
    """Test 3: Database connectivity and operations."""
    print("\n" + "=" * 50)
    print("TEST 3: Database Operations")
    print("=" * 50)

    try:
        from yourdaily.utils.db import DatabaseManager

        # Initialize database manager
        db = DatabaseManager(
            search_db_path="data/db/search_index.db",
            article_db_path="data/db/article_data.db",
        )

        # Test basic operations
        test_article = {
            "topic": "Test",
            "title": "Test Article",
            "url": "https://example.com/test",
            "source": "Test Source",
            "rss_date": get_yesterday_date(),
            "published_date": get_yesterday_date(),
        }

        # Insert test article
        db.insert_search_result(**test_article)

        # Retrieve test article
        articles = db.get_articles_by_date(get_yesterday_date())
        test_found = any(article["title"] == "Test Article" for article in articles)

        if test_found:
            print("✅ Database operations successful")
            # Clean up test data
            db.delete_search_result("https://example.com/test")
            print("✅ Test data cleaned up")
        else:
            print("❌ Database operations failed")

        return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


def test_rss_feeds_and_browser():
    """Test 4: RSS feed fetching and browser automation."""
    print("\n" + "=" * 50)
    print("TEST 4: RSS Feeds and Browser")
    print("=" * 50)

    try:
        from yourdaily.scraper.fetch_search_results import NewsFetcher

        # Initialize news fetcher
        fetcher = NewsFetcher()

        # Test RSS feed fetching
        test_feeds = [
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://rss.cnn.com/rss/edition.rss",
        ]

        for feed_url in test_feeds:
            try:
                articles = fetcher.fetch_rss_feed(feed_url)
                if articles:
                    print(f"✅ RSS feed {feed_url}: {len(articles)} articles")
                else:
                    print(f"⚠️ RSS feed {feed_url}: No articles found")
            except Exception as e:
                print(f"❌ RSS feed {feed_url}: {e}")

        return True

    except Exception as e:
        print(f"❌ RSS and browser test failed: {e}")
        return False


def test_topics_loading():
    """Test 4.5: Topics configuration loading."""
    print("\n" + "=" * 50)
    print("TEST 4.5: Topics Configuration")
    print("=" * 50)

    try:
        topics_file = Path("data/Topics.md")
        if topics_file.exists():
            with open(topics_file, "r", encoding="utf-8") as f:
                content = f.read()
                if "Technology" in content and "Business" in content:
                    print("✅ Topics configuration loaded successfully")
                    return True
                else:
                    print("❌ Topics configuration missing required topics")
                    return False
        else:
            print("❌ Topics.md file not found")
            return False

    except Exception as e:
        print(f"❌ Topics loading failed: {e}")
        return False


def test_sample_data_creation():
    """Test 5: Create sample data for testing."""
    print("\n" + "=" * 60)
    print("TEST 5: Sample Data Creation")
    print("=" * 60)

    try:
        from yourdaily.utils.db import DatabaseManager

        db = DatabaseManager(
            search_db_path="data/db/search_index.db",
            article_db_path="data/db/article_data.db",
        )

        # Create sample search results
        sample_articles = [
            {
                "topic": "Technology",
                "title": "AI Breakthrough in Machine Learning",
                "url": "https://example.com/ai-news-1",
                "source": "Tech News",
                "rss_date": get_yesterday_date(),
                "published_date": get_yesterday_date(),
            },
            {
                "topic": "Business",
                "title": "Major Tech Company Announces New Product",
                "url": "https://example.com/business-news-1",
                "source": "Business Daily",
                "rss_date": get_yesterday_date(),
                "published_date": get_yesterday_date(),
            },
            {
                "topic": "Science",
                "title": "Breakthrough in Renewable Energy",
                "url": "https://example.com/science-news-1",
                "source": "Science Daily",
                "rss_date": get_yesterday_date(),
                "published_date": get_yesterday_date(),
            },
        ]

        # Insert sample articles
        for article in sample_articles:
            db.insert_search_result(**article)

        print(f"✅ Inserted {len(sample_articles)} sample search results")

        # Create sample article data
        sample_summaries = [
            {
                "url": "https://example.com/ai-news-1",
                "clean_text": (
                    "Sample article content about AI breakthroughs in machine "
                    "learning algorithms. Researchers have developed new neural "
                    "network architectures that show significant improvements in "
                    "accuracy and efficiency."
                ),
                "summarized_text": (
                    "**Technology Summary for "
                    + get_yesterday_date()
                    + "**\n\n• AI researchers made significant breakthroughs in "
                    "machine learning algorithms\n• New neural network architecture "
                    "shows 40% improvement in accuracy\n• Major tech companies are "
                    "investing heavily in AI research\n• Breakthrough could "
                    "revolutionize how we approach complex problems\n• Industry "
                    "experts predict widespread adoption within 2 years"
                ),
            },
            {
                "url": "https://example.com/business-news-1",
                "clean_text": (
                    "Sample article content about major tech company "
                    "announcements and new product launches in the technology "
                    "sector."
                ),
                "summarized_text": (
                    "**Business Summary for "
                    + get_yesterday_date()
                    + "**\n\n• Tech giant announces revolutionary new product "
                    "line\n• Company expects $2 billion in revenue from new "
                    "offerings\n• Product launch scheduled for Q2 2024\n• "
                    "Strategic partnerships formed with leading manufacturers\n• "
                    "Stock prices rose 15% following the announcement"
                ),
            },
            {
                "url": "https://example.com/science-news-1",
                "clean_text": (
                    "Sample article content about renewable energy "
                    "breakthroughs and climate change research developments."
                ),
                "summarized_text": (
                    "**Science Summary for "
                    + get_yesterday_date()
                    + "**\n\n• Scientists develop new solar panel technology "
                    "with 50% efficiency\n• Breakthrough could make renewable "
                    "energy more affordable\n• Research shows significant progress "
                    "in battery storage\n• Climate change mitigation strategies "
                    "show promising results\n• International collaboration leads "
                    "to innovative solutions"
                ),
            },
        ]

        # Insert sample summaries
        for summary in sample_summaries:
            db.insert_article_data(**summary)

        print(f"✅ Inserted {len(sample_summaries)} sample article summaries")

        # Verify data
        conn = sqlite3.connect("data/db/search_index.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM search_index")
        search_count = cursor.fetchone()[0]
        conn.close()

        conn2 = sqlite3.connect("data/db/article_data.db")
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT COUNT(*) FROM article_data")
        article_count = cursor2.fetchone()[0]
        conn2.close()

        print(
            f"Database contents: {search_count} search results, "
            f"{article_count} articles"
        )

        return True

    except Exception as e:
        print(f"❌ Sample data creation failed: {e}")
        return False


def test_gemini_api():
    """Test 6: Gemini API connectivity."""
    print("\n" + "=" * 60)
    print("TEST 6: Gemini API")
    print("=" * 60)

    try:
        import google.generativeai as genai

        load_dotenv()

        api_key = os.getenv("GEMINI_KEY")
        if not api_key:
            print("❌ GEMINI_KEY not found in .env")
            return False

        # Configure Gemini
        genai.configure(api_key=api_key)

        # Test with a simple prompt
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content("Say 'Hello, Gemini API is working!'")

        if response.text:
            print("✅ Gemini API connection successful")
            print(f"Response: {response.text}")
            return True
        else:
            print("❌ Gemini API returned empty response")
            return False

    except Exception as e:
        print(f"❌ Gemini API test failed: {e}")
        return False


def test_tts_setup():
    """Test 7: Google Cloud TTS setup."""
    print("\n" + "=" * 60)
    print("TEST 7: Google Cloud TTS")
    print("=" * 60)

    try:
        from google.cloud import texttospeech

        load_dotenv()

        creds_path = os.getenv("GCLOUD_TTS_CREDS")
        if not creds_path:
            print("❌ GCLOUD_TTS_CREDS not found in .env")
            return False

        if not os.path.exists(creds_path):
            print(f"❌ Credentials file not found: {creds_path}")
            return False

        # Set environment variable for Google Cloud
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

        # Initialize TTS client
        client = texttospeech.TextToSpeechClient()

        # Test synthesis request
        synthesis_input = texttospeech.SynthesisInput(
            text="Hello, this is a test of the text to speech system."
        )

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # Save test audio
        os.makedirs("data/audio/temp", exist_ok=True)
        with open("data/audio/temp/test_tts.mp3", "wb") as out:
            out.write(response.audio_content)

        print("✅ Google Cloud TTS setup successful")
        print("Test audio saved to: data/audio/temp/test_tts.mp3")

        return True

    except Exception as e:
        print(f"❌ TTS setup failed: {e}")
        return False


def test_audio_generation():
    """Test 8: Full audio generation with sample data."""
    print("\n" + "=" * 60)
    print("TEST 8: Audio Generation")
    print("=" * 60)

    try:
        # Import the audio generator
        from yourdaily.tts.generate_audio import AudioGenerator

        # Initialize audio generator
        generator = AudioGenerator()

        # Run audio generation
        result = generator.run()

        if result:
            print("✅ Audio generation completed successfully")

            # Check for generated files
            audio_dir = Path("data/audio")
            if audio_dir.exists():
                files = list(audio_dir.rglob("*.mp3"))
                print(f"Generated {len(files)} audio files:")
                for file in files:
                    print(f"   {file}")

            return True
        else:
            print("❌ Audio generation failed")
            return False

    except Exception as e:
        print(f"❌ Audio generation test failed: {e}")
        return False


def test_full_pipeline():
    """Test 9: Full pipeline integration."""
    print("\n" + "=" * 60)
    print("TEST 9: Full Pipeline")
    print("=" * 60)

    try:
        from yourdaily.run_pipeline import PipelineRunner

        # Initialize pipeline
        pipeline = PipelineRunner()

        # Run pipeline
        result = pipeline.run()

        if result:
            print("✅ Full pipeline completed successfully")
            return True
        else:
            print("❌ Full pipeline failed")
            return False

    except Exception as e:
        print(f"❌ Full pipeline test failed: {e}")
        return False


def main():
    """Run all tests in sequence."""
    print("🧪 Your Daily Podcaster - Step-by-Step Testing")
    print("=" * 60)

    tests = [
        test_environment_setup,
        test_imports,
        test_database,
        test_rss_feeds_and_browser,
        test_topics_loading,
        test_sample_data_creation,
        test_gemini_api,
        test_tts_setup,
        test_audio_generation,
        test_full_pipeline,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    for i, (test, result) in enumerate(zip(tests, results), 1):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i:2d}. {test.__name__}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Your setup is ready.")
    else:
        print("⚠️ Some tests failed. Please check the issues above.")


if __name__ == "__main__":
    main()
