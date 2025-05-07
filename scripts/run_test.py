#!/usr/bin/env python
"""
Run test_preferences.py with specific MongoDB connection parameters.

This script sets MongoDB environment variables and then runs test_preferences.py.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main():
    """Run test_preferences.py with the MongoDB URI."""
    parser = argparse.ArgumentParser(
        description="Run test_preferences.py with MongoDB connection parameters"
    )
    parser.add_argument(
        "--uri", dest="mongodb_uri", required=True, help="MongoDB URI (required)"
    )
    parser.add_argument(
        "--db",
        dest="mongodb_db",
        default="rbt",
        help="MongoDB database name (default: rbt)",
    )
    parser.add_argument(
        "--user-id",
        dest="user_id",
        help="Test user ID (overrides settings.test_user_id)",
    )

    args = parser.parse_args()

    # Get project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Run test_preferences.py directly with environment variables
    test_script = project_root / "debug" / "test_preferences.py"
    if not test_script.exists():
        print(f"Error: Test script not found at {test_script}")
        return 1

    # Set environment variables for the subprocess
    env = os.environ.copy()
    env["MONGODB_URI"] = args.mongodb_uri
    env["MONGODB_DATABASE"] = args.mongodb_db

    # Prepare a safe display version of the URI (without credentials)
    display_uri = args.mongodb_uri
    if "@" in display_uri:
        display_uri = display_uri.split("@")[-1]

    print(f"Running test with:")
    print(f"  - Database: {args.mongodb_db}")
    print(f"  - MongoDB Server: {display_uri}")
    if args.user_id:
        print(f"  - Test User ID: {args.user_id}")
        env["TEST_USER_ID"] = args.user_id

    print(f"\nStarting test script: {test_script}")
    print("=" * 60)

    # Run the script with the environment variables
    result = subprocess.run([sys.executable, str(test_script)], env=env, check=False)

    print("=" * 60)
    if result.returncode == 0:
        print("Test completed successfully!")
    else:
        print(f"Test failed with exit code: {result.returncode}")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
