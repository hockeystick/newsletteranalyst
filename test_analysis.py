#!/usr/bin/env python3
"""
Test script for email analysis with Claude AI.

This script tests the LLM analysis functionality with a small batch of emails
to verify output quality before running larger batches.
"""

import sys
import json
from pathlib import Path

from src import NewsletterDatabase, EmailAnalyzer, BatchEmailAnalyzer


def test_single_email_analysis():
    """Test analyzing a single sample email."""
    print("\n" + "=" * 70)
    print("Test 1: Single Email Analysis")
    print("=" * 70 + "\n")

    sample_email = {
        'subject': 'Welcome to Tech Weekly!',
        'body_text': """Hi there!

Welcome to Tech Weekly - your source for the latest in technology news and insights.

Here's what you can expect:
- Weekly roundup of tech news every Monday
- Deep dives into emerging technologies
- Exclusive interviews with industry leaders
- Special subscriber-only content

Get started by checking out our latest issue: https://techweekly.com/latest

We're thrilled to have you as part of our community of 50,000+ tech enthusiasts.

Questions? Just reply to this email - we read every message.

Best,
The Tech Weekly Team

P.S. Make sure to whitelist our email to never miss an issue!
""",
        'sender': 'Tech Weekly <hello@techweekly.com>'
    }

    try:
        analyzer = EmailAnalyzer()

        print("Analyzing sample email...")
        print(f"Subject: {sample_email['subject']}")
        print(f"Sender: {sample_email['sender']}\n")

        result = analyzer.analyze_email(
            subject=sample_email['subject'],
            body_text=sample_email['body_text'],
            sender=sample_email['sender']
        )

        print("Analysis Result:")
        print("-" * 70)
        print(json.dumps(result, indent=2))
        print("-" * 70)

        # Print usage stats
        analyzer.print_usage_stats()

        print("✓ Single email analysis test passed!\n")
        return True

    except ValueError as e:
        print(f"✗ Error: {e}")
        print("\nPlease set ANTHROPIC_API_KEY in your .env file")
        print("Get your API key from: https://console.anthropic.com/\n")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_emails(batch_size: int = 3):
    """Test analyzing emails from the database."""
    print("\n" + "=" * 70)
    print(f"Test 2: Database Email Analysis ({batch_size} emails)")
    print("=" * 70 + "\n")

    try:
        db = NewsletterDatabase()

        # Check if we have emails
        stats = db.get_database_stats()
        print(f"Database has {stats['total_emails']} emails")
        print(f"Unanalyzed: {stats['unanalyzed_emails']}")
        print(f"Already analyzed: {stats['analyzed_emails']}\n")

        if stats['total_emails'] == 0:
            print("No emails in database. Please fetch emails first using:")
            print("  python -m src.main fetch-emails --max-results 10\n")
            db.close()
            return False

        # Initialize analyzer
        analyzer = EmailAnalyzer()
        batch_analyzer = BatchEmailAnalyzer(db, analyzer, delay_seconds=1.5)

        # Analyze batch
        print(f"Analyzing up to {batch_size} emails...\n")

        summary = batch_analyzer.analyze_batch(
            batch_size=batch_size,
            skip_analyzed=True
        )

        # Print summary
        batch_analyzer.print_summary(summary)

        # Show sample results
        if summary['success'] > 0:
            print("\nSample Analysis Results:")
            print("-" * 70)

            analyzed = db.get_analyzed_emails(limit=min(3, summary['success']))
            for i, email in enumerate(analyzed, 1):
                print(f"\n{i}. {email.get('subject', 'N/A')[:60]}")
                print(f"   Publisher: {email.get('publisher_name', 'N/A')}")
                print(f"   Tone: {email.get('tone', 'N/A')}")
                print(f"   Effectiveness: {email.get('effectiveness_score', 'N/A')}/10")

                # Show value propositions
                try:
                    vps = json.loads(email.get('value_propositions', '[]'))
                    if vps:
                        print(f"   Value Props: {', '.join(vps[:2])}")
                except:
                    pass

            print()

        db.close()
        print("\n✓ Database email analysis test passed!\n")
        return True

    except ValueError as e:
        print(f"✗ Error: {e}")
        print("\nPlease set ANTHROPIC_API_KEY in your .env file")
        print("Get your API key from: https://console.anthropic.com/\n")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("Email Analysis Test Suite")
    print("=" * 70)

    # Check if .env exists
    env_path = Path('.env')
    if not env_path.exists():
        print("\n⚠ Warning: .env file not found")
        print("Please create .env from .env.example and set ANTHROPIC_API_KEY\n")
        sys.exit(1)

    print("\nThis will test the email analysis functionality using Claude AI.")
    print("Estimated cost: < $0.02 USD for test emails\n")

    response = input("Continue with tests? (y/n): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Tests cancelled.")
        sys.exit(0)

    # Test 1: Single email
    test1_passed = test_single_email_analysis()

    if not test1_passed:
        print("Test 1 failed. Please fix the issue before proceeding.")
        sys.exit(1)

    # Test 2: Database emails (ask user)
    print("\n" + "=" * 70)
    print("Test 2 will analyze 3-5 emails from your database.")
    response = input("Run Test 2? (y/n): ").strip().lower()

    if response in ['y', 'yes']:
        test2_passed = test_database_emails(batch_size=5)

        if not test2_passed:
            print("\nTest 2 encountered issues, but this may be expected if you haven't")
            print("fetched emails yet or don't have ANTHROPIC_API_KEY configured.\n")
    else:
        print("\nSkipping Test 2.")

    # Summary
    print("\n" + "=" * 70)
    print("Test Suite Complete!")
    print("=" * 70)
    print("\nIf tests passed, you're ready to analyze emails:")
    print("  python -m src.main analyze-emails --batch-size 10")
    print()


if __name__ == '__main__':
    main()
