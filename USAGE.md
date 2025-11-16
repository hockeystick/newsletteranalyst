# Usage Guide - Newsletter Analyst

Quick guide to get started with Newsletter Analyst.

## Prerequisites

1. Complete Gmail API setup (see [SETUP.md](SETUP.md))
2. Install dependencies: `pip install -r requirements.txt`
3. Authenticate with Gmail: `python src/gmail_client.py`

## Quick Start - Testing with Small Batch

### Option 1: Run Basic Tests

Test all components without fetching real data:

```bash
python test_basic.py
```

This will:
- Test HTML-to-text conversion
- Test database operations
- Optionally test Gmail integration with 5 emails

### Option 2: Fetch a Small Batch (Recommended)

Start with 10-20 emails to test the system:

```bash
# Fetch 10 most recent emails from inbox
python -m src.main fetch-emails --label "INBOX" --max-results 10
```

This will:
1. Connect to Gmail
2. Fetch 10 emails
3. Process each email (extract metadata, convert HTML to text)
4. Detect email sequences
5. Save to SQLite database
6. Show summary statistics

### Option 3: Test with Specific Newsletter

If you have a specific newsletter label:

```bash
# Replace "Newsletter-Onboarding" with your label
python -m src.main fetch-emails --label "Newsletter-Onboarding" --max-results 20
```

Or search for a specific sender:

```bash
python -m src.main fetch-emails --query "from:newsletter@example.com" --max-results 15
```

## CLI Commands Reference

### 1. Fetch Emails

**Basic fetch:**
```bash
python -m src.main fetch-emails --max-results 20
```

**Fetch from specific label:**
```bash
python -m src.main fetch-emails --label "Newsletter-Onboarding" --max-results 50
```

**Fetch since a date:**
```bash
python -m src.main fetch-emails --since "2025-01-01" --max-results 100
```

**Fetch with complex query:**
```bash
python -m src.main fetch-emails --query "from:newsletter@example.com subject:welcome" --max-results 30
```

**Custom database location:**
```bash
python -m src.main fetch-emails --db-path "data/my_newsletters.db" --max-results 20
```

**Include duplicates (not recommended):**
```bash
python -m src.main fetch-emails --no-skip-duplicates --max-results 20
```

### 2. View Statistics

**Overall database stats:**
```bash
python -m src.main stats
```

Shows:
- Total emails and publishers
- Analyzed vs unanalyzed emails
- Top publishers by email count
- Sequence statistics

**List all publishers:**
```bash
python -m src.main list-publishers
```

Shows publishers with:
- Email counts
- First and last email dates

### 3. Search Emails

**Search by keyword:**
```bash
python -m src.main search --keyword "welcome"
```

**Search by publisher:**
```bash
python -m src.main search --publisher "Example Newsletter"
```

**Search by sequence number:**
```bash
# Find all first emails in sequences
python -m src.main search --sequence 1 --limit 50
```

**Combined search:**
```bash
python -m src.main search --publisher "Example Newsletter" --sequence 1
```

## Understanding the Output

### Fetch Command Output

```
======================================================================
Newsletter Analyst - Email Fetcher
======================================================================

Initializing...
✓ Connected to Gmail
✓ Database: data/newsletter_emails.db

Loaded 0 existing email hashes for deduplication
Fetching emails...
  Label: INBOX
  Query: (none)
  Max results: 10

Found 10 emails. Processing...

Processing emails: 100%|████████████████████| 10/10 [00:15<00:00,  1.50s/email]

Analyzing email sequences...
Saving 10 emails to database...

Saving to DB: 100%|████████████████████████| 10/10 [00:01<00:00,  8.23email/s]

======================================================================
SUMMARY
======================================================================
Emails fetched:        10
Duplicates skipped:    0
Emails processed:      10
Emails saved:          10
Errors:                0

Publishers:
  Example Newsletter: 3 emails
  Tech Weekly: 2 emails
  Daily Digest: 5 emails

Sequence distribution:
  Email #1: 2 emails
  Email #2: 1 emails

Database Statistics:
  Total emails:          10
  Total publishers:      3
  Analyzed:              0
  Unanalyzed:            10
  Date range:            2025-01-15 to 2025-01-20

✓ Done!
======================================================================
```

