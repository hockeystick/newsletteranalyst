# Newsletter Analyst - Gmail API Setup Guide

This guide walks you through setting up Gmail API access for the Newsletter Analyst application.

## Prerequisites

- Python 3.10 or higher
- A Google account with Gmail access
- Google Cloud Platform account (free tier is sufficient)

## Step 1: Install Dependencies

First, install the required Python packages:

```bash
pip install -r requirements.txt
```

## Step 2: Enable Gmail API in Google Cloud Console

### 2.1 Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top of the page
3. Click **"New Project"**
4. Enter a project name (e.g., "Newsletter Analyst")
5. Click **"Create"**

### 2.2 Enable Gmail API

1. In the Google Cloud Console, make sure your new project is selected
2. Navigate to **"APIs & Services"** > **"Library"** (or use the search bar)
3. Search for **"Gmail API"**
4. Click on **"Gmail API"** from the results
5. Click the **"Enable"** button

### 2.3 Configure OAuth Consent Screen

1. Go to **"APIs & Services"** > **"OAuth consent screen"**
2. Select **"External"** user type (unless you have Google Workspace)
3. Click **"Create"**
4. Fill in the required fields:
   - **App name**: Newsletter Analyst
   - **User support email**: Your email address
   - **Developer contact information**: Your email address
5. Click **"Save and Continue"**
6. On the **Scopes** page, click **"Add or Remove Scopes"**
7. Filter for "Gmail API" and select:
   - `.../auth/gmail.readonly` (Read all resources and metadata)
8. Click **"Update"** and then **"Save and Continue"**
9. On the **Test users** page, click **"Add Users"**
10. Add your Gmail address as a test user
11. Click **"Save and Continue"**
12. Review the summary and click **"Back to Dashboard"**

### 2.4 Create OAuth 2.0 Credentials

1. Go to **"APIs & Services"** > **"Credentials"**
2. Click **"+ Create Credentials"** at the top
3. Select **"OAuth client ID"**
4. Choose **"Desktop app"** as the application type
5. Enter a name (e.g., "Newsletter Analyst Desktop")
6. Click **"Create"**
7. A dialog will appear with your client ID and secret - click **"OK"**
8. You'll see your new OAuth 2.0 Client ID in the list

## Step 3: Download credentials.json

1. In the **Credentials** page, find your newly created OAuth 2.0 Client ID
2. Click the **download icon** (⬇️) on the right side of the credential row
3. This will download a JSON file (usually named something like `client_secret_xxxxx.json`)
4. Rename this file to **`credentials.json`**
5. Move it to the **`config/`** folder in your project:

```bash
mv ~/Downloads/client_secret_*.json config/credentials.json
```

## Step 4: Configure Environment Variables

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Open `.env` and verify the path is correct:

```env
GMAIL_CREDENTIALS_PATH=config/credentials.json
```

## Step 5: Run First-Time Authentication

Now you're ready to authenticate with Gmail!

### 5.1 Run the Test Script

```bash
python src/gmail_client.py
```

### 5.2 Complete OAuth Flow

1. The script will open your default web browser
2. You may see a warning: **"Google hasn't verified this app"**
   - Click **"Advanced"**
   - Click **"Go to Newsletter Analyst (unsafe)"**
3. Sign in with your Google account (the one you added as a test user)
4. Review the permissions requested
5. Click **"Allow"**
6. You should see a success message in the browser
7. The browser tab can be closed

### 5.3 Verify Authentication

Back in your terminal, you should see:

```
Successfully authenticated with Gmail API
Token saved to config/token.json

============================================================
Testing Gmail API Connection
============================================================

Connected to: your.email@gmail.com
Total messages: XXXX
Total threads: XXXX

Fetching last 5 emails...
```

The script will display information about your 5 most recent emails.

## Step 6: Understanding the Files

After successful authentication, you'll have these new files:

- **`config/credentials.json`**: Your OAuth 2.0 client credentials (keep private!)
- **`config/token.json`**: Your access token (auto-refreshes, keep private!)
- **`.env`**: Your environment configuration (keep private!)

### Important Security Notes

⚠️ **Never commit these files to version control!**

Add them to `.gitignore`:

```bash
echo "config/credentials.json" >> .gitignore
echo "config/token.json" >> .gitignore
echo ".env" >> .gitignore
```

## Troubleshooting

### "File not found: config/credentials.json"

- Ensure you downloaded the credentials file from Google Cloud Console
- Verify it's named exactly `credentials.json`
- Confirm it's in the `config/` directory

### "The user must be in the list of test users"

- Go back to OAuth consent screen in Google Cloud Console
- Add your Gmail address to the test users list
- Try authenticating again

### "Token refresh failed"

- Delete `config/token.json`
- Run the authentication script again
- This will create a fresh token

### "Rate limit exceeded"

- The client includes automatic retry logic with exponential backoff
- If you see this error, the script will wait and retry automatically
- Gmail API has a generous quota, so this is rare during normal use

## Next Steps

Now that your Gmail API connection is working, you can:

1. Test the connection anytime by running: `python src/gmail_client.py`
2. Use the `GmailClient` class in your own scripts
3. Build the newsletter analysis features

## Using the Gmail Client in Your Code

Here's a quick example:

```python
from src.gmail_client import GmailClient

# Initialize client (will use credentials from .env)
client = GmailClient()

# List emails from inbox
emails = client.list_emails(label_ids=['INBOX'], max_results=10)

# Get full email details
for msg in emails:
    email = client.get_email(msg['id'])
    headers = client.get_email_headers(email)
    body = client.extract_email_body(email)

    print(f"Subject: {headers.get('subject')}")
    print(f"Body: {body['plain'][:100]}...")
```

## API Quotas

Gmail API has the following quotas (as of 2024):

- **Per-user rate limit**: 250 quota units per user per second
- **Daily limit**: 1,000,000,000 quota units per day

Most operations (like reading emails) cost 5-10 quota units, so you're unlikely to hit these limits during normal development and testing.

## Support

If you encounter issues:

1. Check the [Gmail API documentation](https://developers.google.com/gmail/api)
2. Review the [Python quickstart guide](https://developers.google.com/gmail/api/quickstart/python)
3. Check your Google Cloud Console for any error messages

---

**You're all set! Ready to analyze those newsletters! 📧**
