"""
Publisher Manager Module

This module provides functions for managing newsletter publishers,
including adding, listing, and exporting publisher data.
"""

import csv
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from .database import NewsletterDatabase


class PublisherManager:
    """Manage newsletter publishers."""

    def __init__(self, db: NewsletterDatabase):
        """
        Initialize publisher manager.

        Args:
            db: NewsletterDatabase instance
        """
        self.db = db

    def add_publisher_interactive(self) -> Optional[int]:
        """
        Add a new publisher with interactive prompts.

        Returns:
            Publisher ID if successful, None otherwise
        """
        print("\n" + "=" * 70)
        print("Add New Publisher")
        print("=" * 70)
        print("Enter publisher information (press Enter to skip optional fields)\n")

        # Required fields
        name = input("Publisher name *: ").strip()
        if not name:
            print("Error: Publisher name is required.")
            return None

        # Optional fields
        domain = input("Email domain (e.g., newsletter.com): ").strip() or None
        country = input("Country (e.g., US, UK, CA): ").strip() or None
        language = input("Language (e.g., en, es, fr): ").strip() or None
        website = input("Website URL: ").strip() or None

        print("\nBusiness model options: free, freemium, paid, sponsored, other")
        business_model = input("Business model: ").strip() or None

        # Signup date (default to today)
        print(f"\nSignup date (YYYY-MM-DD, default: today)")
        signup_date_input = input("Signup date: ").strip()

        if signup_date_input:
            try:
                # Validate date format
                datetime.strptime(signup_date_input, '%Y-%m-%d')
                signup_date = signup_date_input
            except ValueError:
                print(f"Invalid date format. Using today's date.")
                signup_date = datetime.now().strftime('%Y-%m-%d')
        else:
            signup_date = datetime.now().strftime('%Y-%m-%d')

        notes = input("Notes (optional): ").strip() or None

        # Confirmation
        print("\n" + "-" * 70)
        print("Publisher Details:")
        print(f"  Name: {name}")
        print(f"  Domain: {domain or 'N/A'}")
        print(f"  Country: {country or 'N/A'}")
        print(f"  Language: {language or 'N/A'}")
        print(f"  Website: {website or 'N/A'}")
        print(f"  Business Model: {business_model or 'N/A'}")
        print(f"  Signup Date: {signup_date}")
        print(f"  Notes: {notes or 'N/A'}")
        print("-" * 70)

        confirm = input("\nSave this publisher? (y/n): ").strip().lower()

        if confirm not in ['y', 'yes']:
            print("Publisher not saved.")
            return None

        # Save to database
        try:
            publisher_id = self.db.save_publisher(
                name=name,
                domain=domain,
                country=country,
                language=language,
                website=website,
                business_model=business_model,
                signup_date=signup_date,
                notes=notes
            )
            print(f"\n✓ Publisher saved successfully (ID: {publisher_id})")
            return publisher_id

        except Exception as e:
            print(f"\n✗ Error saving publisher: {e}")
            return None

    def add_publisher(
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
        Add a new publisher programmatically.

        Args:
            name: Publisher name (required)
            domain: Email domain
            country: Country code
            language: Language code
            website: Website URL
            business_model: Business model type
            signup_date: Signup date (YYYY-MM-DD)
            notes: Additional notes

        Returns:
            Publisher ID
        """
        if not signup_date:
            signup_date = datetime.now().strftime('%Y-%m-%d')

        return self.db.save_publisher(
            name=name,
            domain=domain,
            country=country,
            language=language,
            website=website,
            business_model=business_model,
            signup_date=signup_date,
            notes=notes
        )

    def list_publishers(self, detailed: bool = False) -> List[Dict[str, Any]]:
        """
        List all publishers with their statistics.

        Args:
            detailed: If True, include detailed statistics

        Returns:
            List of publisher dictionaries with stats
        """
        # Get publisher stats from emails
        email_stats = self.db.get_publisher_stats()

        # Get publisher details from publishers table
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT
                id, name, domain, country, language,
                website, business_model, signup_date, notes,
                created_at
            FROM publishers
            ORDER BY name
        """)

        publishers_data = {}
        for row in cursor.fetchall():
            publishers_data[row[1]] = {  # Key by name
                'id': row[0],
                'name': row[1],
                'domain': row[2],
                'country': row[3],
                'language': row[4],
                'website': row[5],
                'business_model': row[6],
                'signup_date': row[7],
                'notes': row[8],
                'created_at': row[9],
            }

        # Merge with email stats
        results = []

        # Add publishers with emails
        for stat in email_stats:
            pub_name = stat['publisher_name']
            pub_data = publishers_data.get(pub_name, {
                'id': None,
                'name': pub_name,
                'domain': None,
                'country': None,
                'language': None,
                'website': None,
                'business_model': None,
                'signup_date': None,
                'notes': None,
                'created_at': None,
            })

            pub_data.update({
                'email_count': stat['email_count'],
                'first_email': stat['first_email'],
                'last_email': stat['last_email'],
                'analyzed_count': stat['analyzed_count'],
            })

            results.append(pub_data)

            # Remove from publishers_data so we don't duplicate
            if pub_name in publishers_data:
                del publishers_data[pub_name]

        # Add publishers without emails
        for pub_name, pub_data in publishers_data.items():
            pub_data.update({
                'email_count': 0,
                'first_email': None,
                'last_email': None,
                'analyzed_count': 0,
            })
            results.append(pub_data)

        # Sort by email count (descending), then by name
        results.sort(key=lambda x: (-x['email_count'], x['name']))

        return results

    def export_publishers_csv(
        self,
        output_path: str,
        include_template_fields: bool = True
    ) -> bool:
        """
        Export publishers to CSV file.

        Args:
            output_path: Path to output CSV file
            include_template_fields: If True, include signup tracking fields

        Returns:
            True if successful
        """
        try:
            publishers = self.list_publishers(detailed=True)

            # Create output directory if needed
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                if include_template_fields:
                    # Full template for signup tracking
                    fieldnames = [
                        'Publisher',
                        'Country',
                        'Language',
                        'Website',
                        'Business Model',
                        'Signup Date',
                        'Signup URL',
                        'Confirmation Received',
                        'Onboarding Emails Count',
                        'First Email Date',
                        'Last Email Date',
                        'Notes'
                    ]
                else:
                    # Basic export
                    fieldnames = [
                        'Publisher',
                        'Domain',
                        'Country',
                        'Language',
                        'Website',
                        'Business Model',
                        'Signup Date',
                        'Email Count',
                        'First Email',
                        'Last Email',
                        'Notes'
                    ]

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for pub in publishers:
                    if include_template_fields:
                        row = {
                            'Publisher': pub['name'],
                            'Country': pub.get('country', ''),
                            'Language': pub.get('language', ''),
                            'Website': pub.get('website', ''),
                            'Business Model': pub.get('business_model', ''),
                            'Signup Date': pub.get('signup_date', ''),
                            'Signup URL': '',  # Template field for manual entry
                            'Confirmation Received': 'Yes' if pub['email_count'] > 0 else 'No',
                            'Onboarding Emails Count': pub['email_count'],
                            'First Email Date': pub.get('first_email', '')[:10] if pub.get('first_email') else '',
                            'Last Email Date': pub.get('last_email', '')[:10] if pub.get('last_email') else '',
                            'Notes': pub.get('notes', '')
                        }
                    else:
                        row = {
                            'Publisher': pub['name'],
                            'Domain': pub.get('domain', ''),
                            'Country': pub.get('country', ''),
                            'Language': pub.get('language', ''),
                            'Website': pub.get('website', ''),
                            'Business Model': pub.get('business_model', ''),
                            'Signup Date': pub.get('signup_date', ''),
                            'Email Count': pub['email_count'],
                            'First Email': pub.get('first_email', '')[:10] if pub.get('first_email') else '',
                            'Last Email': pub.get('last_email', '')[:10] if pub.get('last_email') else '',
                            'Notes': pub.get('notes', '')
                        }

                    writer.writerow(row)

            print(f"✓ Exported {len(publishers)} publishers to {output_path}")
            return True

        except Exception as e:
            print(f"✗ Error exporting publishers: {e}")
            return False

    def generate_signup_template(self, output_path: str = 'output/signup_tracking_template.csv') -> bool:
        """
        Generate an empty signup tracking template CSV.

        This creates a Google Sheets-compatible template for tracking
        newsletter signups during the collection phase.

        Args:
            output_path: Path to output CSV file

        Returns:
            True if successful
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            fieldnames = [
                'Publisher',
                'Country',
                'Language',
                'Website',
                'Business Model',
                'Signup Date',
                'Signup URL',
                'Confirmation Received',
                'Onboarding Emails Count',
                'First Email Date',
                'Last Email Date',
                'Notes'
            ]

            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                # Add a few example rows
                examples = [
                    {
                        'Publisher': 'Example Newsletter',
                        'Country': 'US',
                        'Language': 'en',
                        'Website': 'https://example.com',
                        'Business Model': 'freemium',
                        'Signup Date': '2025-01-15',
                        'Signup URL': 'https://example.com/subscribe',
                        'Confirmation Received': 'Yes',
                        'Onboarding Emails Count': '3',
                        'First Email Date': '2025-01-15',
                        'Last Email Date': '2025-01-20',
                        'Notes': 'Good onboarding sequence'
                    },
                    {
                        'Publisher': 'Tech Weekly',
                        'Country': 'UK',
                        'Language': 'en',
                        'Website': 'https://techweekly.io',
                        'Business Model': 'free',
                        'Signup Date': '2025-01-16',
                        'Signup URL': 'https://techweekly.io/join',
                        'Confirmation Received': 'Yes',
                        'Onboarding Emails Count': '2',
                        'First Email Date': '2025-01-16',
                        'Last Email Date': '2025-01-18',
                        'Notes': ''
                    }
                ]

                for example in examples:
                    writer.writerow(example)

            print(f"✓ Created signup tracking template at {output_path}")
            print(f"  You can open this in Google Sheets or Excel to track signups")
            return True

        except Exception as e:
            print(f"✗ Error creating template: {e}")
            return False


def print_publisher_table(publishers: List[Dict[str, Any]], limit: Optional[int] = None):
    """
    Print publishers in a formatted table.

    Args:
        publishers: List of publisher dictionaries
        limit: Maximum number to display
    """
    if not publishers:
        print("No publishers found.")
        return

    display_pubs = publishers[:limit] if limit else publishers

    print(f"\nFound {len(publishers)} publisher(s):")
    print()
    print(f"{'#':<4} {'Publisher':<35} {'Country':<8} {'Lang':<5} {'Model':<10} {'Emails':<8} {'Signup Date':<12}")
    print("-" * 90)

    for i, pub in enumerate(display_pubs, 1):
        print(
            f"{i:<4} "
            f"{pub['name'][:34]:<35} "
            f"{pub.get('country', 'N/A'):<8} "
            f"{pub.get('language', 'N/A'):<5} "
            f"{pub.get('business_model', 'N/A')[:9]:<10} "
            f"{pub['email_count']:<8} "
            f"{pub.get('signup_date', 'N/A')[:10]:<12}"
        )

    if limit and len(publishers) > limit:
        print(f"\n... and {len(publishers) - limit} more")

    print()


if __name__ == '__main__':
    # Example usage
    from .database import NewsletterDatabase

    print("Publisher Manager - Test Mode\n")

    db = NewsletterDatabase()
    manager = PublisherManager(db)

    # List existing publishers
    publishers = manager.list_publishers()
    print_publisher_table(publishers)

    # Generate template
    manager.generate_signup_template()

    db.close()
