#!/usr/bin/env python3
"""
Newsletter Analyst CLI

Command-line interface for fetching, processing, and analyzing newsletter emails.
"""

import sys
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

import click
from tqdm import tqdm

from .gmail_client import GmailClient
from .email_processor import EmailProcessor, analyze_email_sequence
from .database import NewsletterDatabase
from .publisher_manager import PublisherManager, print_publisher_table
from .llm_analyzer import EmailAnalyzer
from .batch_analyzer import BatchEmailAnalyzer
from .reporter import EmailReporter
from .pattern_detector import PatternDetector


@click.group()
@click.version_option(version='0.1.0')
def cli():
    """
    Newsletter Analyst - Analyze newsletter onboarding emails.

    This tool helps you fetch, process, and analyze newsletter emails
    from your Gmail account.
    """
    pass


@cli.command('fetch-emails')
@click.option(
    '--label',
    default='INBOX',
    help='Gmail label to filter by (e.g., "Newsletter-Onboarding", "INBOX")'
)
@click.option(
    '--since',
    default=None,
    help='Fetch emails since this date (format: YYYY-MM-DD)'
)
@click.option(
    '--query',
    default='',
    help='Additional Gmail search query (e.g., "from:newsletter@example.com")'
)
@click.option(
    '--max-results',
    default=100,
    type=int,
    help='Maximum number of emails to fetch'
)
@click.option(
    '--db-path',
    default='data/newsletter_emails.db',
    help='Path to SQLite database'
)
@click.option(
    '--skip-duplicates/--no-skip-duplicates',
    default=True,
    help='Skip duplicate emails based on hash'
)
def fetch_emails(
    label: str,
    since: Optional[str],
    query: str,
    max_results: int,
    db_path: str,
    skip_duplicates: bool
):
    """
    Fetch emails from Gmail and store in database.

    Examples:

        # Fetch from Newsletter-Onboarding label since Jan 1, 2025
        python -m src.main fetch-emails --label "Newsletter-Onboarding" --since "2025-01-01"

        # Fetch 50 emails from a specific sender
        python -m src.main fetch-emails --query "from:newsletter@example.com" --max-results 50

        # Fetch all inbox emails with custom label
        python -m src.main fetch-emails --label "INBOX" --max-results 200
    """
    click.echo("=" * 70)
    click.echo("Newsletter Analyst - Email Fetcher")
    click.echo("=" * 70)
    click.echo()

    # Build Gmail query
    gmail_query = query

    if since:
        try:
            # Validate date format
            datetime.strptime(since, '%Y-%m-%d')
            gmail_query += f' after:{since}'
        except ValueError:
            click.echo(f"Error: Invalid date format '{since}'. Use YYYY-MM-DD", err=True)
            sys.exit(1)

    # Initialize components
    click.echo("Initializing...")
    try:
        gmail_client = GmailClient()
        processor = EmailProcessor()
        db = NewsletterDatabase(db_path)
    except Exception as e:
        click.echo(f"Error initializing: {e}", err=True)
        sys.exit(1)

    click.echo(f"✓ Connected to Gmail")
    click.echo(f"✓ Database: {db_path}")
    click.echo()

    # Get existing hashes for deduplication
    existing_hashes = []
    if skip_duplicates:
        existing_hashes = db.get_all_email_hashes()
        click.echo(f"Loaded {len(existing_hashes)} existing email hashes for deduplication")

    # Fetch emails from Gmail
    click.echo(f"Fetching emails...")
    click.echo(f"  Label: {label}")
    click.echo(f"  Query: {gmail_query or '(none)'}")
    click.echo(f"  Max results: {max_results}")
    click.echo()

    try:
        # Determine label IDs
        label_ids = [label] if label else None

        messages = gmail_client.list_emails(
            label_ids=label_ids,
            query=gmail_query.strip(),
            max_results=max_results
        )
    except Exception as e:
        click.echo(f"Error fetching emails: {e}", err=True)
        db.close()
        sys.exit(1)

    if not messages:
        click.echo("No emails found matching the criteria.")
        db.close()
        return

    click.echo(f"Found {len(messages)} emails. Processing...\n")

    # Process emails with progress bar
    processed_emails = []
    skipped_duplicates = 0
    errors = 0

    with tqdm(total=len(messages), desc="Processing emails", unit="email") as pbar:
        for msg in messages:
            try:
                # Fetch full email
                email = gmail_client.get_email(msg['id'])

                # Extract body
                body = gmail_client.extract_email_body(email)

                # Process email
                processed = processor.process_email(
                    email,
                    body['plain'],
                    body['html'],
                    existing_hashes
                )

                # Skip if duplicate
                if skip_duplicates and processed['is_duplicate']:
                    skipped_duplicates += 1
                    pbar.update(1)
                    continue

                processed_emails.append(processed)

            except Exception as e:
                click.echo(f"\nError processing email {msg['id']}: {e}", err=True)
                errors += 1

            pbar.update(1)

    click.echo()

    if not processed_emails:
        click.echo("No new emails to process (all were duplicates).")
        click.echo(f"Skipped duplicates: {skipped_duplicates}")
        db.close()
        return

    # Analyze sequences
    click.echo("Analyzing email sequences...")
    processed_emails = analyze_email_sequence(processed_emails)

    # Save to database
    click.echo(f"Saving {len(processed_emails)} emails to database...")

    saved_count = 0
    with tqdm(total=len(processed_emails), desc="Saving to DB", unit="email") as pbar:
        for email_data in processed_emails:
            try:
                email_id = db.save_email(
                    message_id=email_data['message_id'],
                    thread_id=email_data.get('thread_id'),
                    publisher_name=email_data['publisher_name'],
                    sender=email_data['sender'],
                    sender_email=email_data.get('sender_email'),
                    sender_name=email_data.get('sender_name'),
                    subject=email_data['subject'],
                    send_timestamp=email_data.get('timestamp'),
                    body_text=email_data['body_text'],
                    body_html=email_data['body_html'],
                    email_hash=email_data.get('email_hash'),
                    labels=email_data.get('labels'),
                    snippet=email_data.get('snippet'),
                    email_sequence_number=email_data.get('sequence_number', 0),
                    sequence_confidence=email_data.get('sequence_confidence'),
                    raw_json=email_data['raw_json']
                )
                saved_count += 1
            except Exception as e:
                click.echo(f"\nError saving email: {e}", err=True)
                errors += 1

            pbar.update(1)

    # Display summary
    click.echo()
    click.echo("=" * 70)
    click.echo("SUMMARY")
    click.echo("=" * 70)
    click.echo(f"Emails fetched:        {len(messages)}")
    click.echo(f"Duplicates skipped:    {skipped_duplicates}")
    click.echo(f"Emails processed:      {len(processed_emails)}")
    click.echo(f"Emails saved:          {saved_count}")
    click.echo(f"Errors:                {errors}")
    click.echo()

    # Show publisher breakdown
    publishers = {}
    for email_data in processed_emails:
        pub = email_data['publisher_name']
        if pub not in publishers:
            publishers[pub] = 0
        publishers[pub] += 1

    click.echo("Publishers:")
    for pub, count in sorted(publishers.items(), key=lambda x: x[1], reverse=True):
        click.echo(f"  {pub}: {count} emails")
    click.echo()

    # Show sequence breakdown
    sequences = {}
    for email_data in processed_emails:
        seq = email_data.get('sequence_number', 0)
        if seq > 0:
            if seq not in sequences:
                sequences[seq] = 0
            sequences[seq] += 1

    if sequences:
        click.echo("Sequence distribution:")
        for seq_num, count in sorted(sequences.items()):
            click.echo(f"  Email #{seq_num}: {count} emails")
        click.echo()

    # Show overall database stats
    stats = db.get_database_stats()
    click.echo("Database Statistics:")
    click.echo(f"  Total emails:          {stats['total_emails']}")
    click.echo(f"  Total publishers:      {stats['total_publishers']}")
    click.echo(f"  Analyzed:              {stats['analyzed_emails']}")
    click.echo(f"  Unanalyzed:            {stats['unanalyzed_emails']}")
    click.echo(f"  Date range:            {stats['first_email_date']} to {stats['last_email_date']}")
    click.echo()

    click.echo("✓ Done!")
    click.echo("=" * 70)

    db.close()


