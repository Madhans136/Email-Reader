"""
Main entry point for the Email Reader application.
Fetches and displays emails from Gmail using Composio SDK.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from email_reader import EmailReader


def load_environment():
    """
    Load environment variables from .env file.
    
    Returns:
        tuple: (api_key, base_url) or (None, None) if not found
    """
    # Try to load from .env file in the current directory
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try to load from parent directory
        parent_env_path = Path(__file__).parent.parent / '.env'
        if parent_env_path.exists():
            load_dotenv(parent_env_path)
    
    api_key = os.getenv('COMPOSIO_API_KEY')
    base_url = os.getenv('COMPOSIO_BASE_URL')
    
    return api_key, base_url


def print_email(email: dict):
    """
    Print a single email in the specified format.
    
    Args:
        email: Dictionary containing email details
    """
    subject = email.get('subject', 'N/A')
    thread_id = email.get('thread_id', 'N/A')
    body = email.get('body', 'N/A')
    
    print(f"Subject: {subject}")
    print(f"Thread ID: {thread_id}")
    print(f"Body: {body}")
    print("------------")


def main():
    """Main function to run the email reader."""
    
    print("=" * 50)
    print("Gmail Email Reader using Composio SDK")
    print("=" * 50)
    print()
    
    # Load environment variables
    api_key, base_url = load_environment()
    
    # Validate credentials
    if not api_key:
        print("Error: COMPOSIO_API_KEY not found in environment variables.")
        print("Please create a .env file with your API key.")
        print("See .env.example for reference.")
        sys.exit(1)
    
    if not base_url:
        print("Warning: COMPOSIO_BASE_URL not found, using default.")
        base_url = "https://agent.composio.io"
    
    print(f"Connecting to Composio server...")
    print(f"Base URL: {base_url}")
    print()
    
    try:
        # Initialize email reader
        reader = EmailReader(api_key=api_key, base_url=base_url)
        
        # Fetch emails using the new SDK
        print("Fetching latest 5 emails from Gmail...")
        print()
        
        emails = reader.read_emails(max_results=5)
        
        # Handle no emails case
        if not emails:
            print("No emails found.")
            print("This might be due to:")
            print("- No emails in your Gmail account")
            print("- API connection issues")
            print("- Gmail integration not configured")
            sys.exit(0)
        
        # Print emails in the specified format
        print(f"Found {len(emails)} email(s):")
        print("-" * 50)
        for email in emails:
            print_email(email)
        
        print()
        print("Email fetching completed successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print()
        print("Common issues:")
        print("- Invalid API key")
        print("- Network connection problems")
        print("- Composio server unavailable")
        print("- Gmail not connected to Composio")
        sys.exit(1)


if __name__ == "__main__":
    main()
