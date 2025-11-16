# Publisher Tracking Guide

This guide explains how to manage newsletter publishers and track your signup activity.

## Overview

The Publisher Tracking system helps you:
- Track which newsletters you've signed up for
- Store publisher metadata (country, language, business model)
- Monitor signup dates and confirmation status
- Export data to Google Sheets for collaboration
- Keep notes about each publisher

## Quick Start

### 1. Create a Signup Tracking Template

Generate a Google Sheets-compatible CSV template:

```bash
python -m src.main create-signup-template
```

This creates `output/signup_tracking_template.csv` with these columns:
- Publisher
- Country
- Language
- Website
- Business Model
- Signup Date
- Signup URL
- Confirmation Received
- Onboarding Emails Count
- First Email Date
- Last Email Date
- Notes

You can:
- Open this in Google Sheets for online tracking
- Open in Excel for offline tracking
- Share with team members
- Use as a checklist during signup phase

### 2. Add Publishers to Database

**Interactive mode** (recommended for manual entry):

```bash
python -m src.main add-publisher
```

You'll be prompted for:
- Publisher name (required)
- Email domain (optional)
- Country (optional, e.g., US, UK, CA)
- Language (optional, e.g., en, es, fr)
- Website URL (optional)
- Business model (optional: free, freemium, paid, sponsored, other)
- Signup date (optional, defaults to today)
- Notes (optional)

**Command-line mode** (for scripting):

```bash
python -m src.main add-publisher \
  --name "Tech Weekly" \
  --country "US" \
  --language "en" \
  --website "https://techweekly.com" \
  --business-model "freemium" \
  --signup-date "2025-01-15" \
  --notes "Found via Twitter"
```

### 3. List Publishers

View all publishers with statistics:

```bash
python -m src.main list-publishers
```

Output shows:
- Publisher name
- Country and language
- Business model
- Number of emails received
- Signup date

Limit results:
```bash
python -m src.main list-publishers --limit 10
```

### 4. Export Publishers

Export to CSV for analysis or sharing:

```bash
# Export with signup tracking fields (default)
python -m src.main export-publishers --output publishers.csv

# Export basic data only
python -m src.main export-publishers --output publishers.csv --no-template
```

The exported CSV includes:
- All publisher metadata
- Email counts
- First and last email dates
- Template fields for manual tracking

## Workflow for Signup Collection Phase

### Step 1: Create Template

```bash
python -m src.main create-signup-template --output my_signups.csv
```

### Step 2: Track Signups in Google Sheets

1. Upload `my_signups.csv` to Google Sheets
2. As you sign up for newsletters, add rows with:
   - Publisher name
   - Country, language, website
   - Signup date and URL
   - Initial notes

### Step 3: Add to Database

After signing up, add publisher to database:

```bash
python -m src.main add-publisher
```

Enter the information you collected during signup.

### Step 4: Fetch Emails

After a few days, fetch emails to verify:

```bash
python -m src.main fetch-emails --label "INBOX" --max-results 50
```

The system will:
- Match emails to publishers by domain/name
- Count onboarding emails
- Detect email sequences

### Step 5: Export and Update

Export updated data:

```bash
python -m src.main export-publishers --output publishers_updated.csv
```

Open in Google Sheets to see:
- Which publishers sent confirmation emails
- How many onboarding emails each sent
- Date of first and last email

## Field Descriptions

### Publisher Metadata

- **Publisher**: Newsletter name (required)
- **Country**: 2-letter country code (US, UK, CA, etc.)
- **Language**: 2-letter language code (en, es, fr, etc.)
- **Website**: Publisher's main website URL
- **Business Model**:
  - `free`: Completely free, no paid tier
  - `freemium`: Free tier + premium option
  - `paid`: Paid subscription only
  - `sponsored`: Ad-supported/sponsored content
  - `other`: Other models

### Tracking Fields

- **Signup Date**: When you signed up (YYYY-MM-DD)
- **Signup URL**: The specific signup page you used
- **Confirmation Received**: Did you get a confirmation email? (Yes/No)
- **Onboarding Emails Count**: Number of onboarding emails received
- **First Email Date**: Date of first email
- **Last Email Date**: Date of most recent email
- **Notes**: Any additional information

## Tips

### During Signup Phase

