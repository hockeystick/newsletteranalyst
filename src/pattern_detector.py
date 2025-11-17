"""
Pattern Detection Module

This module analyzes newsletter emails to detect patterns, common phrases,
and identify outliers or unique approaches.
"""

import re
import json
from typing import List, Dict, Any, Tuple
from collections import Counter, defaultdict
import statistics

from .database import NewsletterDatabase


class PatternDetector:
    """Detect patterns and anomalies in newsletter emails."""

    def __init__(self, db: NewsletterDatabase):
        """
        Initialize pattern detector.

        Args:
            db: NewsletterDatabase instance
        """
        self.db = db

    def find_common_phrases(
        self,
        min_word_length: int = 2,
        top_n: int = 50
    ) -> Dict[str, List[Tuple[str, int]]]:
        """
        Find common phrases in onboarding emails.

        Args:
            min_word_length: Minimum number of words in a phrase
            top_n: Number of top phrases to return

        Returns:
            Dictionary with phrase categories and their counts
        """
        cursor = self.db.conn.cursor()

        # Get all email subjects and bodies
        cursor.execute("""
            SELECT subject, body_text
            FROM emails
            WHERE is_analyzed = 1
        """)

        rows = cursor.fetchall()

        # Collect phrases by length
        phrases_by_length = defaultdict(Counter)

        for row in rows:
            subject = row[0] or ''
            body = row[1] or ''

            # Combine and clean text
            text = (subject + ' ' + body).lower()

            # Extract n-grams
            for n in range(min_word_length, min_word_length + 3):  # 2-grams, 3-grams, 4-grams
                ngrams = self._extract_ngrams(text, n)
                phrases_by_length[n].update(ngrams)

        # Get top phrases for each length
        results = {}
        for n, counter in phrases_by_length.items():
            # Filter out very common/generic phrases
            filtered = [
                (phrase, count) for phrase, count in counter.most_common(top_n * 2)
                if self._is_meaningful_phrase(phrase)
            ]
            results[f'{n}_word_phrases'] = filtered[:top_n]

        # Find welcome-related phrases specifically
        welcome_phrases = Counter()
        for row in rows:
            subject = (row[0] or '').lower()
            body = (row[1] or '').lower()
            text = subject + ' ' + body

            # Extract phrases containing welcome-related words
            welcome_keywords = ['welcome', 'thanks for', 'get started', 'first step',
                              'glad you', 'excited to', 'happy to have']

            for keyword in welcome_keywords:
                # Find sentences containing the keyword
                sentences = re.split(r'[.!?]', text)
                for sentence in sentences:
                    if keyword in sentence:
                        # Clean and store
                        cleaned = ' '.join(sentence.split())
                        if 10 < len(cleaned) < 200:  # Reasonable length
                            welcome_phrases[cleaned] += 1

        results['welcome_phrases'] = welcome_phrases.most_common(20)

        return results

    def _extract_ngrams(self, text: str, n: int) -> List[str]:
        """
        Extract n-grams from text.

        Args:
            text: Input text
            n: Number of words per phrase

        Returns:
            List of n-grams
        """
        # Clean text
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()

        # Filter out very short words and numbers
        words = [w for w in words if len(w) > 2 and not w.isdigit()]

        # Generate n-grams
        ngrams = []
        for i in range(len(words) - n + 1):
            phrase = ' '.join(words[i:i+n])
            ngrams.append(phrase)

        return ngrams

    def _is_meaningful_phrase(self, phrase: str) -> bool:
        """
        Filter out generic/meaningless phrases.

        Args:
            phrase: Phrase to check

        Returns:
            True if meaningful
        """
        # Filter out phrases with only common words
        common_words = {'the', 'and', 'for', 'you', 'your', 'our', 'this', 'that',
                       'with', 'from', 'are', 'can', 'will', 'have', 'has'}

        words = set(phrase.split())

        # At least one word should not be in common words
        if words.issubset(common_words):
            return False

        # Should have at least one word longer than 3 characters
        if not any(len(w) > 3 for w in words):
            return False

        return True

    def group_similar_ctas(self, similarity_threshold: float = 0.7) -> Dict[str, List[str]]:
        """
        Group similar CTAs together.

        Args:
            similarity_threshold: Threshold for grouping (not used in simple version)

        Returns:
            Dictionary with CTA groups
        """
        cursor = self.db.conn.cursor()

        cursor.execute("""
            SELECT calls_to_action
            FROM email_analysis
            WHERE calls_to_action IS NOT NULL
        """)

        rows = cursor.fetchall()

        # Collect all CTAs
        all_ctas = []
        for row in rows:
            ctas = json.loads(row[0])
            for cta in ctas:
                if isinstance(cta, dict):
                    text = cta.get('text', '')
                    cta_type = cta.get('type', 'unknown')
                else:
                    text = str(cta)
                    cta_type = 'unknown'

                if text.strip():
                    all_ctas.append({'text': text.strip(), 'type': cta_type})

        # Group by keyword/pattern
        cta_groups = defaultdict(list)

        # Define grouping patterns
        patterns = {
            'get_started': r'\b(get started|start now|begin|start your)\b',
            'sign_up': r'\b(sign up|register|join|subscribe)\b',
            'learn_more': r'\b(learn more|find out|discover|explore)\b',
            'read': r'\b(read|view|check out|see)\b',
            'try': r'\b(try|test|experience)\b',
            'contact': r'\b(contact|reach out|get in touch|email us|reply)\b',
            'download': r'\b(download|get|grab)\b',
            'follow': r'\b(follow|connect)\b',
            'settings': r'\b(settings|preferences|manage|update)\b',
            'unsubscribe': r'\b(unsubscribe|opt out)\b',
        }

        # Also group by CTA type if available
        for cta in all_ctas:
            text_lower = cta['text'].lower()

            # Check patterns
            matched = False
            for group_name, pattern in patterns.items():
                if re.search(pattern, text_lower):
                    cta_groups[group_name].append(cta['text'])
                    matched = True
                    break

            # If no pattern match, use type
            if not matched:
                if cta['type'] != 'unknown':
                    cta_groups[cta['type']].append(cta['text'])
                else:
                    cta_groups['other'].append(cta['text'])

        # Count unique CTAs in each group
        result = {}
        for group, ctas in cta_groups.items():
            # Count frequency
            cta_counter = Counter(ctas)
            result[group] = {
                'count': len(ctas),
                'unique': len(cta_counter),
                'most_common': cta_counter.most_common(10)
            }

        return result

    def identify_outliers(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Identify unusual or outlier emails.

        Returns:
            Dictionary with different types of outliers
        """
        cursor = self.db.conn.cursor()

        # Get all analyzed emails
        cursor.execute("""
            SELECT
                e.id, e.publisher_name, e.subject, e.body_text,
                a.effectiveness_score, a.tone, a.calls_to_action,
                a.value_propositions
            FROM emails e
            INNER JOIN email_analysis a ON e.id = a.email_id
        """)

        rows = cursor.fetchall()

        if not rows:
            return {}

        # Calculate statistics
        body_lengths = []
        scores = []
        cta_counts = []
        vp_counts = []

        email_data = []

        for row in rows:
            body_len = len(row[3]) if row[3] else 0
            body_lengths.append(body_len)

            if row[4]:
                scores.append(row[4])

            ctas = json.loads(row[6]) if row[6] else []
            cta_counts.append(len(ctas))

            vps = json.loads(row[7]) if row[7] else []
            vp_counts.append(len(vps))

            email_data.append({
                'id': row[0],
                'publisher': row[1],
                'subject': row[2],
                'body_length': body_len,
                'score': row[4],
                'tone': row[5],
                'cta_count': len(ctas),
                'vp_count': len(vps)
            })

        # Calculate means and standard deviations
        mean_length = statistics.mean(body_lengths)
        std_length = statistics.stdev(body_lengths) if len(body_lengths) > 1 else 0

        mean_ctas = statistics.mean(cta_counts)
        std_ctas = statistics.stdev(cta_counts) if len(cta_counts) > 1 else 0

        mean_vps = statistics.mean(vp_counts)
        std_vps = statistics.stdev(vp_counts) if len(vp_counts) > 1 else 0

        # Identify outliers
        outliers = {
            'unusually_long': [],
            'unusually_short': [],
            'very_high_score': [],
            'very_low_score': [],
            'many_ctas': [],
            'few_ctas': [],
            'unique_approach': []
        }

        for email in email_data:
            # Length outliers (beyond 2 standard deviations)
            if std_length > 0:
                if email['body_length'] > mean_length + 2 * std_length:
                    outliers['unusually_long'].append({
                        'publisher': email['publisher'],
                        'subject': email['subject'],
                        'length': email['body_length'],
                        'avg_length': int(mean_length)
                    })
                elif email['body_length'] < max(mean_length - 2 * std_length, 0):
                    outliers['unusually_short'].append({
                        'publisher': email['publisher'],
                        'subject': email['subject'],
                        'length': email['body_length'],
                        'avg_length': int(mean_length)
                    })

            # Score outliers
            if email['score']:
                if email['score'] >= 9:
                    outliers['very_high_score'].append({
                        'publisher': email['publisher'],
                        'subject': email['subject'],
                        'score': email['score']
                    })
                elif email['score'] <= 4:
                    outliers['very_low_score'].append({
                        'publisher': email['publisher'],
                        'subject': email['subject'],
                        'score': email['score']
                    })

            # CTA outliers
            if std_ctas > 0:
                if email['cta_count'] > mean_ctas + 2 * std_ctas:
                    outliers['many_ctas'].append({
                        'publisher': email['publisher'],
                        'subject': email['subject'],
                        'cta_count': email['cta_count'],
                        'avg_ctas': round(mean_ctas, 1)
                    })
                elif email['cta_count'] == 0:
                    outliers['few_ctas'].append({
                        'publisher': email['publisher'],
                        'subject': email['subject'],
                        'cta_count': email['cta_count']
                    })

        # Limit results
        for key in outliers:
            outliers[key] = outliers[key][:10]

        return outliers

    def get_tone_patterns(self) -> Dict[str, Any]:
        """
        Analyze tone patterns and correlations.

        Returns:
            Dictionary with tone analysis
        """
        cursor = self.db.conn.cursor()

        cursor.execute("""
            SELECT
                a.tone,
                a.effectiveness_score,
                e.email_sequence_number,
                p.business_model
            FROM email_analysis a
            INNER JOIN emails e ON a.email_id = e.id
            LEFT JOIN publishers p ON e.publisher_name = p.name
            WHERE a.tone IS NOT NULL
        """)

        rows = cursor.fetchall()

        # Group by tone
        tone_data = defaultdict(lambda: {
            'count': 0,
            'scores': [],
            'sequences': [],
            'business_models': []
        })

        for row in rows:
            tone = row[0]
            score = row[1]
            sequence = row[2]
            business_model = row[3]

            tone_data[tone]['count'] += 1
            if score:
                tone_data[tone]['scores'].append(score)
            if sequence:
                tone_data[tone]['sequences'].append(sequence)
            if business_model:
                tone_data[tone]['business_models'].append(business_model)

        # Calculate statistics
        results = {}
        for tone, data in tone_data.items():
            results[tone] = {
                'count': data['count'],
                'avg_score': round(statistics.mean(data['scores']), 2) if data['scores'] else None,
                'most_common_sequence': Counter(data['sequences']).most_common(1)[0] if data['sequences'] else None,
                'business_model_distribution': dict(Counter(data['business_models']).most_common()) if data['business_models'] else {}
            }

        return results


if __name__ == '__main__':
    # Example usage
    from .database import NewsletterDatabase

    print("Pattern Detector - Test Mode\n")

    db = NewsletterDatabase()
    detector = PatternDetector(db)

    # Find common phrases
    print("Finding common phrases...")
    phrases = detector.find_common_phrases(top_n=10)

    print("\nMost common 2-word phrases:")
    for phrase, count in phrases.get('2_word_phrases', [])[:10]:
        print(f"  {count:3}x  {phrase}")

    print("\nMost common welcome phrases:")
    for phrase, count in phrases.get('welcome_phrases', [])[:5]:
        print(f"  {count:2}x  {phrase[:80]}...")

    # Group CTAs
    print("\n\nGrouping CTAs...")
    cta_groups = detector.group_similar_ctas()

    for group, data in sorted(cta_groups.items(), key=lambda x: x[1]['count'], reverse=True)[:5]:
        print(f"\n{group.upper()} ({data['count']} total, {data['unique']} unique):")
        for cta, count in data['most_common'][:3]:
            print(f"  {count:2}x  {cta}")

    # Identify outliers
    print("\n\nIdentifying outliers...")
    outliers = detector.identify_outliers()

    if outliers.get('very_high_score'):
        print("\nHigh-performing emails (score ≥9):")
        for email in outliers['very_high_score'][:3]:
            print(f"  {email['score']}/10 - {email['publisher']}: {email['subject'][:50]}")

    db.close()
