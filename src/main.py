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
def list_publishers(db_path: str):
    """List all publishers in database."""
    try:
        db = NewsletterDatabase(db_path)
    except Exception as e:
        click.echo(f"Error opening database: {e}", err=True)
        sys.exit(1)

    pub_stats = db.get_publisher_stats()

    click.echo(f"\nFound {len(pub_stats)} publishers:\n")

    for i, stat in enumerate(pub_stats, 1):
        click.echo(
            f"{i:3}. {stat['publisher_name']:40} "
            f"| {stat['email_count']:3} emails "
            f"| First: {stat['first_email'][:10] if stat['first_email'] else 'N/A'} "
            f"| Last: {stat['last_email'][:10] if stat['last_email'] else 'N/A'}"
        )

    click.echo()
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


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()
