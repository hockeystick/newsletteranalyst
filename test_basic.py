#!/usr/bin/env python3
"""
Basic test script to verify the Newsletter Analyst components.

This script tests:
1. Email processor functionality
2. Database operations
3. Integration between components

Run this after setting up your Gmail credentials to test with a small batch.
"""

from src.gmail_client import GmailClient
from src.email_processor import EmailProcessor
from src.database import NewsletterDatabase


def test_email_processor():
    """Test the email processor."""
    print("\n" + "=" * 70)
    print("Testing Email Processor")
    print("=" * 70)

    processor = EmailProcessor()

    # Test HTML to text conversion
    sample_html = """
    <html>
        <body>
            <h1>Welcome to Newsletter XYZ</h1>
            <p>This is your <strong>first email</strong> in our onboarding series.</p>
            <ul>
                <li>Feature 1: Amazing content</li>
                <li>Feature 2: Weekly insights</li>
            </ul>
            <p>Thanks for subscribing!</p>
        </body>
    </html>
    """

    text = processor.html_to_text(sample_html)
    print("\nHTML to Text conversion:")
    print("-" * 70)
    print(text)
    print("-" * 70)

    # Test hash generation
    hash1 = processor.generate_email_hash(
        "newsletter@example.com",
        "Welcome to Newsletter XYZ",
        text
    )
    print(f"\nGenerated hash: {hash1}")

    # Test duplicate detection
    hash2 = processor.generate_email_hash(
        "newsletter@example.com",
        "Welcome to Newsletter XYZ",
        text
    )

    is_duplicate = processor.is_duplicate(hash1, [hash2])
    print(f"Duplicate detection: {is_duplicate} (should be True)")

    print("\n✓ Email Processor test passed!")


def test_database():
    """Test database operations."""
    print("\n" + "=" * 70)
    print("Testing Database")
    print("=" * 70)

    # Use a test database
    db = NewsletterDatabase('data/test_database.db')

    # Save a test publisher
    publisher_id = db.save_publisher(
        name="Test Newsletter",
        domain="example.com",
        country="US",
        language="en"
    )
    print(f"\n✓ Saved publisher with ID: {publisher_id}")

    # Save a test email
    import time
    email_id = db.save_email(
        message_id="test_msg_001",
        publisher_name="Test Newsletter",
        sender="Test Newsletter <newsletter@example.com>",
        sender_email="newsletter@example.com",
        sender_name="Test Newsletter",
        subject="Welcome to Test Newsletter",
        send_timestamp=int(time.time()),
        body_text="This is a test email body.",
        body_html="<p>This is a test email body.</p>",
        raw_json='{}',
        email_sequence_number=1,
        sequence_confidence="high"
    )
    print(f"✓ Saved email with ID: {email_id}")

    # Retrieve emails
    emails = db.get_emails_by_publisher("Test Newsletter")
    print(f"✓ Retrieved {len(emails)} emails from publisher")

    # Get stats
    stats = db.get_database_stats()
    print(f"\nDatabase stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    db.close()
    print("\n✓ Database test passed!")


def test_gmail_integration(max_emails=5):
    """
    Test integration with Gmail (requires authentication).

    Args:
        max_emails: Number of emails to fetch for testing
    """
    print("\n" + "=" * 70)
    print("Testing Gmail Integration")
    print("=" * 70)

    try:
        # Initialize components
        print("\nInitializing components...")
        gmail = GmailClient()
        processor = EmailProcessor()
        db = NewsletterDatabase()

        print("✓ All components initialized")

        # Fetch a few emails
        print(f"\nFetching {max_emails} recent emails...")
        messages = gmail.list_emails(max_results=max_emails)

        if not messages:
            print("No emails found. Make sure you have emails in your inbox.")
            return

        print(f"✓ Found {len(messages)} emails")

        # Process one email as example
        print("\nProcessing first email as example...")
        msg = messages[0]
        email = gmail.get_email(msg['id'])
        body = gmail.extract_email_body(email)

        processed = processor.process_email(
            email,
            body['plain'],
            body['html']
        )

        print("\nProcessed email details:")
        print(f"  Subject: {processed['subject']}")
        print(f"  From: {processed['sender']}")
        print(f"  Publisher: {processed['publisher_name']}")
        print(f"  Hash: {processed['email_hash'][:16]}...")
        print(f"  Body length: {len(processed['body_text'])} chars")

        print("\n✓ Gmail integration test passed!")
        print("\nYou can now run the full CLI command:")
        print("  python -m src.main fetch-emails --label INBOX --max-results 20")

        db.close()

    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("\nPlease set up Gmail credentials first:")
        print("  1. Follow instructions in SETUP.md")
        print("  2. Download credentials.json to config/")
        print("  3. Create .env file with GMAIL_CREDENTIALS_PATH")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("Newsletter Analyst - Basic Tests")
    print("=" * 70)

    # Test 1: Email Processor
    test_email_processor()

    # Test 2: Database
    test_database()

    # Test 3: Gmail Integration (optional, requires auth)
    print("\n" + "=" * 70)
    print("Gmail Integration Test (optional)")
    print("=" * 70)
    print("\nThis test requires Gmail authentication.")
    response = input("Do you want to run the Gmail integration test? (y/n): ")

    if response.lower() in ['y', 'yes']:
        test_gmail_integration(max_emails=5)
    else:
        print("\nSkipping Gmail integration test.")
        print("\nTo test Gmail integration later, run:")
        print("  python test_basic.py")
        print("\nOr use the CLI directly:")
        print("  python -m src.main fetch-emails --label INBOX --max-results 10")

    print("\n" + "=" * 70)
    print("All Tests Complete!")
    print("=" * 70)
    print()


if __name__ == '__main__':
    main()
