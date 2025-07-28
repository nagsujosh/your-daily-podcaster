# yourdailypodcaster

An AI-powered automated daily podcast generator that creates personalized audio news digests.

## Features

- **Automated News Collection**: Fetches articles from GNews based on your topics
- **AI Summarization**: Uses Gemini API to create concise bullet-point summaries
- **High-Quality TTS**: Converts summaries to natural-sounding audio using Google Cloud TTS
- **Daily Automation**: Runs automatically via GitHub Actions
- **Spotify Publishing**: Generates RSS feeds compatible with Spotify Podcasts

## Setup

### 1. Install the Package
```bash
# Make sure you have a recent version of pip (21.3+)
python -m pip install --upgrade pip

# Install in development mode
pip install -e .
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your API keys:
- `GEMINI_KEY`: Your Google Gemini API key
- `GCLOUD_TTS_CREDS`: Path to your Google Cloud service account JSON file

### 3. Set Up Topics
Edit `data/Topics.md` to define your news topics of interest.

## 📁 Project Structure

```
yourDailyPodcaster/
├── yourdaily/             # Main package
│   ├── __init__.py        # Package initialization
│   ├── run_pipeline.py    # Main pipeline orchestrator
│   ├── scraper/           # News fetching & content scraping
│   ├── summarizer/        # AI summarization with Gemini
│   ├── tts/               # Text-to-speech generation
│   ├── publisher/         # RSS feed & Spotify publishing
│   ├── cleaner/           # Cleanup utilities
│   └── utils/             # Shared utilities
├── data/
│   ├── Topics.md          # Your news topics
│   ├── db/                # SQLite databases
│   └── audio/             # Generated audio files
├── test/                  # Test suite
├── run_pipeline.py        # Entry point script
└── .github/workflows/     # GitHub Actions automation
```

## Usage

### Using the CLI
```bash
# Run the entire pipeline
daily-podcaster

# Or use the entry point script
python run_pipeline.py
```

### Using the Package
```python
from yourdaily import get_logger, setup_logger
from yourdaily.run_pipeline import PipelineOrchestrator

# Setup logging
setup_logger()
logger = get_logger("my_script")

# Run the pipeline
orchestrator = PipelineOrchestrator()
result = orchestrator.run()
```

### Manual Run (Individual Steps)
```bash
# Step 1: Fetch news articles
python -m yourdaily.scraper.fetch_search_results

# Step 2: Scrape article content
python -m yourdaily.scraper.scrape_articles

# Step 3: Summarize articles
python -m yourdaily.summarizer.summarize_articles

# Step 4: Generate audio
python -m yourdaily.tts.generate_audio

# Step 5: Publish podcast
python -m yourdaily.publisher.publish_to_spotify

# Step 6: Cleanup
python -m yourdaily.cleaner.cleanup
```

### Automated Daily Run
The GitHub Action in `.github/workflows/daily_run.yml` will run the entire pipeline daily at 8:00 AM UTC.

### GitHub Actions Setup
1. Add the following secrets to your GitHub repository:
   - `GEMINI_KEY`: Your Google Gemini API key
   - `GCLOUD_TTS_CREDS`: Your Google Cloud service account JSON (as a string)
   - `GNEWS_API_KEY`: Your GNews API key (optional)

2. The workflow will automatically:
   - Run daily at 8:00 AM UTC
   - Generate the podcast
   - Create a GitHub release with the audio file
   - Upload artifacts for 7 days
   - Clean up temporary files

## Database Schema

### search_index.db
Stores article metadata and search results.

### article_data.db
Stores cleaned content, summaries, and audio file paths.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request
