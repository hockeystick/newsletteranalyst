"""
Batch Email Analysis Module

This module handles batch processing of newsletter emails using the LLM analyzer.
It includes resume capability, progress tracking, and database integration.
"""

import time
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from .llm_analyzer import EmailAnalyzer
from .database import NewsletterDatabase


class BatchEmailAnalyzer:
    """Batch process email analysis with resume capability."""

    def __init__(
        self,
        db: NewsletterDatabase,
        analyzer: EmailAnalyzer,
        delay_seconds: float = 1.0
    ):
        """
        Initialize batch analyzer.

        Args:
            db: NewsletterDatabase instance
            analyzer: EmailAnalyzer instance
            delay_seconds: Delay between API requests (default: 1.0)
        """
        self.db = db
        self.analyzer = analyzer
        self.delay_seconds = delay_seconds

        # Statistics
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
        self.skipped_count = 0

    def analyze_batch(
        self,
        batch_size: Optional[int] = None,
        skip_analyzed: bool = True,
        publisher_filter: Optional[str] = None,
        sequence_filter: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze a batch of unanalyzed emails.

        Args:
            batch_size: Maximum number of emails to analyze (None = all)
            skip_analyzed: Skip emails that are already analyzed
            publisher_filter: Only analyze emails from this publisher
            sequence_filter: Only analyze emails with this sequence number

        Returns:
            Dictionary with batch analysis results
        """
        print("\n" + "=" * 70)
        print("Batch Email Analysis")
        print("=" * 70 + "\n")

        # Get unanalyzed emails
        if skip_analyzed:
            emails_to_analyze = self.db.get_unanalyzed_emails(limit=batch_size)
        else:
            # Get all emails
            cursor = self.db.conn.cursor()
            query = "SELECT * FROM emails ORDER BY send_timestamp ASC"
            if batch_size:
                query += f" LIMIT {batch_size}"
            cursor.execute(query)
            emails_to_analyze = [dict(row) for row in cursor.fetchall()]

        # Apply filters
        if publisher_filter:
            emails_to_analyze = [
                e for e in emails_to_analyze
                if e.get('publisher_name') == publisher_filter
            ]

        if sequence_filter is not None:
            emails_to_analyze = [
                e for e in emails_to_analyze
                if e.get('email_sequence_number') == sequence_filter
            ]

        if not emails_to_analyze:
            print("No emails to analyze.")
            return self._get_summary()

        print(f"Found {len(emails_to_analyze)} emails to analyze")
        print(f"Delay between requests: {self.delay_seconds}s")
        print(f"Estimated time: ~{len(emails_to_analyze) * self.delay_seconds / 60:.1f} minutes\n")

        # Check for already analyzed (if not skipping)
        if not skip_analyzed:
            analyzed_ids = set()
            for email in emails_to_analyze:
                if self.db.get_email_analysis(email['id']):
                    analyzed_ids.add(email['id'])

            if analyzed_ids:
                print(f"Note: {len(analyzed_ids)} emails already analyzed (will be re-analyzed)\n")

        # Process emails with progress bar
        with tqdm(total=len(emails_to_analyze), desc="Analyzing emails", unit="email") as pbar:
            for email in emails_to_analyze:
                try:
                    # Check if already analyzed (resume capability)
                    if skip_analyzed and self.db.get_email_analysis(email['id']):
                        self.skipped_count += 1
                        pbar.set_postfix({'skipped': self.skipped_count})
                        pbar.update(1)
                        continue

                    # Analyze email
                    analysis = self.analyzer.analyze_email(
                        subject=email.get('subject', ''),
                        body_text=email.get('body_text', ''),
                        sender=email.get('sender', '')
                    )

                    # Save to database
                    self.db.save_email_analysis(email['id'], analysis)

                    self.success_count += 1
                    self.processed_count += 1

                    pbar.set_postfix({
                        'success': self.success_count,
                        'errors': self.error_count
                    })

                except Exception as e:
                    print(f"\n✗ Error analyzing email {email['id']}: {e}")
                    self.error_count += 1
                    self.processed_count += 1

                    pbar.set_postfix({
                        'success': self.success_count,
                        'errors': self.error_count
                    })

                pbar.update(1)

        # Get final summary
        return self._get_summary()

    def _get_summary(self) -> Dict[str, Any]:
        """Get summary of batch analysis."""
        usage_stats = self.analyzer.get_usage_stats()
        analysis_stats = self.db.get_analysis_stats()

        return {
            'processed': self.processed_count,
            'success': self.success_count,
            'errors': self.error_count,
            'skipped': self.skipped_count,
            'usage': usage_stats,
            'database': analysis_stats
        }

    def print_summary(self, summary: Dict[str, Any]):
        """Print batch analysis summary."""
        print("\n" + "=" * 70)
        print("Batch Analysis Summary")
        print("=" * 70)

        print(f"\nProcessing Results:")
        print(f"  Processed: {summary['processed']}")
        print(f"  Success: {summary['success']}")
        print(f"  Errors: {summary['errors']}")
        print(f"  Skipped: {summary['skipped']}")

        print(f"\nAPI Usage:")
        usage = summary['usage']
        print(f"  Total Requests: {usage['total_requests']}")
        print(f"  Total Tokens: {usage['total_tokens']:,}")
        print(f"  Input Tokens: {usage['total_input_tokens']:,}")
        print(f"  Output Tokens: {usage['total_output_tokens']:,}")
        print(f"  Estimated Cost: ${usage['estimated_cost_usd']:.4f} USD")

        print(f"\nDatabase Statistics:")
        db_stats = summary['database']
        print(f"  Total Analyzed: {db_stats['total_analyzed']}")
        if db_stats['average_effectiveness_score']:
            print(f"  Average Effectiveness Score: {db_stats['average_effectiveness_score']}/10")

        if db_stats['score_distribution']:
            print(f"\n  Score Distribution:")
            for item in db_stats['score_distribution']:
                score = item['effectiveness_score']
                count = item['count']
                print(f"    {score}/10: {count} emails")

        print("\n" + "=" * 70 + "\n")


def analyze_unanalyzed_emails(
    db_path: str = 'data/newsletter_emails.db',
    batch_size: Optional[int] = None,
    delay_seconds: float = 1.0,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to analyze unanalyzed emails.

    Args:
        db_path: Path to database
        batch_size: Maximum number to analyze
        delay_seconds: Delay between API calls
        api_key: Anthropic API key

    Returns:
        Summary dictionary
    """
    db = NewsletterDatabase(db_path)
    analyzer = EmailAnalyzer(api_key=api_key)

    batch_analyzer = BatchEmailAnalyzer(
        db=db,
        analyzer=analyzer,
        delay_seconds=delay_seconds
    )

    summary = batch_analyzer.analyze_batch(
        batch_size=batch_size,
        skip_analyzed=True
    )

    batch_analyzer.print_summary(summary)

    db.close()

    return summary


if __name__ == '__main__':
    # Example usage
    print("Batch Email Analyzer - Test Mode\n")

    try:
        # Analyze up to 5 emails as a test
        summary = analyze_unanalyzed_emails(
            batch_size=5,
            delay_seconds=1.0
        )

        print("\nTest completed successfully!")

    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease set ANTHROPIC_API_KEY in your .env file")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
