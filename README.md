# Newsletter Analyst

A Python application for analyzing newsletter onboarding emails using the Gmail API.

## Overview

Newsletter Analyst helps you understand and analyze onboarding email sequences from newsletters. It connects to your Gmail account, retrieves newsletter emails, and provides tools for analyzing their content, structure, and effectiveness.

## Features

- **Gmail API Integration**: Secure OAuth2 authentication with automatic token refresh
- **Email Retrieval**: Fetch emails by labels, search queries, or specific criteria
- **Content Extraction**: Extract both plain text and HTML versions of emails
- **Email Processing**: Metadata extraction, HTML-to-text conversion with structure preservation
- **Deduplication**: Smart hash-based duplicate detection
- **Sequence Detection**: Automatically identify onboarding email sequences (1st, 2nd, 3rd email, etc.)
- **Publisher Tracking**: Manage newsletter publishers with metadata (country, language, business model)
- **Signup Tracking**: Google Sheets-compatible CSV templates for tracking signups
- **SQLite Database**: Local storage for emails and publisher information
- **CLI Interface**: Easy-to-use command-line tools for fetching and analyzing emails
- **Rate Limit Handling**: Automatic retry logic with exponential backoff

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Gmail API

Follow the detailed instructions in [SETUP.md](SETUP.md) to:
- Enable Gmail API in Google Cloud Console
- Download your credentials
- Complete first-time authentication

### 3. Test Your Connection

```bash
python src/gmail_client.py
```

This will authenticate with Gmail and display your 5 most recent emails.

### 4. Run Basic Tests

```bash
python test_basic.py
```

This will test the email processor, database, and optionally Gmail integration.

### 5. Fetch and Process Emails

```bash
# Fetch emails from a specific label
python -m src.main fetch-emails --label "Newsletter-Onboarding" --max-results 20

# Fetch emails since a specific date
python -m src.main fetch-emails --since "2025-01-01" --max-results 50

# Fetch from specific sender
python -m src.main fetch-emails --query "from:newsletter@example.com" --max-results 30
```

## Project Structure

```
newsletteranalyst/
├── src/                      # Source code
│   ├── __init__.py
│   ├── gmail_client.py       # Gmail API client
│   ├── email_processor.py    # Email processing & analysis
│   ├── database.py           # SQLite database operations
│   ├── publisher_manager.py  # Publisher tracking & management
│   └── main.py              # CLI interface
├── config/                  # Configuration files
│   ├── credentials.json     # OAuth credentials (not in repo)
│   └── token.json           # Access token (not in repo)
├── data/                    # Data storage
│   └── newsletter_emails.db # SQLite database (created automatically)
├── output/                  # Analysis outputs & CSV exports
├── .env                     # Environment variables (not in repo)
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
├── test_basic.py            # Basic test script
├── SETUP.md                # Detailed setup guide
├── USAGE.md                # Usage examples
├── PUBLISHER_TRACKING.md   # Publisher tracking guide
└── README.md               # This file
```

## Usage

### CLI Commands

**Fetch and process emails:**
```bash
# Fetch from specific label since a date
python -m src.main fetch-emails --label "Newsletter-Onboarding" --since "2025-01-01"

# Fetch with custom query
python -m src.main fetch-emails --query "from:newsletter@example.com subject:welcome"

# Fetch limited number
python -m src.main fetch-emails --label "INBOX" --max-results 50
```

**View statistics:**
```bash
# Show database statistics
python -m src.main stats

# List all publishers
python -m src.main list-publishers

# Search emails
python -m src.main search --keyword "welcome" --limit 10
python -m src.main search --publisher "Example Newsletter" --sequence 1
```

**Manage publishers:**
```bash
# Add publisher (interactive mode)
python -m src.main add-publisher

# Add publisher (command-line mode)
python -m src.main add-publisher --name "Tech Weekly" --country US --language en

# Export publishers to CSV
python -m src.main export-publishers --output publishers.csv

# Create signup tracking template
python -m src.main create-signup-template
```

### Python API Example

```python
from src import GmailClient, EmailProcessor, NewsletterDatabase

# Initialize components
gmail = GmailClient()
processor = EmailProcessor()
db = NewsletterDatabase()

# Fetch emails
messages = gmail.list_emails(query='from:newsletter@example.com', max_results=50)

# Process each email
for msg in messages:
    email = gmail.get_email(msg['id'])
    body = gmail.extract_email_body(email)

    # Process and analyze
    processed = processor.process_email(email, body['plain'], body['html'])

    # Save to database
    db.save_email(
        message_id=processed['message_id'],
        publisher_name=processed['publisher_name'],
        sender=processed['sender'],
        subject=processed['subject'],
        send_timestamp=processed['timestamp'],
        body_text=processed['body_text'],
        body_html=processed['body_html'],
        raw_json=processed['raw_json']
    )

# Get analytics
stats = db.get_publisher_stats()
for stat in stats:
    print(f"{stat['publisher_name']}: {stat['email_count']} emails")

db.close()
```

## Security

This application uses OAuth2 for secure authentication. Your credentials and tokens are stored locally and should never be committed to version control.

Sensitive files are protected by `.gitignore`:
- `config/credentials.json` - Your OAuth client credentials
- `config/token.json` - Your access token
- `.env` - Environment configuration

## Requirements

- Python 3.10+
- Google account with Gmail
- Google Cloud Platform project with Gmail API enabled

## Next Steps

After setting up the Gmail connection:
1. Create a signup tracking template to organize your newsletter collection
2. Add publishers to track metadata (country, language, business model)
3. Fetch emails and let the system detect onboarding sequences
4. Export data for analysis in Google Sheets or Excel
5. Build custom analysis and visualization tools

## Documentation

- [Setup Guide](SETUP.md) - Gmail API setup and authentication
- [Usage Guide](USAGE.md) - CLI commands and workflows
- [Publisher Tracking](PUBLISHER_TRACKING.md) - Managing publishers and tracking signups
- [Gmail API Docs](https://developers.google.com/gmail/api) - Official Gmail API documentation

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
1. Check [SETUP.md](SETUP.md) troubleshooting section
2. Review Gmail API documentation
3. Open an issue in the repository
