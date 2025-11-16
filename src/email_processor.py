"""
Email Processing Module

This module provides functions for processing newsletter emails including:
- Metadata extraction
- HTML to text conversion
- Email deduplication
- Sequence detection for onboarding series
"""

import re
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import html2text
from bs4 import BeautifulSoup


class EmailProcessor:
    """Process and analyze newsletter emails."""

    def __init__(self):
        """Initialize email processor."""
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.body_width = 0  # Don't wrap text
        self.html_converter.ignore_emphasis = False

    def extract_metadata(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from a Gmail email object.

        Args:
            email: Gmail email dictionary from GmailClient.get_email()

        Returns:
            Dictionary with extracted metadata
        """
        headers = self._get_headers_dict(email)

        # Extract basic metadata
        metadata = {
            'message_id': email.get('id', ''),
            'thread_id': email.get('threadId', ''),
            'sender': headers.get('from', ''),
            'sender_email': self._extract_email_address(headers.get('from', '')),
            'sender_name': self._extract_name(headers.get('from', '')),
            'recipient': headers.get('to', ''),
            'subject': headers.get('subject', ''),
            'date': headers.get('date', ''),
            'timestamp': self._parse_timestamp(headers.get('date', '')),
            'labels': email.get('labelIds', []),
            'snippet': email.get('snippet', ''),
            'size_estimate': email.get('sizeEstimate', 0),
        }

        # Add additional headers if present
        optional_headers = ['cc', 'bcc', 'reply-to', 'list-unsubscribe']
        for header in optional_headers:
            if header in headers:
                metadata[header.replace('-', '_')] = headers[header]

        return metadata

    def _get_headers_dict(self, email: Dict[str, Any]) -> Dict[str, str]:
        """Convert email headers to dictionary."""
        headers = {}
        payload = email.get('payload', {})

        for header in payload.get('headers', []):
            name = header.get('name', '').lower()
            value = header.get('value', '')
            headers[name] = value

        return headers

    def _extract_email_address(self, from_field: str) -> str:
        """
        Extract email address from From field.

        Example: "John Doe <john@example.com>" -> "john@example.com"
        """
        match = re.search(r'<(.+?)>', from_field)
        if match:
            return match.group(1)
        # If no angle brackets, assume the whole field is the email
        if '@' in from_field:
            return from_field.strip()
        return ''

    def _extract_name(self, from_field: str) -> str:
        """
        Extract sender name from From field.

        Example: "John Doe <john@example.com>" -> "John Doe"
        """
        # Check if name is before angle bracket
        match = re.match(r'(.+?)\s*<', from_field)
        if match:
            name = match.group(1).strip()
            # Remove quotes if present
            name = name.strip('"\'')
            return name

        # If no angle brackets, try to extract name from email
        if '@' in from_field:
            # No separate name provided
            return ''

        return from_field.strip()

    def _parse_timestamp(self, date_str: str) -> Optional[int]:
        """
        Parse email date string to Unix timestamp.

        Args:
            date_str: Email date string (RFC 2822 format)

        Returns:
            Unix timestamp (seconds since epoch) or None
        """
        if not date_str:
            return None

        try:
            dt = parsedate_to_datetime(date_str)
            return int(dt.timestamp())
        except Exception as e:
            print(f"Error parsing date '{date_str}': {e}")
            return None

    def html_to_text(self, html_content: str, preserve_structure: bool = True) -> str:
        """
        Convert HTML email to plain text while preserving structure.

        Args:
            html_content: HTML string
            preserve_structure: If True, preserve formatting like lists, headers

        Returns:
            Plain text version of the email
        """
        if not html_content:
            return ''

        if preserve_structure:
            # Use html2text for better structure preservation
            try:
                text = self.html_converter.handle(html_content)
                return text.strip()
            except Exception as e:
                print(f"Error converting HTML with html2text: {e}")
                # Fallback to BeautifulSoup

        # Use BeautifulSoup as fallback or for simple conversion
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for script in soup(['script', 'style', 'meta', 'link']):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            return text
        except Exception as e:
            print(f"Error converting HTML with BeautifulSoup: {e}")
            return ''

    def generate_email_hash(
        self,
        sender: str,
        subject: str,
        body_text: str,
        timestamp: Optional[int] = None
    ) -> str:
        """
        Generate a unique hash for email deduplication.

        Uses sender, subject, and first 500 chars of body to create hash.
        Optionally includes timestamp for more strict deduplication.

        Args:
            sender: Email sender
            subject: Email subject
            body_text: Email body (plain text)
            timestamp: Optional timestamp for stricter matching

        Returns:
            SHA256 hash string
        """
        # Normalize inputs
        sender = sender.lower().strip()
        subject = re.sub(r'\s+', ' ', subject.strip())

        # Use first 500 chars of body to avoid issues with dynamic content at end
        body_snippet = body_text[:500].strip()
        body_snippet = re.sub(r'\s+', ' ', body_snippet)

        # Create hash input
        hash_input = f"{sender}|{subject}|{body_snippet}"

        if timestamp:
            hash_input += f"|{timestamp}"

        # Generate hash
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

    def is_duplicate(
        self,
        email_hash: str,
        existing_hashes: List[str]
    ) -> bool:
        """
        Check if email is a duplicate.

        Args:
            email_hash: Hash of current email
            existing_hashes: List of hashes from previously processed emails

        Returns:
            True if duplicate, False otherwise
        """
        return email_hash in existing_hashes

    def detect_sequence_position(
        self,
        emails: List[Dict[str, Any]],
        current_email: Dict[str, Any]
    ) -> Tuple[int, str]:
        """
        Detect position of email in onboarding sequence.

        Analyzes timing patterns and content to determine if email is part of
        a welcome series (1st, 2nd, 3rd email, etc.).

        Args:
            emails: List of emails from same sender, sorted by timestamp
            current_email: The email to analyze

        Returns:
            Tuple of (sequence_number, confidence_level)
            confidence_level: 'high', 'medium', 'low'
        """
        current_timestamp = current_email.get('timestamp')
        current_subject = current_email.get('subject', '').lower()

        if not current_timestamp:
            return (0, 'low')

        # Check for explicit sequence indicators in subject
        sequence_patterns = [
            (r'welcome(?:\s+to)?(?:\s+email)?(?:\s+#?1|\s+one)?(?:\s*[-|:])?', 1),
            (r'(?:email\s*)?#?\s*1(?:\s*[-|:])', 1),
            (r'(?:email\s*)?#?\s*2(?:\s*[-|:])', 2),
            (r'(?:email\s*)?#?\s*3(?:\s*[-|:])', 3),
            (r'(?:email\s*)?#?\s*4(?:\s*[-|:])', 4),
            (r'(?:email\s*)?#?\s*5(?:\s*[-|:])', 5),
            (r'day\s*1(?:\s*[-|:])', 1),
            (r'day\s*2(?:\s*[-|:])', 2),
            (r'day\s*3(?:\s*[-|:])', 3),
        ]

        for pattern, seq_num in sequence_patterns:
            if re.search(pattern, current_subject):
                return (seq_num, 'high')

        # If we don't have other emails from same sender, check content
        if not emails:
            # Check if it looks like a welcome email
            welcome_keywords = ['welcome', 'getting started', 'first step', 'introduction']
            if any(keyword in current_subject for keyword in welcome_keywords):
                return (1, 'medium')
            return (0, 'low')

        # Sort emails by timestamp
        sorted_emails = sorted(emails, key=lambda x: x.get('timestamp', 0))

        # Find position of current email
        current_position = None
        for idx, email in enumerate(sorted_emails):
            if email.get('message_id') == current_email.get('message_id'):
                current_position = idx
                break

        if current_position is None:
            return (0, 'low')

        # Analyze timing patterns
        sequence_num = current_position + 1  # 1-indexed

        # Check timing patterns (onboarding emails typically sent within first week)
        if sequence_num == 1:
            return (1, 'high')

        # Calculate time since first email
        first_email_timestamp = sorted_emails[0].get('timestamp', 0)
        time_diff_hours = (current_timestamp - first_email_timestamp) / 3600

        # Typical onboarding patterns:
        # Email 1: Immediate
        # Email 2: 1-3 days later
        # Email 3: 3-7 days later
        # Email 4+: 7+ days later

        confidence = 'medium'

        if sequence_num == 2 and 24 <= time_diff_hours <= 72:
            confidence = 'high'
        elif sequence_num == 3 and 72 <= time_diff_hours <= 168:
            confidence = 'high'
        elif sequence_num >= 4 and time_diff_hours <= 336:  # Within 2 weeks
            confidence = 'medium'
        elif time_diff_hours > 336:  # More than 2 weeks
            # Probably not part of onboarding series
            confidence = 'low'
            sequence_num = 0

        return (sequence_num, confidence)

    def extract_publisher_info(self, sender_email: str, sender_name: str) -> Dict[str, str]:
        """
        Extract publisher information from sender details.

        Args:
            sender_email: Sender email address
            sender_name: Sender name

        Returns:
            Dictionary with publisher info
        """
        # Extract domain
        domain = ''
        if '@' in sender_email:
            domain = sender_email.split('@')[1].lower()

        # Clean up publisher name
        publisher_name = sender_name if sender_name else domain

        # Remove common email service indicators
        publisher_name = re.sub(r'\s*via\s+\w+.*$', '', publisher_name, flags=re.IGNORECASE)

        return {
            'domain': domain,
            'publisher_name': publisher_name,
            'sender_email': sender_email,
        }

    def process_email(
        self,
        email: Dict[str, Any],
        body_plain: str,
        body_html: str,
        existing_hashes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process a complete email with all extraction and analysis.

        Args:
            email: Gmail email object
            body_plain: Plain text body
            body_html: HTML body
            existing_hashes: List of existing email hashes for deduplication

        Returns:
            Dictionary with all processed email data
        """
        # Extract metadata
        metadata = self.extract_metadata(email)

        # Convert HTML to text if plain text not available
        if not body_plain and body_html:
            body_plain = self.html_to_text(body_html)

        # Generate hash for deduplication
        email_hash = self.generate_email_hash(
            metadata['sender'],
            metadata['subject'],
            body_plain,
            metadata.get('timestamp')
        )

        # Check for duplicates
        is_dup = False
        if existing_hashes:
            is_dup = self.is_duplicate(email_hash, existing_hashes)

        # Extract publisher info
        publisher_info = self.extract_publisher_info(
            metadata['sender_email'],
            metadata['sender_name']
        )

        # Combine all data
        processed = {
            **metadata,
            **publisher_info,
            'body_text': body_plain,
            'body_html': body_html,
            'email_hash': email_hash,
            'is_duplicate': is_dup,
            'raw_json': json.dumps(email),
        }

        return processed


def analyze_email_sequence(emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyze a list of emails to detect sequence positions.

    Args:
        emails: List of processed email dictionaries with timestamp

    Returns:
        List of emails with sequence_number and sequence_confidence added
    """
    processor = EmailProcessor()

    # Group emails by sender
    emails_by_sender = {}
    for email in emails:
        sender = email.get('sender_email', '')
        if sender not in emails_by_sender:
            emails_by_sender[sender] = []
        emails_by_sender[sender].append(email)

    # Detect sequences for each sender
    for sender, sender_emails in emails_by_sender.items():
        # Sort by timestamp
        sorted_emails = sorted(sender_emails, key=lambda x: x.get('timestamp', 0))

        for email in sorted_emails:
            seq_num, confidence = processor.detect_sequence_position(
                sorted_emails,
                email
            )
            email['sequence_number'] = seq_num
            email['sequence_confidence'] = confidence

    return emails


if __name__ == '__main__':
    # Example usage
    processor = EmailProcessor()

    # Test HTML to text conversion
    sample_html = """
    <html>
        <body>
            <h1>Welcome to our newsletter!</h1>
            <p>This is the <strong>first email</strong> in our onboarding series.</p>
            <ul>
                <li>Feature 1</li>
                <li>Feature 2</li>
            </ul>
        </body>
    </html>
    """

    text = processor.html_to_text(sample_html)
    print("HTML to Text conversion:")
    print(text)
    print("\n" + "="*60 + "\n")

    # Test hash generation
    hash1 = processor.generate_email_hash(
        "newsletter@example.com",
        "Welcome to Example Newsletter",
        "This is the first email..."
    )
    print(f"Email hash: {hash1}")
