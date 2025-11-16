"""
Database Module

This module handles SQLite database operations for storing newsletter emails
and publisher information.
"""

import sqlite3
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path


class NewsletterDatabase:
    """SQLite database for newsletter emails and publishers."""

    def __init__(self, db_path: str = 'data/newsletter_emails.db'):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        # Ensure data directory exists
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = str(db_path)
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        print(f"Connected to database: {self.db_path}")

    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        # Publishers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publishers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                domain TEXT,
                country TEXT,
                language TEXT,
                website TEXT,
                business_model TEXT,
                signup_date TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, domain)
            )
        """)

        # Emails table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                thread_id TEXT,
                publisher_id INTEGER,
                publisher_name TEXT NOT NULL,
                country TEXT,
                signup_date TEXT,
                email_sequence_number INTEGER DEFAULT 0,
                sequence_confidence TEXT,
                sender TEXT NOT NULL,
                sender_email TEXT,
                sender_name TEXT,
                subject TEXT,
                send_timestamp INTEGER,
                send_date TEXT,
                body_text TEXT,
                body_html TEXT,
                email_hash TEXT,
                labels TEXT,
                snippet TEXT,
                raw_json TEXT,
                is_analyzed BOOLEAN DEFAULT 0,
                analysis_notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (publisher_id) REFERENCES publishers (id)
            )
        """)

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_emails_publisher
            ON emails(publisher_name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_emails_sender
            ON emails(sender_email)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_emails_timestamp
            ON emails(send_timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_emails_sequence
            ON emails(email_sequence_number)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_emails_hash
            ON emails(email_hash)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_emails_analyzed
            ON emails(is_analyzed)
        """)

        self.conn.commit()
        print("Database tables created/verified")

    def save_publisher(
        self,
        name: str,
        domain: Optional[str] = None,
        country: Optional[str] = None,
        language: Optional[str] = None,
        website: Optional[str] = None,
        business_model: Optional[str] = None,
        signup_date: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Save or update publisher information.

        Args:
            name: Publisher name
            domain: Email domain
            country: Publisher country
            language: Primary language
            website: Publisher website URL
            business_model: Business model description
            signup_date: Date of newsletter signup
            notes: Additional notes

        Returns:
            Publisher ID
        """
        cursor = self.conn.cursor()

        # Check if publisher exists
        cursor.execute(
            "SELECT id FROM publishers WHERE name = ? AND domain = ?",
            (name, domain)
        )
        result = cursor.fetchone()

        if result:
            # Update existing publisher
            publisher_id = result[0]
            cursor.execute("""
                UPDATE publishers
                SET country = COALESCE(?, country),
                    language = COALESCE(?, language),
                    website = COALESCE(?, website),
                    business_model = COALESCE(?, business_model),
                    signup_date = COALESCE(?, signup_date),
                    notes = COALESCE(?, notes),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (country, language, website, business_model, signup_date, notes, publisher_id))
        else:
            # Insert new publisher
            cursor.execute("""
                INSERT INTO publishers (name, domain, country, language, website, business_model, signup_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, domain, country, language, website, business_model, signup_date, notes))
            publisher_id = cursor.lastrowid

        self.conn.commit()
        return publisher_id

    def save_email(
        self,
        message_id: str,
        publisher_name: str,
        sender: str,
        subject: str,
        send_timestamp: int,
        body_text: str,
        body_html: str,
        raw_json: str,
        thread_id: Optional[str] = None,
        publisher_id: Optional[int] = None,
        country: Optional[str] = None,
        signup_date: Optional[str] = None,
        email_sequence_number: int = 0,
        sequence_confidence: Optional[str] = None,
        sender_email: Optional[str] = None,
        sender_name: Optional[str] = None,
        email_hash: Optional[str] = None,
        labels: Optional[List[str]] = None,
        snippet: Optional[str] = None
    ) -> int:
        """
        Save email to database.

        Args:
            message_id: Gmail message ID
            publisher_name: Name of newsletter publisher
            sender: Full sender string
            subject: Email subject
            send_timestamp: Unix timestamp
            body_text: Plain text body
            body_html: HTML body
            raw_json: Raw email JSON
            ... (other optional parameters)

        Returns:
            Email ID, or existing ID if duplicate
        """
        cursor = self.conn.cursor()

        # Check if email already exists
        cursor.execute("SELECT id FROM emails WHERE message_id = ?", (message_id,))
        result = cursor.fetchone()

        if result:
            print(f"Email {message_id} already exists (ID: {result[0]})")
            return result[0]

        # Convert timestamp to date string
        send_date = datetime.fromtimestamp(send_timestamp).isoformat() if send_timestamp else None

        # Convert labels list to JSON string
        labels_json = json.dumps(labels) if labels else None

        # Insert email
        cursor.execute("""
            INSERT INTO emails (
                message_id, thread_id, publisher_id, publisher_name, country, signup_date,
                email_sequence_number, sequence_confidence, sender, sender_email, sender_name,
                subject, send_timestamp, send_date, body_text, body_html, email_hash,
                labels, snippet, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_id, thread_id, publisher_id, publisher_name, country, signup_date,
            email_sequence_number, sequence_confidence, sender, sender_email, sender_name,
            subject, send_timestamp, send_date, body_text, body_html, email_hash,
            labels_json, snippet, raw_json
        ))

        email_id = cursor.lastrowid
        self.conn.commit()

        return email_id

    def get_emails_by_publisher(
        self,
        publisher_name: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all emails from a specific publisher.

        Args:
            publisher_name: Name of publisher
            limit: Maximum number of emails to return

        Returns:
            List of email dictionaries
        """
        cursor = self.conn.cursor()

        query = """
            SELECT * FROM emails
            WHERE publisher_name = ?
            ORDER BY send_timestamp ASC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, (publisher_name,))
        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def get_unanalyzed_emails(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get emails that haven't been analyzed yet.

        Args:
            limit: Maximum number of emails to return

        Returns:
            List of email dictionaries
        """
        cursor = self.conn.cursor()

        query = """
            SELECT * FROM emails
            WHERE is_analyzed = 0
            ORDER BY send_timestamp ASC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def get_all_email_hashes(self) -> List[str]:
        """
        Get all email hashes for deduplication.

        Returns:
            List of email hash strings
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT email_hash FROM emails WHERE email_hash IS NOT NULL")
        rows = cursor.fetchall()
        return [row[0] for row in rows]

    def get_emails_by_sender(
        self,
        sender_email: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all emails from a specific sender email address.

        Args:
            sender_email: Sender email address
            limit: Maximum number of emails to return

        Returns:
            List of email dictionaries
        """
        cursor = self.conn.cursor()

        query = """
            SELECT * FROM emails
            WHERE sender_email = ?
            ORDER BY send_timestamp ASC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, (sender_email,))
        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def mark_email_analyzed(
        self,
        email_id: int,
        analysis_notes: Optional[str] = None
    ) -> bool:
        """
        Mark an email as analyzed.

        Args:
            email_id: Email ID
            analysis_notes: Optional notes about the analysis

        Returns:
            True if successful
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            UPDATE emails
            SET is_analyzed = 1, analysis_notes = ?
            WHERE id = ?
        """, (analysis_notes, email_id))

        self.conn.commit()
        return cursor.rowcount > 0

    def get_publisher_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics for each publisher.

        Returns:
            List of publisher statistics
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                publisher_name,
                COUNT(*) as email_count,
                MIN(send_date) as first_email,
                MAX(send_date) as last_email,
                SUM(CASE WHEN is_analyzed = 1 THEN 1 ELSE 0 END) as analyzed_count
            FROM emails
            GROUP BY publisher_name
            ORDER BY email_count DESC
        """)

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_sequence_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics about email sequences.

        Returns:
            List of sequence statistics by publisher
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                publisher_name,
                email_sequence_number,
                COUNT(*) as count,
                sequence_confidence,
                AVG(LENGTH(body_text)) as avg_length
            FROM emails
            WHERE email_sequence_number > 0
            GROUP BY publisher_name, email_sequence_number, sequence_confidence
            ORDER BY publisher_name, email_sequence_number
        """)

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def search_emails(
        self,
        keyword: Optional[str] = None,
        publisher: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sequence_number: Optional[int] = None,
        limit: Optional[int] = 100
    ) -> List[Dict[str, Any]]:
        """
        Search emails with various filters.

        Args:
            keyword: Search in subject and body
            publisher: Filter by publisher name
            start_date: Filter by date (YYYY-MM-DD format)
            end_date: Filter by date (YYYY-MM-DD format)
            sequence_number: Filter by sequence number
            limit: Maximum results

        Returns:
            List of matching emails
        """
        cursor = self.conn.cursor()

        query = "SELECT * FROM emails WHERE 1=1"
        params = []

        if keyword:
            query += " AND (subject LIKE ? OR body_text LIKE ?)"
            keyword_pattern = f"%{keyword}%"
            params.extend([keyword_pattern, keyword_pattern])

        if publisher:
            query += " AND publisher_name = ?"
            params.append(publisher)

        if start_date:
            query += " AND send_date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND send_date <= ?"
            params.append(end_date)

        if sequence_number is not None:
            query += " AND email_sequence_number = ?"
            params.append(sequence_number)

        query += " ORDER BY send_timestamp DESC"

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get overall database statistics.

        Returns:
            Dictionary with database stats
        """
        cursor = self.conn.cursor()

        # Total emails
        cursor.execute("SELECT COUNT(*) FROM emails")
        total_emails = cursor.fetchone()[0]

        # Total publishers
        cursor.execute("SELECT COUNT(DISTINCT publisher_name) FROM emails")
        total_publishers = cursor.fetchone()[0]

        # Analyzed emails
        cursor.execute("SELECT COUNT(*) FROM emails WHERE is_analyzed = 1")
        analyzed_emails = cursor.fetchone()[0]

        # Emails with sequences
        cursor.execute("SELECT COUNT(*) FROM emails WHERE email_sequence_number > 0")
        sequenced_emails = cursor.fetchone()[0]

        # Date range
        cursor.execute("SELECT MIN(send_date), MAX(send_date) FROM emails")
        date_range = cursor.fetchone()

        return {
            'total_emails': total_emails,
            'total_publishers': total_publishers,
            'analyzed_emails': analyzed_emails,
            'unanalyzed_emails': total_emails - analyzed_emails,
            'sequenced_emails': sequenced_emails,
            'first_email_date': date_range[0],
            'last_email_date': date_range[1],
        }

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == '__main__':
    # Example usage
    print("Testing Newsletter Database...\n")

    with NewsletterDatabase() as db:
        # Get stats
        stats = db.get_database_stats()
        print("Database Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

        print("\nPublisher Statistics:")
        pub_stats = db.get_publisher_stats()
        for stat in pub_stats[:5]:  # Show top 5
            print(f"  {stat['publisher_name']}: {stat['email_count']} emails")