@cli.command('stats')
@click.option(
    '--db-path',
    default='data/newsletter_emails.db',
    help='Path to SQLite database'
)
def show_stats(db_path: str):
    """Show database statistics."""
    click.echo("=" * 70)
    click.echo("Newsletter Database Statistics")
    click.echo("=" * 70)
    click.echo()

    try:
        db = NewsletterDatabase(db_path)
    except Exception as e:
        click.echo(f"Error opening database: {e}", err=True)
        sys.exit(1)

    # Overall stats
    stats = db.get_database_stats()
    click.echo("Overall Statistics:")
    for key, value in stats.items():
        click.echo(f"  {key.replace('_', ' ').title()}: {value}")
    click.echo()

    # Publisher stats
    click.echo("Top Publishers:")
    pub_stats = db.get_publisher_stats()
    for i, stat in enumerate(pub_stats[:10], 1):
        click.echo(
            f"  {i}. {stat['publisher_name']}: {stat['email_count']} emails "
            f"({stat['analyzed_count']} analyzed)"
        )
    click.echo()

    # Sequence stats
    click.echo("Sequence Statistics:")
    seq_stats = db.get_sequence_stats()

    if seq_stats:
        current_publisher = None
        for stat in seq_stats[:20]:  # Show top 20
            if stat['publisher_name'] != current_publisher:
                click.echo(f"\n  {stat['publisher_name']}:")
                current_publisher = stat['publisher_name']

            click.echo(
                f"    Email #{stat['email_sequence_number']}: "
                f"{stat['count']} emails "
                f"(confidence: {stat['sequence_confidence']})"
            )
    else:
        click.echo("  No sequence data available")

    click.echo()
    click.echo("=" * 70)

    db.close()


