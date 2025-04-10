#!/usr/bin/env python
"""Script to check if AWS S3 and CloudFront settings are properly loaded."""

import os
import sys
from pathlib import Path

# Add parent directory to path so we can import project modules
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


def check_storage_settings():
    """Check if AWS S3 and CloudFront settings are properly loaded."""
    from config.settings import settings
    from utils.storage import get_storage_provider

    print("Checking Storage Settings:")
    print(f"  Provider: {settings.storage.provider}")
    print(f"  AWS Bucket: {settings.storage.aws_bucket}")
    print(f"  AWS Region: {settings.storage.aws_region}")
    print(
        f"  AWS Access Key: {settings.storage.aws_access_key[:5]}..."
        if settings.storage.aws_access_key
        else "None"
    )
    print(
        f"  AWS Secret Key: {settings.storage.aws_secret_key[:5]}..."
        if settings.storage.aws_secret_key
        else "None"
    )
    print(f"  CloudFront Enabled: {settings.storage.cloudfront_enabled}")
    print(f"  CloudFront Domain: {settings.storage.cloudfront_domain}")

    # Test getting a storage provider
    provider = get_storage_provider()
    print(f"\nStorage Provider: {type(provider).__name__}")

    if hasattr(provider, "bucket"):
        print(f"  S3 Bucket: {provider.bucket}")

    if hasattr(provider, "cloudfront_domain"):
        print(f"  CloudFront Domain: {provider.cloudfront_domain}")

    # Generate an example URL
    example_key = f"{settings.storage.profile_pictures_path}/example.jpg"
    example_url = provider.get_url(example_key)
    print(f"\nExample URL: {example_url}")

    if "cloudfront.net" in str(example_url):
        print("SUCCESS: CloudFront is properly configured and being used for URLs.")
    elif "s3.amazonaws.com" in str(example_url):
        print("NOTE: S3 direct URL is being used instead of CloudFront.")
    else:
        print("WARNING: URL doesn't appear to be using S3 or CloudFront.")


if __name__ == "__main__":
    check_storage_settings()
