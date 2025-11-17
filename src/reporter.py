"""
Reporting Module

This module provides functions for exporting analyzed email data and generating
summary reports with statistics and insights.
"""

import csv
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

from .database import NewsletterDatabase


class EmailReporter:
    """Generate reports and exports from analyzed email data."""

    def __init__(self, db: NewsletterDatabase):
        """
        Initialize reporter.

        Args:
            db: NewsletterDatabase instance
        """
        self.db = db

    def export_analysis_to_csv(
        self,
        output_path: str,
        include_raw_json: bool = False
    ) -> bool:
        """
        Export all analyzed emails to CSV.

        Args:
            output_path: Path to output CSV file
            include_raw_json: Include raw analysis JSON (default: False)

        Returns:
            True if successful
        """
        try:
            # Get all analyzed emails with analysis
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT
                    e.id, e.message_id, e.publisher_name, e.country, e.sender,
                    e.subject, e.send_date, e.email_sequence_number, e.sequence_confidence,
                    e.body_text,
                    a.primary_purpose, a.value_propositions, a.calls_to_action,
                    a.personalization_elements, a.tone, a.frequency_expectations,
                    a.notable_elements, a.effectiveness_score, a.effectiveness_reasoning,
                    a.key_takeaways, a.model_used, a.input_tokens, a.output_tokens,
                    a.analyzed_at
                FROM emails e
                INNER JOIN email_analysis a ON e.id = a.email_id
                ORDER BY e.publisher_name, e.email_sequence_number
            """)

            rows = cursor.fetchall()

            if not rows:
                print("No analyzed emails to export.")
                return False

            # Create output directory if needed
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'email_id', 'message_id', 'publisher_name', 'country', 'sender',
                    'subject', 'send_date', 'sequence_number', 'sequence_confidence',
                    'body_length', 'primary_purpose', 'tone', 'effectiveness_score',
                    'effectiveness_reasoning', 'frequency_expectations',
                    'value_proposition_count', 'value_propositions',
                    'cta_count', 'ctas', 'personalization_count', 'personalization_elements',
                    'notable_element_count', 'notable_elements', 'key_takeaways',
                    'model_used', 'input_tokens', 'output_tokens', 'analyzed_at'
                ]

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for row in rows:
                    # Parse JSON fields
                    value_props = json.loads(row[11]) if row[11] else []
                    ctas = json.loads(row[12]) if row[12] else []
                    personalization = json.loads(row[13]) if row[13] else []
                    notable = json.loads(row[16]) if row[16] else []
                    takeaways = json.loads(row[19]) if row[19] else []

                    # Format CTAs for CSV
                    cta_texts = [cta.get('text', '') if isinstance(cta, dict) else str(cta) for cta in ctas]

                    csv_row = {
                        'email_id': row[0],
                        'message_id': row[1],
                        'publisher_name': row[2],
                        'country': row[3] or '',
                        'sender': row[4],
                        'subject': row[5],
                        'send_date': row[6],
                        'sequence_number': row[7],
                        'sequence_confidence': row[8] or '',
                        'body_length': len(row[9]) if row[9] else 0,
                        'primary_purpose': row[10] or '',
                        'tone': row[14] or '',
                        'effectiveness_score': row[17] or '',
                        'effectiveness_reasoning': row[18] or '',
                        'frequency_expectations': row[15] or '',
                        'value_proposition_count': len(value_props),
                        'value_propositions': ' | '.join(value_props),
                        'cta_count': len(ctas),
                        'ctas': ' | '.join(cta_texts),
                        'personalization_count': len(personalization),
                        'personalization_elements': ' | '.join(personalization),
                        'notable_element_count': len(notable),
                        'notable_elements': ' | '.join(notable),
                        'key_takeaways': ' | '.join(takeaways),
                        'model_used': row[20] or '',
                        'input_tokens': row[21] or 0,
                        'output_tokens': row[22] or 0,
                        'analyzed_at': row[23]
                    }

                    writer.writerow(csv_row)

            print(f"✓ Exported {len(rows)} analyzed emails to {output_path}")
            return True

        except Exception as e:
            print(f"✗ Error exporting analysis: {e}")
            return False

    def get_summary_by_country(self) -> List[Dict[str, Any]]:
        """
        Generate summary statistics by country.

        Returns:
            List of country statistics
        """
        cursor = self.db.conn.cursor()

        cursor.execute("""
            SELECT
                e.country,
                COUNT(DISTINCT e.publisher_name) as publisher_count,
                COUNT(e.id) as email_count,
                AVG(a.effectiveness_score) as avg_effectiveness,
                AVG(LENGTH(e.body_text)) as avg_body_length,
                GROUP_CONCAT(DISTINCT a.tone) as tones
            FROM emails e
            INNER JOIN email_analysis a ON e.id = a.email_id
            WHERE e.country IS NOT NULL AND e.country != ''
            GROUP BY e.country
            ORDER BY email_count DESC
        """)

        results = []
        for row in cursor.fetchall():
            results.append({
                'country': row[0],
                'publisher_count': row[1],
                'email_count': row[2],
                'avg_effectiveness_score': round(row[3], 2) if row[3] else None,
                'avg_body_length': round(row[4], 0) if row[4] else None,
                'common_tones': row[5]
            })

        return results

    def get_summary_by_business_model(self) -> List[Dict[str, Any]]:
        """
        Generate summary statistics by business model.

        Returns:
            List of business model statistics
        """
        cursor = self.db.conn.cursor()

        # Get publisher business models and join with emails
        cursor.execute("""
            SELECT
                p.business_model,
                COUNT(DISTINCT e.publisher_name) as publisher_count,
                COUNT(e.id) as email_count,
                AVG(a.effectiveness_score) as avg_effectiveness,
                AVG(LENGTH(e.body_text)) as avg_body_length,
                GROUP_CONCAT(DISTINCT a.tone) as tones
            FROM emails e
            INNER JOIN email_analysis a ON e.id = a.email_id
            LEFT JOIN publishers p ON e.publisher_name = p.name
            WHERE p.business_model IS NOT NULL AND p.business_model != ''
            GROUP BY p.business_model
            ORDER BY email_count DESC
        """)

        results = []
        for row in cursor.fetchall():
            results.append({
                'business_model': row[0],
                'publisher_count': row[1],
                'email_count': row[2],
                'avg_effectiveness_score': round(row[3], 2) if row[3] else None,
                'avg_body_length': round(row[4], 0) if row[4] else None,
                'common_tones': row[5]
            })

        return results

    def get_common_patterns(self) -> Dict[str, Any]:
        """
        Identify common patterns across analyzed emails.

        Returns:
            Dictionary with pattern statistics
        """
        cursor = self.db.conn.cursor()

        # Get all analyses
        cursor.execute("""
            SELECT
                tone, calls_to_action, value_propositions,
                personalization_elements, effectiveness_score
            FROM email_analysis
        """)

        rows = cursor.fetchall()

        # Collect data
        tones = []
        all_ctas = []
        all_value_props = []
        all_personalization = []
        scores = []

        for row in rows:
            if row[0]:
                tones.append(row[0])

            if row[1]:
                ctas = json.loads(row[1])
                for cta in ctas:
                    if isinstance(cta, dict):
                        all_ctas.append(cta.get('text', ''))
                    else:
                        all_ctas.append(str(cta))

            if row[2]:
                vps = json.loads(row[2])
                all_value_props.extend(vps)

            if row[3]:
                pers = json.loads(row[3])
                all_personalization.extend(pers)

            if row[4]:
                scores.append(row[4])

        # Calculate statistics
        tone_counts = Counter(tones)
        score_dist = Counter(scores)

        # Find most common CTAs (case-insensitive, trimmed)
        cta_normalized = [cta.strip().lower() for cta in all_ctas if cta.strip()]
        cta_counts = Counter(cta_normalized)

        # Find most common value proposition themes (by keywords)
        vp_keywords = []
        for vp in all_value_props:
            words = vp.lower().split()
            # Extract meaningful keywords (longer than 3 chars)
            keywords = [w for w in words if len(w) > 3 and w.isalpha()]
            vp_keywords.extend(keywords)
        vp_keyword_counts = Counter(vp_keywords)

        # Personalization patterns
        pers_normalized = [p.strip().lower() for p in all_personalization if p.strip()]
        pers_counts = Counter(pers_normalized)

        return {
            'total_analyzed': len(rows),
            'tone_distribution': dict(tone_counts.most_common()),
            'most_common_tones': tone_counts.most_common(5),
            'score_distribution': dict(score_dist),
            'most_common_ctas': cta_counts.most_common(10),
            'most_common_vp_keywords': vp_keyword_counts.most_common(10),
            'most_common_personalization': pers_counts.most_common(10),
            'average_score': round(sum(scores) / len(scores), 2) if scores else None
        }

    def generate_text_report(self, output_path: str) -> bool:
        """
        Generate a comprehensive text report.

        Args:
            output_path: Path to output text file

        Returns:
            True if successful
        """
        try:
            # Gather all data
            db_stats = self.db.get_database_stats()
            analysis_stats = self.db.get_analysis_stats()
            country_stats = self.get_summary_by_country()
            business_stats = self.get_summary_by_business_model()
            patterns = self.get_common_patterns()

            # Create output directory
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write report
            with open(output_path, 'w', encoding='utf-8') as f:
                # Header
                f.write("=" * 70 + "\n")
                f.write("NEWSLETTER ONBOARDING EMAIL ANALYSIS REPORT\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                # Database Overview
                f.write("DATABASE OVERVIEW\n")
                f.write("-" * 70 + "\n")
                f.write(f"Total Emails: {db_stats['total_emails']}\n")
                f.write(f"Total Publishers: {db_stats['total_publishers']}\n")
                f.write(f"Analyzed Emails: {db_stats['analyzed_emails']}\n")
                f.write(f"Analysis Coverage: {db_stats['analyzed_emails']/max(db_stats['total_emails'], 1)*100:.1f}%\n")
                f.write(f"Date Range: {db_stats['first_email_date']} to {db_stats['last_email_date']}\n\n")

                # Analysis Statistics
                f.write("ANALYSIS STATISTICS\n")
                f.write("-" * 70 + "\n")
                if analysis_stats['average_effectiveness_score']:
                    f.write(f"Average Effectiveness Score: {analysis_stats['average_effectiveness_score']}/10\n")

                f.write(f"\nEffectiveness Score Distribution:\n")
                for item in analysis_stats['score_distribution']:
                    score = item['effectiveness_score']
                    count = item['count']
                    f.write(f"  {score}/10: {count} emails\n")

                # Token usage
                tokens = analysis_stats['token_usage']
                if tokens.get('total_input'):
                    f.write(f"\nToken Usage:\n")
                    f.write(f"  Total Input Tokens: {int(tokens['total_input']):,}\n")
                    f.write(f"  Total Output Tokens: {int(tokens['total_output']):,}\n")
                    f.write(f"  Average per Email: {int(tokens['avg_input'] + tokens['avg_output']):,} tokens\n")

                f.write("\n")

                # Country Analysis
                if country_stats:
                    f.write("ANALYSIS BY COUNTRY\n")
                    f.write("-" * 70 + "\n")
                    f.write(f"{'Country':<20} {'Publishers':<12} {'Emails':<8} {'Avg Score':<12} {'Avg Length':<12}\n")
                    f.write("-" * 70 + "\n")

                    for stat in country_stats:
                        f.write(
                            f"{stat['country']:<20} "
                            f"{stat['publisher_count']:<12} "
                            f"{stat['email_count']:<8} "
                            f"{stat['avg_effectiveness_score'] or 'N/A':<12} "
                            f"{int(stat['avg_body_length']) if stat['avg_body_length'] else 'N/A':<12}\n"
                        )
                    f.write("\n")

                # Business Model Analysis
                if business_stats:
                    f.write("ANALYSIS BY BUSINESS MODEL\n")
                    f.write("-" * 70 + "\n")
                    f.write(f"{'Model':<20} {'Publishers':<12} {'Emails':<8} {'Avg Score':<12} {'Avg Length':<12}\n")
                    f.write("-" * 70 + "\n")

                    for stat in business_stats:
                        f.write(
                            f"{stat['business_model']:<20} "
                            f"{stat['publisher_count']:<12} "
                            f"{stat['email_count']:<8} "
                            f"{stat['avg_effectiveness_score'] or 'N/A':<12} "
                            f"{int(stat['avg_body_length']) if stat['avg_body_length'] else 'N/A':<12}\n"
                        )
                    f.write("\n")

                # Common Patterns
                f.write("COMMON PATTERNS\n")
                f.write("-" * 70 + "\n")

                f.write(f"\nTone Distribution:\n")
                for tone, count in patterns['most_common_tones']:
                    percentage = count / patterns['total_analyzed'] * 100
                    f.write(f"  {tone}: {count} ({percentage:.1f}%)\n")

                f.write(f"\nMost Common CTAs:\n")
                for cta, count in patterns['most_common_ctas'][:10]:
                    f.write(f"  {count:3}x  {cta}\n")

                f.write(f"\nCommon Value Proposition Themes (by keyword):\n")
                for keyword, count in patterns['most_common_vp_keywords'][:10]:
                    f.write(f"  {count:3}x  {keyword}\n")

                f.write(f"\nCommon Personalization Elements:\n")
                for pers, count in patterns['most_common_personalization'][:10]:
                    f.write(f"  {count:3}x  {pers}\n")

                # Footer
                f.write("\n" + "=" * 70 + "\n")
                f.write("END OF REPORT\n")
                f.write("=" * 70 + "\n")

            print(f"✓ Generated report: {output_path}")
            return True

        except Exception as e:
            print(f"✗ Error generating report: {e}")
            import traceback
            traceback.print_exc()
            return False

    def export_by_country(self, country: str, output_path: str) -> bool:
        """
        Export analyzed emails for a specific country.

        Args:
            country: Country code to filter by
            output_path: Path to output CSV file

        Returns:
            True if successful
        """
        try:
            cursor = self.db.conn.cursor()

            cursor.execute("""
                SELECT
                    e.publisher_name, e.sender, e.subject, e.send_date,
                    e.email_sequence_number, e.body_text,
                    a.primary_purpose, a.tone, a.effectiveness_score,
                    a.value_propositions, a.calls_to_action, a.key_takeaways
                FROM emails e
                INNER JOIN email_analysis a ON e.id = a.email_id
                WHERE e.country = ?
                ORDER BY e.publisher_name, e.email_sequence_number
            """, (country,))

            rows = cursor.fetchall()

            if not rows:
                print(f"No analyzed emails found for country: {country}")
                return False

            # Create output directory
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'publisher_name', 'sender', 'subject', 'send_date', 'sequence_number',
                    'body_length', 'primary_purpose', 'tone', 'effectiveness_score',
                    'value_propositions', 'ctas', 'key_takeaways'
                ]

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for row in rows:
                    vps = json.loads(row[9]) if row[9] else []
                    ctas = json.loads(row[10]) if row[10] else []
                    cta_texts = [cta.get('text', '') if isinstance(cta, dict) else str(cta) for cta in ctas]
                    takeaways = json.loads(row[11]) if row[11] else []

                    csv_row = {
                        'publisher_name': row[0],
                        'sender': row[1],
                        'subject': row[2],
                        'send_date': row[3],
                        'sequence_number': row[4],
                        'body_length': len(row[5]) if row[5] else 0,
                        'primary_purpose': row[6] or '',
                        'tone': row[7] or '',
                        'effectiveness_score': row[8] or '',
                        'value_propositions': ' | '.join(vps),
                        'ctas': ' | '.join(cta_texts),
                        'key_takeaways': ' | '.join(takeaways)
                    }

                    writer.writerow(csv_row)

            print(f"✓ Exported {len(rows)} emails for {country} to {output_path}")
            return True

        except Exception as e:
            print(f"✗ Error exporting by country: {e}")
            return False


if __name__ == '__main__':
    # Example usage
    from .database import NewsletterDatabase

    print("Email Reporter - Test Mode\n")

    db = NewsletterDatabase()
    reporter = EmailReporter(db)

    # Get patterns
    patterns = reporter.get_common_patterns()
    print(f"Total analyzed: {patterns['total_analyzed']}")
    print(f"\nMost common tones: {patterns['most_common_tones']}")
    print(f"\nMost common CTAs:")
    for cta, count in patterns['most_common_ctas'][:5]:
        print(f"  {count}x {cta}")

    db.close()