@cli.command('list-publishers')
@click.option(
    '--db-path',
    default='data/newsletter_emails.db',
    help='Path to SQLite database'
)
@click.option(
    '--limit',
    type=int,
    default=None,
    help='Maximum number of publishers to display'
)
def list_publishers_cmd(db_path: str, limit: Optional[int]):
    """List all publishers in database with detailed information."""
    try:
        db = NewsletterDatabase(db_path)
        manager = PublisherManager(db)
    except Exception as e:
        click.echo(f"Error opening database: {e}", err=True)
        sys.exit(1)

    publishers = manager.list_publishers()
    print_publisher_table(publishers, limit=limit)

    db.close()


@cli.command('add-publisher')
@click.option(
    '--db-path',
    default='data/newsletter_emails.db',
    help='Path to SQLite database'
)
@click.option('--name', help='Publisher name (skip interactive mode)')
@click.option('--domain', help='Email domain')
@click.option('--country', help='Country code (e.g., US, UK, CA)')
@click.option('--language', help='Language code (e.g., en, es, fr)')
@click.option('--website', help='Website URL')
@click.option('--business-model', help='Business model (free, freemium, paid, sponsored)')
@click.option('--signup-date', help='Signup date (YYYY-MM-DD)')
@click.option('--notes', help='Additional notes')
def add_publisher_cmd(
    db_path: str,
    name: Optional[str],
    domain: Optional[str],
    country: Optional[str],
    language: Optional[str],
    website: Optional[str],
    business_model: Optional[str],
    signup_date: Optional[str],
    notes: Optional[str]
):
    """
    Add a new publisher to the database.

    If no options provided, runs in interactive mode with prompts.

    Examples:

        # Interactive mode
        python -m src.main add-publisher

        # Command-line mode
        python -m src.main add-publisher --name "Tech Weekly" --country US --language en
    """
    try:
        db = NewsletterDatabase(db_path)
        manager = PublisherManager(db)
    except Exception as e:
        click.echo(f"Error opening database: {e}", err=True)
        sys.exit(1)

    if name:
        # Non-interactive mode with command-line options
        try:
            publisher_id = manager.add_publisher(
                name=name,
                domain=domain,
                country=country,
                language=language,
                website=website,
                business_model=business_model,
                signup_date=signup_date,
                notes=notes
            )
            click.echo(f"✓ Publisher '{name}' added successfully (ID: {publisher_id})")
        except Exception as e:
            click.echo(f"✗ Error adding publisher: {e}", err=True)
            sys.exit(1)
    else:
        # Interactive mode
        manager.add_publisher_interactive()

    db.close()


