"""
Newsletter Analyst - Email Analysis Tool

This package provides tools for analyzing newsletter onboarding emails using the Gmail API.
"""

from .gmail_client import GmailClient
from .email_processor import EmailProcessor
from .database import NewsletterDatabase
from .publisher_manager import PublisherManager

__version__ = '0.1.0'
__all__ = ['GmailClient', 'EmailProcessor', 'NewsletterDatabase', 'PublisherManager']