### What Gets Stored

For each email, the database stores:
- **Metadata**: sender, subject, date, labels
- **Content**: plain text and HTML versions
- **Analysis**: publisher info, sequence number, confidence level
- **Hash**: for deduplication
- **Raw JSON**: complete Gmail API response

### Sequence Detection

The system automatically detects if emails are part of an onboarding sequence:

- **Sequence #1**: Usually the welcome email
- **Sequence #2**: Typically sent 1-3 days after signup
- **Sequence #3**: Typically sent 3-7 days after signup

Confidence levels:
- **high**: Strong indicators (subject line patterns, timing)
- **medium**: Moderate indicators (timing patterns)
- **low**: Weak indicators (may not be part of sequence)

## Working with the Data

### Access the SQLite Database

```bash
# Using sqlite3 CLI
sqlite3 data/newsletter_emails.db

# Example queries
SELECT publisher_name, COUNT(*) FROM emails GROUP BY publisher_name;
SELECT subject, send_date FROM emails WHERE sequence_number = 1;
```

### Using Python API

```python
from src import NewsletterDatabase

db = NewsletterDatabase()

# Get all emails from a publisher
emails = db.get_emails_by_publisher("Example Newsletter")

# Get unanalyzed emails
unanalyzed = db.get_unanalyzed_emails(limit=50)

# Search
results = db.search_emails(keyword="welcome", sequence_number=1)

# Stats
stats = db.get_publisher_stats()
for stat in stats:
    print(f"{stat['publisher_name']}: {stat['email_count']} emails")

db.close()
```

## Typical Workflow

1. **Initial Setup** (one time):
   ```bash
   # Follow SETUP.md for Gmail API setup
   pip install -r requirements.txt
   python src/gmail_client.py  # First authentication
   ```

2. **Test with Small Batch**:
   ```bash
   python test_basic.py
   python -m src.main fetch-emails --max-results 10
   python -m src.main stats
   ```

3. **Fetch Specific Newsletters**:
   ```bash
   # Create Gmail label "Newsletter-Onboarding" first
   python -m src.main fetch-emails --label "Newsletter-Onboarding" --max-results 100
   ```

4. **Review and Analyze**:
   ```bash
   python -m src.main stats
   python -m src.main list-publishers
   python -m src.main search --sequence 1
   ```

5. **Iterate**:
   - Fetch more emails as needed
   - Run analysis on unanalyzed emails
   - Export data for further analysis

## Tips

- **Start small**: Test with 10-20 emails first
- **Use labels**: Create Gmail labels to organize newsletters
- **Check duplicates**: The system automatically skips duplicates based on content hash
- **Sequence detection**: Works best when you have multiple emails from same sender
- **Database**: SQLite file is in `data/` folder, can be backed up/shared
- **Rate limits**: Gmail API has generous limits, but the system handles rate limiting automatically

## Troubleshooting

### "No emails found"

- Check your Gmail labels
- Try broader query (remove `--label` or `--query`)
- Make sure you have emails matching the criteria

### "Database locked"

- Close any SQLite browser tools
- Only run one fetch command at a time

### "Rate limit exceeded"

- The system automatically retries with exponential backoff
- If persistent, reduce `--max-results`

### Sequence detection not working

- Sequence detection requires multiple emails from same sender
- Works best with at least 2-3 emails in sequence
- Check confidence levels in output

## Next Steps

After testing with a small batch:

1. **Fetch more emails**: Increase `--max-results` to 50, 100, or more
2. **Organize by date**: Use `--since` to fetch emails from specific time period
3. **Build analysis tools**: Use the database to analyze email patterns
4. **Export data**: Query the SQLite database for reports
5. **Automate**: Create scripts to regularly fetch new emails

## Questions?

- Check [SETUP.md](SETUP.md) for Gmail setup issues
- Check [README.md](README.md) for feature overview
- Review code comments in `src/` modules for detailed API docs
