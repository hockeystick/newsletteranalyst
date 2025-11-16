"""
LLM Analysis Module

This module uses Anthropic's Claude API to analyze newsletter onboarding emails
and extract structured information about their content, purpose, and effectiveness.
"""

import os
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

import anthropic
from dotenv import load_dotenv


class EmailAnalyzer:
    """Analyze newsletter emails using Claude API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the email analyzer.

        Args:
            api_key: Anthropic API key (if not provided, loads from env)
            model: Claude model to use (default: claude-3-5-sonnet-20241022)
        """
        load_dotenv()

        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not provided. Set ANTHROPIC_API_KEY in .env "
                "or pass api_key to constructor."
            )

        self.model = model
        self.client = anthropic.Anthropic(api_key=self.api_key)

        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0

        # Rate limiting
        self.last_request_time = 0
        self.min_delay_seconds = 1.0  # Minimum delay between requests

    def _build_analysis_prompt(self, subject: str, body_text: str, sender: str) -> str:
        """
        Build the analysis prompt for Claude.

        Args:
            subject: Email subject line
            body_text: Email body (plain text)
            sender: Email sender

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert at analyzing newsletter onboarding emails. Analyze the following email and extract structured information about it.

EMAIL DETAILS:
Sender: {sender}
Subject: {subject}

EMAIL CONTENT:
{body_text[:4000]}

Please analyze this email and provide a structured analysis in JSON format with the following fields:

1. primary_purpose: A concise statement (1-2 sentences) of the email's main purpose
2. value_propositions: A list of value propositions or benefits mentioned (array of strings)
3. calls_to_action: A list of all CTAs in the email (array of objects with 'text' and 'type' fields)
4. personalization_elements: List of personalization techniques used (e.g., name, location, interests)
5. tone: Classification of the email's tone (e.g., professional, casual, friendly, urgent, educational)
6. frequency_expectations: Any mention of email frequency or what to expect next (string or null)
7. notable_elements: Any standout features, techniques, or unique elements (array of strings)
8. effectiveness_score: Your assessment of email effectiveness on a scale of 1-10, with brief reasoning
9. key_takeaways: 2-3 actionable insights or lessons from this email (array of strings)

Respond ONLY with valid JSON. Do not include any text before or after the JSON object."""

        return prompt

    def _wait_for_rate_limit(self):
        """Implement rate limiting by waiting if needed."""
        if self.last_request_time > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_delay_seconds:
                wait_time = self.min_delay_seconds - elapsed
                time.sleep(wait_time)

        self.last_request_time = time.time()

    def analyze_email(
        self,
        subject: str,
        body_text: str,
        sender: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single email using Claude API.

        Args:
            subject: Email subject line
            body_text: Email body (plain text)
            sender: Email sender
            metadata: Optional metadata about the email

        Returns:
            Dictionary containing analysis results
        """
        # Rate limiting
        self._wait_for_rate_limit()

        # Build prompt
        prompt = self._build_analysis_prompt(subject, body_text, sender)

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.2,  # Lower temperature for more consistent structured output
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Track usage
            self.total_input_tokens += response.usage.input_tokens
            self.total_output_tokens += response.usage.output_tokens
            self.total_requests += 1

            # Extract and parse response
            response_text = response.content[0].text.strip()

            # Try to parse JSON
            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                # If response isn't pure JSON, try to extract JSON from it
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    analysis = json.loads(json_str)
                else:
                    raise ValueError("Could not parse JSON from response")

            # Add usage metadata
            analysis['_metadata'] = {
                'model': self.model,
                'input_tokens': response.usage.input_tokens,
                'output_tokens': response.usage.output_tokens,
                'analyzed_at': datetime.now().isoformat(),
                'subject': subject,
                'sender': sender
            }

            return analysis

        except anthropic.APIError as e:
            print(f"Anthropic API error: {e}")
            raise
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response text: {response_text[:500]}")
            raise
        except Exception as e:
            print(f"Error analyzing email: {e}")
            raise

    def analyze_email_batch(
        self,
        emails: List[Dict[str, Any]],
        delay_seconds: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze a batch of emails.

        Args:
            emails: List of email dictionaries with 'subject', 'body_text', 'sender'
            delay_seconds: Optional custom delay between requests

        Returns:
            List of analysis results
        """
        if delay_seconds is not None:
            original_delay = self.min_delay_seconds
            self.min_delay_seconds = delay_seconds

        results = []

        for i, email in enumerate(emails):
            print(f"Analyzing email {i+1}/{len(emails)}: {email.get('subject', 'N/A')[:50]}...")

            try:
                analysis = self.analyze_email(
                    subject=email.get('subject', ''),
                    body_text=email.get('body_text', ''),
                    sender=email.get('sender', ''),
                    metadata=email.get('metadata', {})
                )

                # Include email ID if provided
                if 'email_id' in email:
                    analysis['email_id'] = email['email_id']

                results.append(analysis)

            except Exception as e:
                print(f"  ✗ Error: {e}")
                results.append({
                    'email_id': email.get('email_id'),
                    'error': str(e),
                    'analyzed_at': datetime.now().isoformat()
                })

        if delay_seconds is not None:
            self.min_delay_seconds = original_delay

        return results

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics and cost estimates.

        Returns:
            Dictionary with usage stats and cost estimates
        """
        # Claude pricing (as of Jan 2025, approximate)
        # Sonnet: $3/MTok input, $15/MTok output
        input_cost_per_token = 3.0 / 1_000_000
        output_cost_per_token = 15.0 / 1_000_000

        total_cost = (
            self.total_input_tokens * input_cost_per_token +
            self.total_output_tokens * output_cost_per_token
        )

        return {
            'total_requests': self.total_requests,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_input_tokens + self.total_output_tokens,
            'estimated_cost_usd': round(total_cost, 4),
            'average_input_tokens': round(self.total_input_tokens / max(self.total_requests, 1), 1),
            'average_output_tokens': round(self.total_output_tokens / max(self.total_requests, 1), 1),
            'model': self.model
        }

    def print_usage_stats(self):
        """Print usage statistics in a formatted way."""
        stats = self.get_usage_stats()

        print("\n" + "=" * 70)
        print("Claude API Usage Statistics")
        print("=" * 70)
        print(f"Model: {stats['model']}")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Total Tokens: {stats['total_tokens']:,}")
        print(f"  Input Tokens: {stats['total_input_tokens']:,}")
        print(f"  Output Tokens: {stats['total_output_tokens']:,}")
        print(f"Average per Request:")
        print(f"  Input: {stats['average_input_tokens']:.1f} tokens")
        print(f"  Output: {stats['average_output_tokens']:.1f} tokens")
        print(f"\nEstimated Cost: ${stats['estimated_cost_usd']:.4f} USD")
        print("=" * 70 + "\n")


def validate_analysis(analysis: Dict[str, Any]) -> bool:
    """
    Validate that analysis has required fields.

    Args:
        analysis: Analysis dictionary

    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        'primary_purpose',
        'value_propositions',
        'calls_to_action',
        'personalization_elements',
        'tone',
        'effectiveness_score'
    ]

    for field in required_fields:
        if field not in analysis:
            return False

    return True


if __name__ == '__main__':
    # Example usage
    print("Email Analyzer - Test Mode\n")

    # Sample email for testing
    sample_email = {
        'subject': 'Welcome to Tech Weekly!',
        'body_text': """Hi there!

Welcome to Tech Weekly - your source for the latest in technology news and insights.

Here's what you can expect:
- Weekly roundup of tech news every Monday
- Deep dives into emerging technologies
- Exclusive interviews with industry leaders

Get started by checking out our latest issue: https://techweekly.com/latest

Questions? Just reply to this email.

Best,
The Tech Weekly Team
""",
        'sender': 'Tech Weekly <hello@techweekly.com>'
    }

    try:
        analyzer = EmailAnalyzer()

        print("Analyzing sample email...")
        result = analyzer.analyze_email(
            subject=sample_email['subject'],
            body_text=sample_email['body_text'],
            sender=sample_email['sender']
        )

        print("\nAnalysis Result:")
        print(json.dumps(result, indent=2))

        analyzer.print_usage_stats()

    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease set ANTHROPIC_API_KEY in your .env file")
    except Exception as e:
        print(f"Error: {e}")
