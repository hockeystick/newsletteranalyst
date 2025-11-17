# Quick Start Guide

Get Newsletter Analyst running in under 10 minutes! 🚀

## Prerequisites

- Python 3.10+
- Gmail account
- [Anthropic API key](https://console.anthropic.com/)
- [Google Cloud credentials](https://console.cloud.google.com/)

---

## Option 1: Automated Setup (Recommended)

### 1. Run Setup Script

```bash
./setup.sh
```

### 2. Configure API Keys

Edit `.env` file:
```bash
nano .env
```

Add your keys:
```
GMAIL_CREDENTIALS_PATH=config/credentials.json
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

### 3. Add Gmail Credentials

```bash
# Copy your downloaded OAuth credentials
cp ~/Downloads/client_secret_*.json config/credentials.json
```

### 4. Authenticate Gmail

```bash
python -m src.gmail_client
```

Follow the browser prompts to authorize.

### 5. Fetch & Analyze

```bash
# Fetch 50 newsletters
python src/main.py fetch-emails --label "Newsletter" --max-results 50

# Analyze them
python src/main.py analyze-emails

# Launch dashboard
streamlit run dashboard.py
```

Done! 🎉 Dashboard opens at http://localhost:8501

---

## Option 2: Docker (Easiest)

### 1. Set Up Environment

```bash
# Copy environment file
cp .env.example .env

# Edit with your keys
nano .env
```

### 2. Add Gmail Credentials

```bash
mkdir -p config
cp ~/Downloads/client_secret_*.json config/credentials.json
```

### 3. First-Time Gmail Auth

```bash
# Build image
docker-compose build

# Authenticate (one-time, interactive)
docker-compose run --rm newsletter-analyst python -m src.gmail_client
```

Follow browser prompts to authorize.

### 4. Start Dashboard

```bash
docker-compose up -d
```

Dashboard available at http://localhost:8501

### 5. Run Commands

```bash
# Fetch emails
docker-compose exec newsletter-analyst python src/main.py fetch-emails --label "Newsletter" --max-results 50

# Analyze
docker-compose exec newsletter-analyst python src/main.py analyze-emails
```

---

## Option 3: Manual Setup

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create Directories

```bash
mkdir -p data config output logs
```

### 3. Configure Environment

```bash
cp .env.example .env
nano .env  # Add your API keys
```

### 4. Set Up Gmail

```bash
# Add credentials
cp ~/Downloads/client_secret_*.json config/credentials.json

# Authenticate
python -m src.gmail_client
```

### 5. Run Application

```bash
# Fetch emails
python src/main.py fetch-emails --label "Newsletter" --max-results 50

# Analyze
python src/main.py analyze-emails

# Dashboard
streamlit run dashboard.py
```

---

## Getting Your API Keys

### Anthropic API Key

1. Go to https://console.anthropic.com/
2. Sign up / Log in
3. Click "Get API Keys"
4. Create new key
5. Copy to `.env` file

### Google Cloud Credentials

1. Go to https://console.cloud.google.com/
2. Create project (or select existing)
3. Enable Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search "Gmail API"
   - Click "Enable"
4. Create credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Desktop app"
   - Name it (e.g., "Newsletter Analyst")
   - Download JSON
5. Copy to `config/credentials.json`

---

## Common Commands

```bash
# View help
python src/main.py --help

# Fetch from specific sender
python src/main.py fetch-emails --query "from:newsletter@example.com" --max-results 100

# Analyze with custom settings
python src/main.py analyze-emails --batch-size 5 --delay 2.0

# Export analysis to CSV
python src/main.py export-analysis --output output/analysis.csv

# Generate text report
python src/main.py generate-report

# View database stats
python src/main.py stats

# Search emails
python src/main.py search --keyword "welcome" --limit 20
```

---

## Workflow Example

### Day 1: Initial Setup

```bash
# 1. Set up environment
./setup.sh
nano .env  # Add API keys
cp ~/Downloads/credentials.json config/

# 2. Authenticate Gmail
python -m src.gmail_client

# 3. Fetch all newsletters from last 3 months
python src/main.py fetch-emails --label "Newsletter" --max-results 500

# 4. Analyze (this will take time based on volume)
python src/main.py analyze-emails --delay 1.5

# 5. View results
streamlit run dashboard.py
```

### Ongoing: Regular Updates

```bash
# Fetch new emails (run daily/weekly)
python src/main.py fetch-emails --label "Newsletter" --max-results 100

# Analyze new emails
python src/main.py analyze-emails

# Generate weekly report
python src/main.py generate-report --output output/weekly_$(date +%Y%m%d).txt

# Backup database
./backup.sh
```

---

## Troubleshooting

### "Gmail authentication failed"

```bash
rm config/token.json
python -m src.gmail_client
```

### "Anthropic API key not found"

Check `.env` file has:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

### "Port 8501 already in use"

```bash
# Kill existing process
lsof -ti:8501 | xargs kill -9

# Or use different port
streamlit run dashboard.py --server.port 8502
```

### "Database is locked"

```bash
# Close all other terminals/processes
# Then restart
```

### "Module not found"

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

---

## Next Steps

- ✅ **Automate**: Set up cron jobs for regular fetching
- ✅ **Backup**: Run `./backup.sh` weekly
- ✅ **Explore**: Try different search queries
- ✅ **Analyze**: Look for patterns in the dashboard
- ✅ **Export**: Generate reports for publication

---

## Getting Help

- 📖 **Full Documentation**: See `DEPLOYMENT.md`
- 🐛 **Issues**: Check GitHub Issues
- 💡 **CLI Help**: Run `python src/main.py --help`

---

## Pro Tips

1. **Start small**: Fetch 10-20 emails first to test
2. **Monitor costs**: Check `python src/main.py stats` for API usage
3. **Batch processing**: Use `--batch-size 5` for rate limiting
4. **Regular backups**: Add `./backup.sh` to crontab
5. **Use labels**: Organize Gmail with labels for easier fetching

---

Happy analyzing! 📧✨
