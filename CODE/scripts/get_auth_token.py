#!/usr/bin/env python3
"""
Script to get Auth0 access token for testing.

Usage:
    python scripts/get_auth_token.py

Requirements:
    - Set AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET in .env file
    - Or pass them as command line arguments
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def get_token(domain: str, client_id: str, client_secret: str, audience: str):
    """Get access token from Auth0."""

    url = f"https://{domain}/oauth/token"

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": audience,
        "grant_type": "client_credentials"
    }

    headers = {
        "content-type": "application/json"
    }

    print(f"🔐 Requesting token from Auth0...")
    print(f"   Domain: {domain}")
    print(f"   Audience: {audience}")
    print()

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        access_token = data.get("access_token")
        expires_in = data.get("expires_in")

        print("✅ Token received successfully!")
        print()
        print("=" * 80)
        print("ACCESS TOKEN:")
        print("=" * 80)
        print(access_token)
        print("=" * 80)
        print()
        print(f"⏰ Token expires in: {expires_in} seconds ({expires_in // 3600} hours)")
        print()
        print("📋 To use this token, add it to your requests:")
        print(f'   curl -H "Authorization: Bearer {access_token}" http://localhost:8000/users/me')
        print()

        return access_token

    except requests.exceptions.HTTPError as e:
        print(f"❌ Error: {e}")
        print(f"   Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Get credentials from environment or command line
    domain = os.getenv("AUTH0_DOMAIN", "dev-eex6fdnnmp2ps746.us.auth0.com")
    audience = os.getenv("AUTH0_API_AUDIENCE", "https://study-planning-api")

    # Client credentials need to be set
    client_id = os.getenv("AUTH0_CLIENT_ID")
    client_secret = os.getenv("AUTH0_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("❌ Error: AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET must be set")
        print()
        print("To get these values:")
        print("1. Go to Auth0 Dashboard > Applications > Applications")
        print("2. Click on your application")
        print("3. Copy the Client ID and Client Secret")
        print()
        print("Then set them as environment variables:")
        print("   export AUTH0_CLIENT_ID='your-client-id'")
        print("   export AUTH0_CLIENT_SECRET='your-client-secret'")
        print()
        print("Or add them to CODE/.env file:")
        print("   AUTH0_CLIENT_ID=your-client-id")
        print("   AUTH0_CLIENT_SECRET=your-client-secret")
        sys.exit(1)

    get_token(domain, client_id, client_secret, audience)