@cli.command('export-publishers')
@click.option(
    '--db-path',
    default='data/newsletter_emails.db',
    help='Path to SQLite database'
)
@click.option(
    '--output',
    default='output/publishers.csv',
    help='Output CSV file path'
)
@click.option(
    '--template/--no-template',
    default=True,
    help='Include signup tracking template fields'
)
def export_publishers_cmd(db_path: str, output: str, template: bool):
    """
    Export publishers to CSV file.

    Examples:

        # Export with tracking template fields (default)
        python -m src.main export-publishers --output publishers.csv

        # Export basic data only
        python -m src.main export-publishers --output publishers.csv --no-template
    """
    try:
        db = NewsletterDatabase(db_path)
        manager = PublisherManager(db)
    except Exception as e:
        click.echo(f"Error opening database: {e}", err=True)
        sys.exit(1)

    click.echo("Exporting publishers...")
    success = manager.export_publishers_csv(output, include_template_fields=template)

    if success:
        click.echo(f"\n✓ Publishers exported to {output}")
        click.echo("  You can open this file in Google Sheets or Excel")
    else:
        click.echo("\n✗ Export failed", err=True)
        sys.exit(1)

    db.close()


@cli.command('create-signup-template')
@click.option(
    '--output',
    default='output/signup_tracking_template.csv',
    help='Output CSV file path'
)
def create_signup_template_cmd(output: str):
    """
    Create an empty signup tracking template.

    This creates a Google Sheets-compatible CSV template for tracking
    newsletter signups during the collection phase.

    Examples:

        python -m src.main create-signup-template
        python -m src.main create-signup-template --output my_signups.csv
    """
    try:
        db = NewsletterDatabase()
        manager = PublisherManager(db)
    except Exception as e:
        click.echo(f"Error initializing: {e}", err=True)
        sys.exit(1)

    click.echo("Creating signup tracking template...")
    success = manager.generate_signup_template(output)

    if success:
        click.echo(f"\n✓ Template created successfully!")
        click.echo(f"  Open {output} in Google Sheets or Excel to start tracking signups")
    else:
        click.echo("\n✗ Template creation failed", err=True)
        sys.exit(1)

    db.close()


