#!/usr/bin/env python
"""
Test Firebase authentication workflow.

This script tests the Firebase authentication workflow by:
1. Generating a test token
2. Verifying the token structure
3. Testing the authentication endpoints

For development testing only.
"""

import argparse
import json
import sys
from typing import Any, Dict, Optional

try:
    import requests
except ImportError:
    print("Requests module not found. Install it with: pip install requests")
    sys.exit(1)

try:
    from scripts.generate_test_token import generate_firebase_like_token
except ImportError:
    print(
        "Error: Could not import generate_firebase_like_token. Run this script from the project root."
    )
    sys.exit(1)


# Default values
DEFAULT_EMAIL = "test@example.com"
DEFAULT_USER_ID = "test-firebase-uid-1234567890"
DEFAULT_API_URL = "http://localhost:8000/api/v1"
DEFAULT_SECRET = "dev-testing-secret-key"


def test_token_verification(
    api_url: str, token: str, verbose: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Test token verification endpoint.

    Args:
        api_url: Base API URL
        token: Firebase token to verify
        verbose: Whether to print detailed results

    Returns:
        Dict: Verification response if successful, None otherwise
    """
    print("\n=== Testing Token Verification ===")

    url = f"{api_url}/auth/firebase/verify-token"

    try:
        response = requests.post(
            url, json={"id_token": token}, headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Token verification successful!")

            if verbose:
                print("\nToken details:")
                print(json.dumps(result, indent=2))
            else:
                print(f"Token length: {result.get('token_length')}")
                print(f"Verification status: {result.get('verification_status')}")

                firebase_verification = result.get("firebase_verification", {})
                if (
                    firebase_verification
                    and firebase_verification.get("status") == "success"
                ):
                    print(f"UID: {firebase_verification.get('uid')}")
                    print(f"Email: {firebase_verification.get('email')}")
                else:
                    error = (
                        firebase_verification.get("error")
                        if firebase_verification
                        else "Unknown error"
                    )
                    print(f"Firebase verification failed: {error}")

            return result
        else:
            print(f"❌ Token verification failed with status {response.status_code}")
            print(f"Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error testing token verification: {str(e)}")
        return None


def test_firebase_login(
    api_url: str, token: str, verbose: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Test Firebase login endpoint.

    Args:
        api_url: Base API URL
        token: Firebase token to use for login
        verbose: Whether to print detailed results

    Returns:
        Dict: Login response if successful, None otherwise
    """
    print("\n=== Testing Firebase Login ===")

    url = f"{api_url}/auth/firebase/login"

    try:
        response = requests.post(
            url, json={"id_token": token}, headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Firebase login successful!")

            if verbose:
                print("\nLogin response:")
                print(json.dumps(result, indent=2))
            else:
                user = result.get("user", {})
                print(f"User ID: {user.get('id')}")
                print(f"Email: {user.get('email')}")
                print(f"Username: {user.get('username')}")
                print(f"Access token received: {result.get('access_token')[:20]}...")

            return result
        else:
            print(f"❌ Firebase login failed with status {response.status_code}")
            print(f"Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error testing Firebase login: {str(e)}")
        return None


def test_authenticated_endpoint(
    api_url: str, access_token: str, verbose: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Test authenticated endpoint using the access token.

    Args:
        api_url: Base API URL
        access_token: JWT access token from login
        verbose: Whether to print detailed results

    Returns:
        Dict: Response if successful, None otherwise
    """
    print("\n=== Testing Authenticated Endpoint ===")

    url = f"{api_url}/auth/me"

    try:
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Authenticated request successful!")

            if verbose:
                print("\nUser data:")
                print(json.dumps(result, indent=2))
            else:
                print(f"User ID: {result.get('id')}")
                print(f"Email: {result.get('email')}")
                print(f"Username: {result.get('username')}")
                print(f"Auth provider: {result.get('auth_provider')}")

            return result
        else:
            print(f"❌ Authenticated request failed with status {response.status_code}")
            print(f"Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error testing authenticated endpoint: {str(e)}")
        return None


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Test Firebase authentication workflow"
    )
    parser.add_argument(
        "--email",
        default=DEFAULT_EMAIL,
        help=f"User email address (default: {DEFAULT_EMAIL})",
    )
    parser.add_argument(
        "--user-id",
        default=DEFAULT_USER_ID,
        help=f"User ID (default: {DEFAULT_USER_ID})",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"Base API URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--secret",
        default=DEFAULT_SECRET,
        help=f"Secret key for signing (default: {DEFAULT_SECRET})",
    )
    parser.add_argument("--verbose", action="store_true", help="Print detailed results")
    parser.add_argument(
        "--skip-verification", action="store_true", help="Skip token verification test"
    )
    parser.add_argument(
        "--skip-login", action="store_true", help="Skip Firebase login test"
    )
    parser.add_argument(
        "--token", help="Use an existing token instead of generating one"
    )

    args = parser.parse_args()

    print("🔥 Firebase Authentication Test 🔥\n")

    # Generate or use existing token
    token = args.token
    if not token:
        print(f"Generating test token for {args.email}...")
        token = generate_firebase_like_token(
            args.email, args.user_id, 3600, args.secret  # 1 hour expiry
        )
        print(f"Token generated (first 40 chars): {token[:40]}...\n")
    else:
        print(f"Using provided token: {token[:20]}...\n")

    # Run the tests
    login_result = None

    if not args.skip_verification:
        test_token_verification(args.api_url, token, args.verbose)

    if not args.skip_login:
        login_result = test_firebase_login(args.api_url, token, args.verbose)

        if login_result and login_result.get("access_token"):
            access_token = login_result.get("access_token")
            test_authenticated_endpoint(args.api_url, access_token, args.verbose)

    print("\n✨ Test completed ✨")


if __name__ == "__main__":
    main()