1. **Keep a spreadsheet handy**: Open the tracking template in Google Sheets
2. **Fill in immediately**: Add each publisher right after signup
3. **Save signup URLs**: Record the exact URL you used to subscribe
4. **Note the experience**: Add notes about signup process, confirmation, etc.
5. **Track expected emails**: Some newsletters tell you what to expect

### After Collection

1. **Regular exports**: Export weekly to track progress
2. **Update confirmation status**: Mark which publishers actually sent emails
3. **Note missing publishers**: Track which didn't send onboarding emails
4. **Compare business models**: See if model affects onboarding quality

### Data Quality

1. **Consistent naming**: Use the exact publisher name
2. **Standard codes**: Use standard country/language codes
3. **Complete URLs**: Include https:// in website URLs
4. **Date format**: Always use YYYY-MM-DD for dates

## Examples

### Example 1: Track 50 Newsletter Signups

```bash
# Day 1: Create template
python -m src.main create-signup-template --output my_50_newsletters.csv

# Days 1-7: Sign up for newsletters, update CSV in Google Sheets

# Day 8: Add all publishers to database (one by one)
python -m src.main add-publisher
# ... repeat 50 times ...

# Day 15: Fetch all emails (after giving time for onboarding series)
python -m src.main fetch-emails --since "2025-01-01" --max-results 500

# Day 15: Export updated data
python -m src.main export-publishers --output results.csv

# Open results.csv in Google Sheets to analyze
```

### Example 2: Track by Country

```bash
# Add publishers with country tags
python -m src.main add-publisher --name "US Newsletter 1" --country "US"
python -m src.main add-publisher --name "UK Newsletter 1" --country "UK"

# Export and filter in Google Sheets by country column
python -m src.main export-publishers --output by_country.csv
```

### Example 3: Track by Business Model

```bash
# Add with business model tags
python -m src.main add-publisher \
  --name "Free Daily" \
  --business-model "free"

python -m src.main add-publisher \
  --name "Premium Weekly" \
  --business-model "paid"

# Export and analyze onboarding by business model
python -m src.main export-publishers --output by_model.csv
```

## Bulk Import (Advanced)

If you already have a CSV with publishers, you can import using Python:

```python
import csv
from src import NewsletterDatabase, PublisherManager

db = NewsletterDatabase()
manager = PublisherManager(db)

with open('my_publishers.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        manager.add_publisher(
            name=row['Publisher'],
            country=row.get('Country'),
            language=row.get('Language'),
            website=row.get('Website'),
            business_model=row.get('Business Model'),
            signup_date=row.get('Signup Date'),
            notes=row.get('Notes')
        )
        print(f"Added: {row['Publisher']}")

db.close()
```

## Integration with Email Fetching

The publisher tracking integrates with email fetching:

1. **Automatic matching**: Emails are matched to publishers by sender domain
2. **Email counts**: The system counts emails from each publisher
3. **Sequence detection**: Identifies 1st, 2nd, 3rd onboarding emails
4. **Export includes stats**: Exported CSV shows email counts and dates

This means:
- Add publishers BEFORE fetching emails for better tracking
- Publishers without metadata still get tracked from emails
- You can retroactively add metadata to existing email publishers

## Common Questions

**Q: Do I need to add publishers before fetching emails?**
A: No. The system creates publisher entries from emails automatically. But adding publishers manually lets you track metadata (country, business model, etc.).

**Q: Can I edit publisher information later?**
A: Yes. Run `add-publisher` with the same name to update information.

**Q: What if I have publishers without any emails?**
A: They'll still appear in lists and exports. This is useful for tracking signups that never sent confirmation emails.

**Q: Can I track publishers I haven't signed up for yet?**
A: Yes! Add them to your tracking template with future signup dates as a TODO list.

**Q: How do I share tracking with my team?**
A: Export to CSV and upload to Google Sheets. Team members can view/edit and you can re-import later.

## Next Steps

After setting up publisher tracking:

1. Sign up for newsletters systematically
2. Track signups in Google Sheets template
3. Add publishers to database
4. Fetch emails after a few days
5. Export and analyze onboarding patterns
6. Identify best and worst onboarding sequences

See [USAGE.md](USAGE.md) for email fetching and analysis workflows.
