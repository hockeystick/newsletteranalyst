# Newsletter Analyst

A Python application for analyzing newsletter onboarding emails using the Gmail API.

## Overview

Newsletter Analyst helps you understand and analyze onboarding email sequences from newsletters. It connects to your Gmail account, retrieves newsletter emails, and provides tools for analyzing their content, structure, and effectiveness.

## Features

- **Gmail API Integration**: Secure OAuth2 authentication with automatic token refresh
- **Email Retrieval**: Fetch emails by labels, search queries, or specific criteria
- **Content Extraction**: Extract both plain text and HTML versions of emails
- **Rate Limit Handling**: Automatic retry logic with exponential backoff
- **Easy Testing**: Built-in test function to verify your connection

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

## Project Structure

```
newsletteranalyst/
├── src/                    # Source code
│   ├── __init__.py
│   └── gmail_client.py    # Gmail API client
├── config/                # Configuration files
│   ├── credentials.json   # OAuth credentials (not in repo)
│   └── token.json         # Access token (not in repo)
├── data/                  # Data storage
├── output/                # Analysis outputs
├── .env                   # Environment variables (not in repo)
├── .env.example           # Environment template
├── requirements.txt       # Python dependencies
├── SETUP.md              # Detailed setup guide
└── README.md             # This file
```

## Usage Example

```python
from src.gmail_client import GmailClient

# Initialize the client
client = GmailClient()

# Search for newsletter emails
emails = client.list_emails(
    query='from:newsletter@example.com',
    max_results=50
)

# Analyze each email
for msg in emails:
    email = client.get_email(msg['id'])
    headers = client.get_email_headers(email)
    body = client.extract_email_body(email)

    print(f"Subject: {headers['subject']}")
    print(f"From: {headers['from']}")
    print(f"Plain text length: {len(body['plain'])}")
    print(f"Has HTML: {bool(body['html'])}")
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
1. Build email analysis features
2. Create visualization tools
3. Generate insights from newsletter sequences

## Documentation

- [Setup Guide](SETUP.md) - Detailed setup instructions
- [Gmail API Docs](https://developers.google.com/gmail/api) - Official Gmail API documentation

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
1. Check [SETUP.md](SETUP.md) troubleshooting section
2. Review Gmail API documentation
3. Open an issue in the repository
