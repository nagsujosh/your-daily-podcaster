# Configuration Guide

## Quick Start

1. **Clone and Setup**
   ```bash
   git clone https://github.com/nagsujosh/your-daily-podcaster
   cd yourDailyPodcaster
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies**
   ```bash
   # Install with all extras (dev, test, docs)
   pip install -e ".[dev,test,docs]"

   # Or install just the main dependencies
   pip install -e .
   ```

3. **Setup Git and Pre-commit**
   ```bash
   # Initialize git repository
   git init

   # Install pre-commit hooks
   pre-commit install
   ```

4. **Configure API Keys**
   ```bash
   # Create .env file manually
   touch .env
   ```
   # Edit .env with your API keys (see Environment Variables section below)

5. **Customize Topics**
   ```bash
   # Edit data/Topics.md with your preferred news topics
   ```

6. **Test Setup**
   ```bash
   # Run tests
   pytest

   # Or run the pipeline directly
   daily-podcaster
   ```

### Available Commands
```bash
# Install dependencies
make install

# Run tests
make test

# Format code (black + isort)
make format

# Lint code (flake8 + mypy)
make lint

# Run all pre-commit hooks
make precommit
```

## API Keys Setup

### Google Gemini API
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add to `.env`: `GEMINI_KEY=your_key_here`

### Google Cloud TTS
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the Cloud Text-to-Speech API
4. Create a service account and download JSON credentials
5. Add to `.env`: `GCLOUD_TTS_CREDS=path/to/credentials.json`

### News Source Configuration
The application now uses Google News RSS feeds directly, eliminating the need for external API keys. Articles are fetched using browser automation for reliable access.

## Environment Variables

```env
GEMINI_KEY=GEMINI_KEY
GCLOUD_TTS_CREDS=PATH/TO/YOUR/JSON/FILE
SEARCH_DB_PATH=data/db/search_index.db
ARTICLE_DB_PATH=data/db/article_data.db
AUDIO_OUTPUT_DIR=data/audio
TEMP_AUDIO_DIR=data/audio/temp
LOG_LEVEL=INFO
LOG_FILE=logs/podcaster.log
PODCAST_FEED_URL=https://yourdomain.com/podcast.xml
AUDIO_BASE_URL=https://yourdomain.com/audio/
PODCAST_OWNER_EMAIL=your-email@example.com
```

## Code Quality Tools

### Pre-commit Hooks
The project uses pre-commit hooks to maintain code quality:

- **trailing-whitespace**: Removes trailing spaces
- **end-of-file-fixer**: Ensures files end with newline
- **check-yaml**: Validates YAML files
- **check-added-large-files**: Warns about large files
- **check-merge-conflict**: Detects merge conflict markers
- **black**: Formats Python code
- **isort**: Sorts imports
- **flake8**: Lints Python code

### Running Code Quality Checks
```bash
# Run all hooks on staged files
pre-commit run

# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black
pre-commit run flake8
```

### Code Formatting
The project uses:
- **Black** (line length: 88)
- **isort** (profile: black)
- **flake8** (max line length: 88)

## Customizing Topics

Edit `data/Topics.md` to define your news topics:

```markdown
---
title: "Daily News Topics"
description: "Topics to monitor for daily news podcast"
last_updated: "2024-01-01"
topics:
  - "AI breakthroughs and developments"
  - "Major tech company news"
  - "Cybersecurity incidents"
  - "New product launches"
  - "Stock market highlights"
  - "Major mergers and acquisitions"
  - "Economic policy changes"
  - "Cryptocurrency developments"
  - "Medical breakthroughs"
  - "Climate change research"
  - "Space exploration updates"
  - "Public health announcements"
  - "US political developments"
  - "International relations"
  - "Policy changes"
  - "Election updates"
  - "Major entertainment industry news"
  - "Streaming service updates"
  - "Gaming industry developments"
  - "Celebrity tech investments"
---
```

## GitHub Actions Setup

### Repository Secrets
Add these secrets to your GitHub repository:

1. **GEMINI_KEY**: Your Google Gemini API key
2. **GCLOUD_TTS_CREDS**: Your Google Cloud service account JSON (as a string)


### Workflow Configuration
The workflow runs daily at 8:00 AM UTC. To change the schedule, edit `.github/workflows/daily_run.yml`:

```yaml
on:
  schedule:
    # Change this cron expression as needed
    - cron: '0 8 * * *'  # 8:00 AM UTC daily
```

## Audio Configuration

### Voice Settings
Edit `tts/generate_audio.py` to customize voice settings:

```python
# Audio settings
self.voice_name = "en-US-Neural2-F"  # Change voice
self.speaking_rate = 0.9  # Adjust speed (0.25 to 4.0)
```

### Available Voices
- `en-US-Neural2-F` (Female)
- `en-US-Neural2-M` (Male)
- `en-US-Neural2-A` (Female, alternative)
- `en-US-Neural2-C` (Male, alternative)
- `en-US-Neural2-D` (Female, alternative)
- `en-US-Neural2-E` (Male, alternative)
- `en-US-Neural2-F` (Female, alternative)
- `en-US-Neural2-G` (Female, alternative)
- `en-US-Neural2-H` (Female, alternative)
- `en-US-Neural2-I` (Male, alternative)
- `en-US-Neural2-J` (Male, alternative)

## Podcast Publishing

### RSS Feed Configuration
The system generates an RSS feed at `data/audio/podcast.xml`. To make it publicly accessible:

1. **GitHub Pages**: Enable GitHub Pages in your repository settings
2. **Custom Domain**: Update `PODCAST_FEED_URL` and `AUDIO_BASE_URL` in `.env`
3. **CDN**: Upload files to a CDN and update the URLs

### Spotify Submission
1. **Configure owner email**: Set `PODCAST_OWNER_EMAIL` in your `.env` file (required by Spotify)
2. Generate the RSS feed with the updated configuration
3. Submit the RSS feed URL to Spotify for Podcasters
4. Wait for approval (usually 24-48 hours)

**Note**: Spotify requires an email address in the RSS feed's `itunes:owner` element. Make sure to set the `PODCAST_OWNER_EMAIL` environment variable before generating your RSS feed.

## Development Workflow

### Daily Development
```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Make changes to code

# 3. Stage changes
git add .

# 4. Pre-commit hooks run automatically on commit
git commit -m "Your commit message"

# 5. Run tests
make test

# 6. Push changes
git push
```

### Adding New Dependencies
```bash
# Add to pyproject.toml dependencies section
# Then reinstall
pip install -e ".[dev,test,docs]"
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific test file
pytest test/test_basic.py
```

## Performance & Maintenance

### Memory Usage
- Cleanup runs automatically after each pipeline
- Old data is removed after 7 days
- Logs are rotated automatically

### API Costs
- **Gemini API**: ~$0.0015 per 1K characters
- **Google Cloud TTS**: ~$4.00 per 1M characters
- **Google News RSS**: Free, no API key required

### Custom Cleanup Rules
Edit `cleaner/cleanup.py` to customize cleanup behavior:

```python
# Cleanup settings
self.keep_final_audio_days = 7  # Keep final podcasts for 7 days
self.cleanup_old_data_days = 7  # Clean article data older than 7 days
```
