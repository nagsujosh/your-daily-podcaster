# flake8: noqa
#!/usr/bin/env python3
"""
Step-by-Step Test Suite for Your Daily Podcaster

This script allows you to test each component individually and debug issues.
Run specific tests by commenting/uncommenting the test functions at the bottom.
"""

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

from yourdaily.utils.db import DatabaseManager
from yourdaily.utils.time import get_yesterday_date


def test_environment_setup():
    """Test 1: Environment and basic setup."""
    print("\n" + "=" * 60)
    print("TEST 1: Environment Setup")
    print("=" * 60)

    from yourdaily.utils.logger import setup_logger

    setup_logger()

    # Load environment variables
    load_dotenv()

    # Check required API keys
    gemini_key = os.getenv("GEMINI_KEY")
    tts_creds = os.getenv("GCLOUD_TTS_CREDS")
    gnews_key = os.getenv("GNEWS_API_KEY")

    print(f"✅ GEMINI_KEY: {'Set' if gemini_key else '❌ Missing'}")
    print(f"✅ GCLOUD_TTS_CREDS: {'Set' if tts_creds else '❌ Missing'}")
    print(f"✅ GNEWS_API_KEY: {'Set' if gnews_key else '⚠️ Optional'}")

    # Test imports
    try:
        from google.cloud import texttospeech

        print("✅ Google Cloud TTS imported")
    except ImportError as e:
        print(f"❌ Google Cloud TTS import failed: {e}")

    try:
        import google.generativeai as genai

        print("✅ Google Generative AI imported")
    except ImportError as e:
        print(f"❌ Google Generative AI import failed: {e}")

    try:
        from gnews import GNews

        print("✅ GNews imported")
    except ImportError as e:
        print(f"❌ GNews import failed: {e}")

    return True


def test_database_creation():
    """Test 2: Database creation and schema."""
    print("\n" + "=" * 60)
    print("TEST 2: Database Creation")
    print("=" * 60)

    from yourdaily.utils.logger import setup_logger

    setup_logger()

    try:
        # Initialize database
        DatabaseManager(
            search_db_path="data/db/search_index.db",
            article_db_path="data/db/article_data.db",
        )
        print("✅ Database manager initialized")

        # Check if tables exist
        # Check search_index table
        conn = sqlite3.connect("data/db/search_index.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND "
            "name='search_index'"
        )
        if cursor.fetchone():
            print("✅ search_index table exists")
        else:
            print("❌ search_index table missing")

        # Check article_data table
        conn2 = sqlite3.connect("data/db/article_data.db")
        cursor2 = conn2.cursor()
        cursor2.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND "
            "name='article_data'"
        )
        if cursor2.fetchone():
            print("✅ article_data table exists")
        else:
            print("❌ article_data table missing")

        conn.close()
        conn2.close()

        return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


def test_topics_loading():
    """Test 3: Topics.md loading."""
    print("\n" + "=" * 60)
    print("TEST 3: Topics Loading")
    print("=" * 60)

    try:
        import frontmatter

        # Check if Topics.md exists
        topics_file = "data/Topics.md"
        if not os.path.exists(topics_file):
            print(f"❌ Topics.md not found at {topics_file}")
            return False

        print(f"✅ Topics.md found at {topics_file}")

        # Load and parse topics
        with open(topics_file, "r", encoding="utf-8") as f:
            content = f.read()

        post = frontmatter.loads(content)
        topics = post.get("topics", [])

        print(f"✅ Loaded {len(topics)} topics:")
        for i, topic in enumerate(topics[:5], 1):  # Show first 5
            print(f"   {i}. {topic}")

        if len(topics) > 5:
            print(f"   ... and {len(topics) - 5} more")

        return True

    except Exception as e:
        print(f"❌ Topics loading failed: {e}")
        return False


def test_gnews_api():
    """Test 4: GNews API connectivity."""
    print("\n" + "=" * 60)
    print("TEST 4: GNews API")
    print("=" * 60)

    try:
        from gnews import GNews

        load_dotenv()

        # Initialize GNews
        gnews = GNews(language="en", country="US", max_results=10)

        # Set API key if available
        api_key = os.getenv("GNEWS_API_KEY")
        if api_key:
            gnews.api_key = api_key
            print("✅ Using GNews API key")
        else:
            print("Using GNews free tier (limited)")

        # Test search
        yesterday = get_yesterday_date()
        print(f"🔍 Searching for 'technology' articles from {yesterday}")

        articles = gnews.get_news("technology")

        if articles:
            print(f"✅ Found {len(articles)} articles")
            print(f"Sample article: {articles[0].get('title', 'No title')[:50]}...")

            # Check for yesterday's articles
            yesterday_articles = [
                a for a in articles if a.get("published date", "").startswith(yesterday)
            ]
            print(f"Articles from yesterday: {len(yesterday_articles)}")

        else:
            print("No articles found (this might be normal for free tier)")

        return True

    except Exception as e:
        print(f"❌ GNews API test failed: {e}")
        return False


def test_sample_data_creation():
    """Test 5: Create sample data for testing."""
    print("\n" + "=" * 60)
    print("TEST 5: Sample Data Creation")
    print("=" * 60)

    try:
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
                "gnews_date": get_yesterday_date(),
                "published_date": get_yesterday_date(),
            },
            {
                "topic": "Business",
                "title": "Major Tech Company Announces New Product",
                "url": "https://example.com/business-news-1",
                "source": "Business Daily",
                "gnews_date": get_yesterday_date(),
                "published_date": get_yesterday_date(),
            },
            {
                "topic": "Science",
                "title": "Breakthrough in Renewable Energy",
                "url": "https://example.com/science-news-1",
                "source": "Science Daily",
                "gnews_date": get_yesterday_date(),
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

        # Test simple generation
        model = genai.GenerativeModel("gemini-1.5-flash")

        test_prompt = (
            "Summarize this in one sentence: AI technology is advancing rapidly."
        )
        response = model.generate_content(test_prompt)

        print("✅ Gemini API connection successful")
        print(f"Test response: {response.text}")

        return True

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
    """Test 9: Full pipeline with sample data."""
    print("\n" + "=" * 60)
    print("TEST 9: Full Pipeline")
    print("=" * 60)

    try:
        # Run the full pipeline
        from run_pipeline import run_pipeline

        result = run_pipeline()

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
    """Main test runner."""
    print("Your Daily Podcaster - Step-by-Step Test Suite")
    print("=" * 60)
    print("Run specific tests by uncommenting them below")
    print("=" * 60)

    # ========================================
    # UNCOMMENT THE TESTS YOU WANT TO RUN
    # ========================================

    # Basic setup tests
    test_environment_setup()
    test_database_creation()
    test_topics_loading()

    # API tests
    test_gnews_api()
    test_gemini_api()
    test_tts_setup()

    # Data and processing tests
    test_sample_data_creation()
    test_audio_generation()

    # Full pipeline test (run last)
    # test_full_pipeline()

    print("\n" + "=" * 60)
    print("Test suite completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Fix any ❌ errors above")
    print("2. Uncomment test_full_pipeline() to test the complete system")
    print("3. Check generated files in data/audio/ directory")


if __name__ == "__main__":
    main()
