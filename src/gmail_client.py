"""
Gmail API Client Module

This module provides a client for interacting with the Gmail API using OAuth2 authentication.
It includes functions for listing emails, retrieving email content, and handling authentication.
"""

import os
import base64
import time
from typing import List, Dict, Optional, Any
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailClient:
    """Client for interacting with Gmail API."""

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Gmail client.

        Args:
            credentials_path: Path to credentials.json file. If not provided,
                            will look for GMAIL_CREDENTIALS_PATH in environment.
        """
        load_dotenv()

        self.credentials_path = credentials_path or os.getenv('GMAIL_CREDENTIALS_PATH')
        if not self.credentials_path:
            raise ValueError(
                "Credentials path not provided. Set GMAIL_CREDENTIALS_PATH in .env "
                "or pass credentials_path to constructor."
            )

        self.token_path = Path('config/token.json')
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Gmail API using OAuth2."""
        creds = None

        # Load existing token if available
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        # If no valid credentials available, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired token...")
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}")
                    print("Re-authenticating...")
                    creds = None

            if not creds:
                if not Path(self.credentials_path).exists():
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_path}\n"
                        "Please download credentials.json from Google Cloud Console."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
            print(f"Token saved to {self.token_path}")

        self.service = build('gmail', 'v1', credentials=creds)
        print("Successfully authenticated with Gmail API")

    def _handle_rate_limit(self, error: HttpError, attempt: int = 1, max_attempts: int = 3):
        """
        Handle rate limit errors with exponential backoff.

        Args:
            error: The HttpError that occurred
            attempt: Current attempt number
            max_attempts: Maximum number of retry attempts

        Raises:
            HttpError: If max attempts exceeded or non-rate-limit error
        """
        if error.resp.status == 429:  # Rate limit exceeded
            if attempt >= max_attempts:
                raise error

            wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
            print(f"Rate limit hit. Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)
        else:
            raise error

    def list_emails(
        self,
        label_ids: Optional[List[str]] = None,
        query: str = '',
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List emails matching the specified criteria.

        Args:
            label_ids: List of label IDs to filter by (e.g., ['INBOX', 'UNREAD'])
            query: Gmail search query (e.g., 'from:example@gmail.com')
            max_results: Maximum number of emails to return

        Returns:
            List of email metadata dictionaries

        Example:
            emails = client.list_emails(label_ids=['INBOX'], query='is:unread')
        """
        try:
            messages = []
            page_token = None

            while len(messages) < max_results:
                attempt = 1
                max_attempts = 3

                while attempt <= max_attempts:
                    try:
                        results = self.service.users().messages().list(
                            userId='me',
                            labelIds=label_ids,
                            q=query,
                            maxResults=min(max_results - len(messages), 500),
                            pageToken=page_token
                        ).execute()
                        break
                    except HttpError as error:
                        self._handle_rate_limit(error, attempt, max_attempts)
                        attempt += 1

                if 'messages' not in results:
                    break

                messages.extend(results['messages'])
                page_token = results.get('nextPageToken')

                if not page_token:
                    break

            print(f"Found {len(messages)} emails")
            return messages[:max_results]

        except HttpError as error:
            print(f"An error occurred while listing emails: {error}")
            raise

    def get_email(self, message_id: str) -> Dict[str, Any]:
        """
        Get full email details by message ID.

        Args:
            message_id: The Gmail message ID

        Returns:
            Dictionary containing full email data

        Example:
            email = client.get_email('18c5f8a1b2d3e4f5')
        """
        attempt = 1
        max_attempts = 3

        while attempt <= max_attempts:
            try:
                message = self.service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format='full'
                ).execute()
                return message
            except HttpError as error:
                self._handle_rate_limit(error, attempt, max_attempts)
                attempt += 1

        raise HttpError(f"Failed to retrieve email {message_id} after {max_attempts} attempts")

    def _decode_base64(self, data: str) -> str:
        """Decode base64 URL-safe encoded string."""
        try:
            # Add padding if needed
            padding = 4 - len(data) % 4
            if padding != 4:
                data += '=' * padding

            decoded_bytes = base64.urlsafe_b64decode(data)
            return decoded_bytes.decode('utf-8', errors='replace')
        except Exception as e:
            print(f"Error decoding base64: {e}")
            return ""

    def _extract_body_from_parts(self, parts: List[Dict]) -> Dict[str, str]:
        """
        Recursively extract email body from message parts.

        Args:
            parts: List of message parts

        Returns:
            Dictionary with 'plain' and 'html' keys
        """
        body = {'plain': '', 'html': ''}

        for part in parts:
            mime_type = part.get('mimeType', '')

            # Handle nested parts (multipart messages)
            if 'parts' in part:
                nested_body = self._extract_body_from_parts(part['parts'])
                if nested_body['plain']:
                    body['plain'] += nested_body['plain']
                if nested_body['html']:
                    body['html'] += nested_body['html']

            # Extract text/plain
            elif mime_type == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    body['plain'] += self._decode_base64(data)

            # Extract text/html
            elif mime_type == 'text/html':
                data = part.get('body', {}).get('data', '')
                if data:
                    body['html'] += self._decode_base64(data)

        return body

    def extract_email_body(self, message: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract both plain text and HTML body from an email.

        Args:
            message: Email message dictionary from get_email()

        Returns:
            Dictionary with 'plain' and 'html' keys containing email body

        Example:
            email = client.get_email(message_id)
            body = client.extract_email_body(email)
            print(body['plain'])  # Plain text version
            print(body['html'])   # HTML version
        """
        body = {'plain': '', 'html': ''}
        payload = message.get('payload', {})

        # Check if message has parts (multipart message)
        if 'parts' in payload:
            body = self._extract_body_from_parts(payload['parts'])
        else:
            # Single part message
            mime_type = payload.get('mimeType', '')
            data = payload.get('body', {}).get('data', '')

            if data:
                decoded = self._decode_base64(data)
                if mime_type == 'text/plain':
                    body['plain'] = decoded
                elif mime_type == 'text/html':
                    body['html'] = decoded

        return body

    def get_email_headers(self, message: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract common headers from an email.

        Args:
            message: Email message dictionary from get_email()

        Returns:
            Dictionary with header names as keys
        """
        headers = {}
        payload = message.get('payload', {})

        for header in payload.get('headers', []):
            name = header.get('name', '').lower()
            value = header.get('value', '')

            if name in ['from', 'to', 'subject', 'date', 'cc', 'bcc']:
                headers[name] = value

        return headers

    def test_connection(self, num_emails: int = 5) -> None:
        """
        Test Gmail API connection by fetching recent emails.

        Args:
            num_emails: Number of recent emails to fetch (default: 5)

        Example:
            client = GmailClient()
            client.test_connection()
        """
        print(f"\n{'='*60}")
        print("Testing Gmail API Connection")
        print(f"{'='*60}\n")

        try:
            # Get profile info
            profile = self.service.users().getProfile(userId='me').execute()
            print(f"Connected to: {profile.get('emailAddress')}")
            print(f"Total messages: {profile.get('messagesTotal')}")
            print(f"Total threads: {profile.get('threadsTotal')}\n")

            # Fetch recent emails
            print(f"Fetching last {num_emails} emails...\n")
            messages = self.list_emails(max_results=num_emails)

            if not messages:
                print("No messages found.")
                return

            print(f"{'='*60}")
            for i, msg in enumerate(messages, 1):
                email = self.get_email(msg['id'])
                headers = self.get_email_headers(email)
                body = self.extract_email_body(email)

                print(f"\nEmail {i}/{len(messages)}")
                print(f"{'-'*60}")
                print(f"From: {headers.get('from', 'N/A')}")
                print(f"Subject: {headers.get('subject', 'N/A')}")
                print(f"Date: {headers.get('date', 'N/A')}")

                # Show snippet of body
                plain_text = body['plain'][:200] if body['plain'] else 'N/A'
                if len(body['plain']) > 200:
                    plain_text += '...'
                print(f"Body preview: {plain_text}")
                print(f"Has HTML: {'Yes' if body['html'] else 'No'}")

            print(f"\n{'='*60}")
            print("Test completed successfully!")
            print(f"{'='*60}\n")

        except HttpError as error:
            print(f"An error occurred: {error}")
            raise


def main():
    """Main function for testing the Gmail client."""
    try:
        client = GmailClient()
        client.test_connection()
    except Exception as e:
        print(f"Error: {e}")
        print("\nPlease ensure you have:")
        print("1. Created a .env file (copy from .env.example)")
        print("2. Downloaded credentials.json from Google Cloud Console")
        print("3. Set GMAIL_CREDENTIALS_PATH in .env")


if __name__ == '__main__':
    main()