@cli.command('search')
@click.option('--keyword', help='Search in subject and body')
@click.option('--publisher', help='Filter by publisher name')
@click.option('--sequence', type=int, help='Filter by sequence number')
@click.option('--limit', default=20, type=int, help='Maximum results to show')
@click.option(
    '--db-path',
    default='data/newsletter_emails.db',
    help='Path to SQLite database'
)
def search_emails(
    keyword: Optional[str],
    publisher: Optional[str],
    sequence: Optional[int],
    limit: int,
    db_path: str
):
    """Search emails in database."""
    try:
        db = NewsletterDatabase(db_path)
    except Exception as e:
        click.echo(f"Error opening database: {e}", err=True)
        sys.exit(1)

    results = db.search_emails(
        keyword=keyword,
        publisher=publisher,
        sequence_number=sequence,
        limit=limit
    )

    click.echo(f"\nFound {len(results)} results:\n")

    for i, email in enumerate(results, 1):
        click.echo(f"{i}. [{email['publisher_name']}] {email['subject']}")
        click.echo(f"   From: {email['sender']}")
        click.echo(f"   Date: {email['send_date'][:19] if email['send_date'] else 'N/A'}")
        if email['email_sequence_number'] > 0:
            click.echo(f"   Sequence: #{email['email_sequence_number']} ({email['sequence_confidence']})")
        click.echo()

    db.close()


