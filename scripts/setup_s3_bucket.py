#!/usr/bin/env python
"""Script to set up an AWS S3 bucket for profile pictures storage."""

import argparse
import logging
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Add parent directory to path so we can import project modules
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def create_s3_bucket(
    bucket_name, region, access_key=None, secret_key=None, make_public=False
):
    """
    Create an S3 bucket for profile picture storage.

    Args:
        bucket_name: Name of the bucket to create
        region: AWS region where the bucket will be created
        access_key: AWS access key (optional, will use AWS CLI credentials if not provided)
        secret_key: AWS secret key (optional, will use AWS CLI credentials if not provided)
        make_public: Whether to try to make the bucket publicly accessible (may fail if account has Block Public Access enabled)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create the S3 client
        session_args = {}
        if access_key and secret_key:
            session_args["aws_access_key_id"] = access_key
            session_args["aws_secret_access_key"] = secret_key

        session = boto3.Session(**session_args)
        s3_client = session.client("s3", region_name=region)

        # Check if bucket already exists
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"Bucket {bucket_name} already exists")

            # Continue with configuration
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                # Bucket doesn't exist, proceed with creation
                logger.info(f"Creating new bucket: {bucket_name}")
                try:
                    # Create bucket with the appropriate region configuration
                    if region == "us-east-1":
                        # Special case for us-east-1
                        s3_client.create_bucket(
                            Bucket=bucket_name, ACL="private"  # Start with private
                        )
                    else:
                        # Other regions need a location constraint
                        s3_client.create_bucket(
                            Bucket=bucket_name,
                            CreateBucketConfiguration={"LocationConstraint": region},
                            ACL="private",  # Start with private
                        )

                    logger.info(
                        f"Successfully created bucket: {bucket_name} in region: {region}"
                    )
                except Exception as bucket_e:
                    logger.error(f"Error creating bucket: {str(bucket_e)}")
                    return False
            else:
                logger.error(f"Error checking bucket: {str(e)}")
                return False

        if make_public:
            try:
                # Try to set public read access policy
                logger.info("Attempting to set public read access...")

                # Set bucket policy to allow public read access to objects
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "PublicReadForGetBucketObjects",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": "s3:GetObject",
                            "Resource": f"arn:aws:s3:::{bucket_name}/*",
                        }
                    ],
                }

                # Convert policy to JSON string
                import json

                policy_json = json.dumps(policy)

                # Apply policy to bucket
                s3_client.put_bucket_policy(Bucket=bucket_name, Policy=policy_json)

                logger.info(f"Applied public read policy to bucket: {bucket_name}")
                logger.info(
                    "Your bucket is configured for public access. Objects can be accessed directly via URL."
                )
            except ClientError as policy_error:
                if "BlockPublicPolicy" in str(policy_error):
                    logger.warning(
                        "Block Public Access settings are enabled on your account. Cannot set public policy."
                    )
                    logger.info(
                        "This is fine - we'll use pre-signed URLs for accessing objects instead."
                    )
                else:
                    logger.warning(f"Could not set public policy: {str(policy_error)}")
        else:
            logger.info(
                "Skipping public access configuration. Will use pre-signed URLs."
            )

        # Set CORS configuration to allow web access (doesn't require public access)
        try:
            cors_config = {
                "CORSRules": [
                    {
                        "AllowedHeaders": ["*"],
                        "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
                        "AllowedOrigins": ["*"],
                        "ExposeHeaders": ["ETag", "Content-Length"],
                        "MaxAgeSeconds": 3000,
                    }
                ]
            }

            s3_client.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_config)

            logger.info(f"Applied CORS configuration to bucket: {bucket_name}")
        except Exception as cors_error:
            logger.warning(f"Could not set CORS: {str(cors_error)}")

        # Generate and display a pre-signed URL example
        try:
            test_url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": "profile_pictures/example.jpg"},
                ExpiresIn=3600,  # 1 hour
            )
            logger.info(f"Example pre-signed URL: {test_url}")
            logger.info(
                "Pre-signed URLs will work even with private buckets and expire after the specified time."
            )
        except Exception as url_error:
            logger.warning(
                f"Could not generate example pre-signed URL: {str(url_error)}"
            )

        return True

    except Exception as e:
        logger.error(f"Error during bucket setup: {str(e)}")
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Set up AWS S3 bucket for profile pictures"
    )
    parser.add_argument(
        "--bucket", help="S3 bucket name", default=settings.storage.aws_bucket
    )
    parser.add_argument(
        "--region", help="AWS region", default=settings.storage.aws_region
    )
    parser.add_argument("--access-key", help="AWS access key (optional)")
    parser.add_argument("--secret-key", help="AWS secret key (optional)")
    parser.add_argument(
        "--public",
        action="store_true",
        help="Try to make bucket public (may not work if account has Block Public Access)",
    )

    args = parser.parse_args()

    # Use settings if not provided
    bucket_name = args.bucket
    region = args.region
    access_key = args.access_key or settings.storage.aws_access_key
    secret_key = args.secret_key or settings.storage.aws_secret_key
    make_public = args.public

    logger.info(f"Setting up S3 bucket: {bucket_name} in region: {region}")
    success = create_s3_bucket(bucket_name, region, access_key, secret_key, make_public)

    if success:
        logger.info("S3 bucket setup complete!")
        logger.info("Update your .env.local file with the following settings:")
        logger.info(f"STORAGE_PROVIDER=aws_s3")
        logger.info(f"STORAGE_AWS_BUCKET={bucket_name}")
        logger.info(f"STORAGE_AWS_REGION={region}")

        if not (access_key and secret_key):
            logger.info("STORAGE_AWS_ACCESS_KEY=your_access_key")
            logger.info("STORAGE_AWS_SECRET_KEY=your_secret_key")

        if not make_public or "BlockPublicPolicy" in success:
            logger.info("STORAGE_AWS_USE_PRESIGNED_URLS=true")
            logger.info("STORAGE_AWS_PRESIGNED_URL_EXPIRY=3600")
    else:
        logger.error("Failed to set up S3 bucket")
        sys.exit(1)


if __name__ == "__main__":
    main()