@cli.command('analyze-emails')
@click.option(
    '--db-path',
    default='data/newsletter_emails.db',
    help='Path to SQLite database'
)
@click.option(
    '--batch-size',
    type=int,
    default=None,
    help='Maximum number of emails to analyze (default: all unanalyzed)'
)
@click.option(
    '--delay',
    type=float,
    default=1.0,
    help='Delay between API requests in seconds (default: 1.0)'
)
@click.option(
    '--publisher',
    help='Only analyze emails from specific publisher'
)
@click.option(
    '--sequence',
    type=int,
    help='Only analyze emails with specific sequence number'
)
@click.option(
    '--reanalyze',
    is_flag=True,
    help='Re-analyze already analyzed emails'
)
def analyze_emails_cmd(
    db_path: str,
    batch_size: Optional[int],
    delay: float,
    publisher: Optional[str],
    sequence: Optional[int],
    reanalyze: bool
):
    """
    Analyze emails using Claude AI.

    Uses Anthropic's Claude API to extract structured insights from newsletter
    onboarding emails. Analyzes purpose, value propositions, CTAs, tone, and
    effectiveness.

    Examples:

        # Analyze first 10 unanalyzed emails
        python -m src.main analyze-emails --batch-size 10

        # Analyze with custom delay (for rate limiting)
        python -m src.main analyze-emails --batch-size 5 --delay 2.0

        # Analyze only first emails in sequences
        python -m src.main analyze-emails --sequence 1 --batch-size 20

        # Analyze specific publisher
        python -m src.main analyze-emails --publisher "Tech Weekly" --batch-size 10
    """
    click.echo("=" * 70)
    click.echo("Newsletter Email Analysis with Claude AI")
    click.echo("=" * 70)
    click.echo()

    # Initialize components
    try:
        db = NewsletterDatabase(db_path)
        analyzer = EmailAnalyzer()
        batch_analyzer = BatchEmailAnalyzer(db, analyzer, delay_seconds=delay)
    except ValueError as e:
        click.echo(f"✗ Error: {e}", err=True)
        click.echo("\nPlease set ANTHROPIC_API_KEY in your .env file", err=True)
        click.echo("Get your API key from: https://console.anthropic.com/", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Error initializing: {e}", err=True)
        sys.exit(1)

    # Run batch analysis
    try:
        summary = batch_analyzer.analyze_batch(
            batch_size=batch_size,
            skip_analyzed=not reanalyze,
            publisher_filter=publisher,
            sequence_filter=sequence
        )

        # Print summary
        batch_analyzer.print_summary(summary)

        # Show sample results if any were processed
        if summary['success'] > 0:
            click.echo("Sample Analysis Results:")
            click.echo("-" * 70)

            analyzed = db.get_analyzed_emails(limit=3)
            for i, email in enumerate(analyzed[:3], 1):
                click.echo(f"\n{i}. {email.get('subject', 'N/A')}")
                click.echo(f"   Publisher: {email.get('publisher_name', 'N/A')}")
                click.echo(f"   Tone: {email.get('tone', 'N/A')}")
                click.echo(f"   Effectiveness Score: {email.get('effectiveness_score', 'N/A')}/10")

            click.echo("\n" + "-" * 70)
            click.echo("\nView full analysis results:")
            click.echo(f"  Database: {db_path}")
            click.echo(f"  Table: email_analysis")

    except Exception as e:
        click.echo(f"\n✗ Error during analysis: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

    click.echo("\n✓ Analysis complete!")


@cli.command('export-analysis')
@click.option(
    '--db-path',
    default='data/newsletter_emails.db',
    help='Path to SQLite database'
)
@click.option(
    '--output',
    default='output/analysis_results.csv',
    help='Output CSV file path'
)
def export_analysis_cmd(db_path: str, output: str):
    """
    Export all analyzed emails to CSV with analysis results.

    Creates a comprehensive CSV file with all email data and AI analysis results
    including effectiveness scores, CTAs, value propositions, and more.

    Examples:

        python -m src.main export-analysis
        python -m src.main export-analysis --output my_results.csv
    """
    click.echo("Exporting analyzed emails to CSV...")

    try:
        db = NewsletterDatabase(db_path)
        reporter = EmailReporter(db)

        success = reporter.export_analysis_to_csv(output)

        if success:
            click.echo(f"\n✓ Export complete!")
            click.echo(f"  File: {output}")
            click.echo("\nThis CSV can be opened in:")
            click.echo("  - Google Sheets")
            click.echo("  - Microsoft Excel")
            click.echo("  - Python/Pandas for further analysis")
        else:
            click.echo("\n✗ Export failed", err=True)
            sys.exit(1)

        db.close()

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command('generate-report')
@click.option(
    '--db-path',
    default='data/newsletter_emails.db',
    help='Path to SQLite database'
)
@click.option(
    '--output',
    default='output/analysis_report.txt',
    help='Output text file path'
)
def generate_report_cmd(db_path: str, output: str):
    """
    Generate a comprehensive analysis report.

    Creates a text report with statistics, patterns, and insights from
    analyzed newsletter emails. Includes breakdowns by country, business model,
    and common patterns.

    Examples:

        python -m src.main generate-report
        python -m src.main generate-report --output my_report.txt
    """
    click.echo("Generating analysis report...")

    try:
        db = NewsletterDatabase(db_path)
        reporter = EmailReporter(db)

        success = reporter.generate_text_report(output)

        if success:
            click.echo(f"\n✓ Report generated!")
            click.echo(f"  File: {output}")
            click.echo("\nReport includes:")
            click.echo("  - Database statistics")
            click.echo("  - Effectiveness scores")
            click.echo("  - Country analysis")
            click.echo("  - Business model analysis")
            click.echo("  - Common patterns")
        else:
            click.echo("\n✗ Report generation failed", err=True)
            sys.exit(1)

        db.close()

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command('export-by-country')
@click.option(
    '--db-path',
    default='data/newsletter_emails.db',
    help='Path to SQLite database'
)
@click.option(
    '--country',
    required=True,
    help='Country code to filter by (e.g., "US", "UK", "CZ")'
)
@click.option(
    '--output',
    default=None,
    help='Output CSV file path (default: output/{country}_analysis.csv)'
)
def export_by_country_cmd(db_path: str, country: str, output: Optional[str]):
    """
    Export analyzed emails for a specific country.

    Filters emails by country and exports analysis results to CSV.
    Useful for comparing onboarding approaches by region.

    Examples:

        python -m src.main export-by-country --country "US"
        python -m src.main export-by-country --country "CZ" --output czech_newsletters.csv
    """
    # Default output path
    if not output:
        output = f"output/{country}_analysis.csv"

    click.echo(f"Exporting emails for country: {country}...")

    try:
        db = NewsletterDatabase(db_path)
        reporter = EmailReporter(db)

        success = reporter.export_by_country(country, output)

        if success:
            click.echo(f"\n✓ Export complete!")
            click.echo(f"  File: {output}")
        else:
            click.echo(f"\n⚠ No analyzed emails found for country: {country}", err=True)

        db.close()

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command('find-patterns')
@click.option(
    '--db-path',
    default='data/newsletter_emails.db',
    help='Path to SQLite database'
)
@click.option(
    '--show-phrases/--no-phrases',
    default=True,
    help='Show common phrases'
)
@click.option(
    '--show-ctas/--no-ctas',
    default=True,
    help='Show grouped CTAs'
)
@click.option(
    '--show-outliers/--no-outliers',
    default=True,
    help='Show outlier emails'
)
def find_patterns_cmd(
    db_path: str,
    show_phrases: bool,
    show_ctas: bool,
    show_outliers: bool
):
    """
    Detect patterns and outliers in analyzed emails.

    Analyzes common phrases, groups similar CTAs, and identifies
    unusual or standout emails.

    Examples:

        python -m src.main find-patterns
        python -m src.main find-patterns --no-phrases
        python -m src.main find-patterns --show-ctas --no-outliers
    """
    click.echo("=" * 70)
    click.echo("Pattern Detection")
    click.echo("=" * 70)
    click.echo()

    try:
        db = NewsletterDatabase(db_path)
        detector = PatternDetector(db)

        # Common phrases
        if show_phrases:
            click.echo("Finding common phrases...")
            phrases = detector.find_common_phrases(top_n=10)

            click.echo("\nMost Common 2-Word Phrases:")
            for phrase, count in phrases.get('2_word_phrases', [])[:15]:
                click.echo(f"  {count:3}x  {phrase}")

            click.echo("\nMost Common 3-Word Phrases:")
            for phrase, count in phrases.get('3_word_phrases', [])[:10]:
                click.echo(f"  {count:3}x  {phrase}")

            click.echo("\nMost Common Welcome Phrases:")
            for phrase, count in phrases.get('welcome_phrases', [])[:10]:
                click.echo(f"  {count:2}x  {phrase[:70]}...")

            click.echo()

        # Grouped CTAs
        if show_ctas:
            click.echo("Grouping similar CTAs...")
            cta_groups = detector.group_similar_ctas()

            click.echo("\nCTA Categories:")
            for group, data in sorted(cta_groups.items(), key=lambda x: x[1]['count'], reverse=True)[:10]:
                click.echo(f"\n{group.upper().replace('_', ' ')} ({data['count']} total, {data['unique']} unique):")
                for cta, count in data['most_common'][:5]:
                    click.echo(f"  {count:2}x  {cta[:60]}")

            click.echo()

        # Outliers
        if show_outliers:
            click.echo("Identifying outliers...")
            outliers = detector.identify_outliers()

            if outliers.get('very_high_score'):
                click.echo("\nHigh-Performing Emails (Score ≥9):")
                for email in outliers['very_high_score'][:5]:
                    click.echo(f"  {email['score']}/10 - {email['publisher']}: {email['subject'][:50]}")

            if outliers.get('very_low_score'):
                click.echo("\nLow-Performing Emails (Score ≤4):")
                for email in outliers['very_low_score'][:5]:
                    click.echo(f"  {email['score']}/10 - {email['publisher']}: {email['subject'][:50]}")

            if outliers.get('unusually_long'):
                click.echo("\nUnusually Long Emails:")
                for email in outliers['unusually_long'][:5]:
                    click.echo(f"  {email['length']:,} chars ({email['avg_length']:,} avg) - {email['publisher']}")

            if outliers.get('many_ctas'):
                click.echo("\nEmails with Many CTAs:")
                for email in outliers['many_ctas'][:5]:
                    click.echo(f"  {email['cta_count']} CTAs ({email['avg_ctas']:.1f} avg) - {email['publisher']}")

        click.echo("\n" + "=" * 70)
        db.close()

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()
