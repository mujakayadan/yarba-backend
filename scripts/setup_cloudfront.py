#!/usr/bin/env python
"""Script to set up AWS CloudFront distribution for S3 bucket."""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

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


def create_origin_access_identity(cf_client) -> Dict:
    """
    Create a CloudFront origin access identity.

    Args:
        cf_client: CloudFront client

    Returns:
        Dict: Response containing ID and S3 canonical user ID
    """
    try:
        response = cf_client.create_cloud_front_origin_access_identity(
            CloudFrontOriginAccessIdentityConfig={
                "CallerReference": f"yarba-app-{time.time()}",
                "Comment": "Origin Access Identity for Yarba App",
            }
        )

        oai_id = response["CloudFrontOriginAccessIdentity"]["Id"]
        s3_canonical_user_id = response["CloudFrontOriginAccessIdentity"][
            "S3CanonicalUserId"
        ]

        logger.info(f"Created CloudFront Origin Access Identity: {oai_id}")

        return {"id": oai_id, "s3_canonical_user_id": s3_canonical_user_id}
    except ClientError as e:
        logger.error(f"Error creating CloudFront Origin Access Identity: {str(e)}")
        sys.exit(1)


def update_bucket_policy(s3_client, bucket_name: str, oai_id: str) -> None:
    """
    Update S3 bucket policy to allow access from CloudFront OAI.

    Args:
        s3_client: S3 client
        bucket_name: S3 bucket name
        oai_id: CloudFront Origin Access Identity ID
    """
    try:
        # Get existing bucket policy
        try:
            response = s3_client.get_bucket_policy(Bucket=bucket_name)
            existing_policy = json.loads(response["Policy"])
            statements = existing_policy.get("Statement", [])
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchBucketPolicy":
                # No existing policy, create new policy document
                existing_policy = {"Version": "2012-10-17", "Statement": []}
                statements = []
            else:
                raise

        # Check if CloudFront OAI statement already exists
        oai_statement_exists = False
        for statement in statements:
            if (
                statement.get("Principal", {}).get("AWS")
                == f"arn:aws:iam::cloudfront:user/CloudFront Origin Access Identity {oai_id}"
                or statement.get("Principal", {}).get("CanonicalUser")
                == f"arn:aws:iam::cloudfront:user/CloudFront Origin Access Identity {oai_id}"
            ):
                oai_statement_exists = True
                break

        if not oai_statement_exists:
            # Create CloudFront access statement using the S3 CanonicalUser format
            cf_statement = {
                "Sid": "AllowCloudFrontOriginAccess",
                "Effect": "Allow",
                "Principal": {"Service": "cloudfront.amazonaws.com"},
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*",
                "Condition": {
                    "StringEquals": {
                        "AWS:SourceArn": "arn:aws:cloudfront::*:distribution/*"
                    }
                },
            }

            # Add CloudFront statement to policy
            statements.append(cf_statement)
            existing_policy["Statement"] = statements

            # Update bucket policy
            s3_client.put_bucket_policy(
                Bucket=bucket_name, Policy=json.dumps(existing_policy)
            )

            logger.info(
                f"Updated bucket policy for {bucket_name} to allow CloudFront access"
            )
        else:
            logger.info(
                f"Bucket policy for {bucket_name} already allows CloudFront access"
            )

    except ClientError as e:
        logger.error(f"Error updating bucket policy: {str(e)}")
        sys.exit(1)


def create_cloudfront_distribution(
    cf_client,
    bucket_name: str,
    bucket_region: str,
    oai_id: str,
    cache_behaviors: Optional[List[Dict]] = None,
    aliases: Optional[List[str]] = None,
    certificate_arn: Optional[str] = None,
    price_class: str = "PriceClass_100",
    enable_ipv6: bool = True,
) -> Dict:
    """
    Create a CloudFront distribution for an S3 bucket.

    Args:
        cf_client: CloudFront client
        bucket_name: S3 bucket name
        bucket_region: S3 bucket region
        oai_id: CloudFront Origin Access Identity ID
        cache_behaviors: Optional cache behaviors
        aliases: Optional CNAME aliases
        certificate_arn: ACM certificate ARN (required if aliases are provided)
        price_class: Price class ('PriceClass_100', 'PriceClass_200', or 'PriceClass_All')
        enable_ipv6: Whether to enable IPv6

    Returns:
        Dict: CloudFront distribution information
    """
    try:
        # Basic distribution configuration
        distribution_config = {
            "CallerReference": f"yarba-app-{time.time()}",
            "Comment": f"Yarba App S3 Distribution for {bucket_name}",
            "Enabled": True,
            "DefaultRootObject": "index.html",
            "PriceClass": price_class,
            "IsIPV6Enabled": enable_ipv6,
            # Configure the S3 origin
            "Origins": {
                "Quantity": 1,
                "Items": [
                    {
                        "Id": f"S3-{bucket_name}",
                        "DomainName": f"{bucket_name}.s3.{bucket_region}.amazonaws.com",
                        "S3OriginConfig": {
                            "OriginAccessIdentity": f"origin-access-identity/cloudfront/{oai_id}"
                        },
                    }
                ],
            },
            # Default cache behavior
            "DefaultCacheBehavior": {
                "TargetOriginId": f"S3-{bucket_name}",
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": {
                    "Quantity": 2,
                    "Items": ["GET", "HEAD"],
                    "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
                },
                "Compress": True,
                "ForwardedValues": {
                    "QueryString": False,
                    "Cookies": {"Forward": "none"},
                },
                "MinTTL": 0,
                "DefaultTTL": 86400,  # 1 day
                "MaxTTL": 31536000,  # 1 year
            },
        }

        # Add cache behaviors if provided
        if cache_behaviors:
            cache_behavior_items = []
            for behavior in cache_behaviors:
                cache_behavior_items.append(
                    {
                        "PathPattern": behavior["path_pattern"],
                        "TargetOriginId": f"S3-{bucket_name}",
                        "ViewerProtocolPolicy": "redirect-to-https",
                        "AllowedMethods": {
                            "Quantity": 2,
                            "Items": ["GET", "HEAD"],
                            "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
                        },
                        "Compress": True,
                        "ForwardedValues": {
                            "QueryString": behavior.get("forward_query_string", False),
                            "Cookies": {"Forward": "none"},
                        },
                        "MinTTL": behavior.get("min_ttl", 0),
                        "DefaultTTL": behavior.get("default_ttl", 86400),
                        "MaxTTL": behavior.get("max_ttl", 31536000),
                    }
                )

            distribution_config["CacheBehaviors"] = {
                "Quantity": len(cache_behavior_items),
                "Items": cache_behavior_items,
            }
        else:
            distribution_config["CacheBehaviors"] = {"Quantity": 0}

        # Add aliases and certificate if provided
        if aliases:
            distribution_config["Aliases"] = {
                "Quantity": len(aliases),
                "Items": aliases,
            }

            if certificate_arn:
                distribution_config["ViewerCertificate"] = {
                    "ACMCertificateArn": certificate_arn,
                    "SSLSupportMethod": "sni-only",
                    "MinimumProtocolVersion": "TLSv1.2_2021",
                }
            else:
                logger.error("Certificate ARN is required when aliases are provided")
                sys.exit(1)
        else:
            distribution_config["Aliases"] = {"Quantity": 0}

            # Use CloudFront default certificate
            distribution_config["ViewerCertificate"] = {
                "CloudFrontDefaultCertificate": True
            }

        # Create the distribution
        response = cf_client.create_distribution(DistributionConfig=distribution_config)

        distribution_id = response["Distribution"]["Id"]
        distribution_domain = response["Distribution"]["DomainName"]

        logger.info(f"Created CloudFront distribution: {distribution_id}")
        logger.info(f"CloudFront domain: {distribution_domain}")

        return {"id": distribution_id, "domain": distribution_domain}

    except ClientError as e:
        logger.error(f"Error creating CloudFront distribution: {str(e)}")
        sys.exit(1)


def create_cloudfront_key_pair(cf_client) -> Dict:
    """
    Create a CloudFront key pair for signed URLs.

    Args:
        cf_client: CloudFront client

    Returns:
        Dict: Key pair information
    """
    try:
        # Check if we're using the root user
        sts_client = boto3.client("sts")
        caller_identity = sts_client.get_caller_identity()

        # Only the root user can create CloudFront key pairs
        if ":root" not in caller_identity["Arn"]:
            logger.warning(
                "CloudFront key pairs can only be created by the AWS account root user."
            )
            logger.warning(
                "You'll need to create a CloudFront key pair manually in the AWS console."
            )
            logger.warning(
                "See: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-trusted-signers.html"
            )

            return {
                "success": False,
                "message": "CloudFront key pairs can only be created by the AWS account root user.",
            }

        # Create CloudFront key pair
        response = cf_client.create_key_pair(Name=f"yarba-app-key-{time.time()}")

        key_pair_id = response["KeyPair"]["Id"]
        private_key = response["KeyPair"]["PrivateKey"]

        # Save the private key to a file
        key_directory = Path("config/keys")
        key_directory.mkdir(parents=True, exist_ok=True)

        private_key_path = key_directory / f"cloudfront-private-key-{key_pair_id}.pem"
        with open(private_key_path, "w") as f:
            f.write(private_key)

        logger.info(f"Created CloudFront key pair: {key_pair_id}")
        logger.info(f"Private key saved to: {private_key_path}")

        return {
            "success": True,
            "key_pair_id": key_pair_id,
            "private_key_path": str(private_key_path),
        }

    except ClientError as e:
        if "Call was made as a root user" in str(e):
            logger.warning(
                "CloudFront key pairs can only be created by the AWS account root user."
            )
            logger.warning(
                "You'll need to create a CloudFront key pair manually in the AWS console."
            )
            logger.warning(
                "See: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-trusted-signers.html"
            )

            return {
                "success": False,
                "message": "CloudFront key pairs can only be created by the AWS account root user.",
            }
        else:
            logger.error(f"Error creating CloudFront key pair: {str(e)}")
            sys.exit(1)


def update_settings_file(
    domain: str,
    key_pair_id: Optional[str] = None,
    private_key_path: Optional[str] = None,
) -> None:
    """
    Update settings file with CloudFront configuration.

    Args:
        domain: CloudFront domain
        key_pair_id: CloudFront key pair ID (optional)
        private_key_path: Path to CloudFront private key (optional)
    """
    try:
        # Display settings to add
        logger.info("\nAdd the following CloudFront settings to your .env.local file:")
        logger.info("STORAGE_CLOUDFRONT_ENABLED=true")
        logger.info(f"STORAGE_CLOUDFRONT_DOMAIN={domain}")

        if key_pair_id and private_key_path:
            logger.info(f"STORAGE_CLOUDFRONT_KEY_PAIR_ID={key_pair_id}")
            logger.info(f"STORAGE_CLOUDFRONT_PRIVATE_KEY_PATH={private_key_path}")

        # Suggest restarting the application
        logger.info("\nRestart your application to apply the changes.")

    except Exception as e:
        logger.error(f"Error updating settings file: {str(e)}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Set up AWS CloudFront distribution for S3 bucket"
    )
    parser.add_argument(
        "--bucket", help="S3 bucket name", default=settings.storage.aws_bucket
    )
    parser.add_argument(
        "--region", help="AWS region", default=settings.storage.aws_region
    )
    parser.add_argument("--profile", help="AWS profile name")
    parser.add_argument("--access-key", help="AWS access key")
    parser.add_argument("--secret-key", help="AWS secret key")
    parser.add_argument(
        "--price-class", help="Price class (100, 200, or All)", default="100"
    )
    parser.add_argument("--cdn-cert-arn", help="ACM certificate ARN for custom domain")
    parser.add_argument(
        "--cname",
        help="Custom domain name (must have valid ACM certificate)",
        action="append",
    )
    parser.add_argument(
        "--create-key-pair",
        help="Create a CloudFront key pair for signed URLs",
        action="store_true",
    )

    args = parser.parse_args()

    # Map price class
    price_class_map = {
        "100": "PriceClass_100",  # US, Canada, Europe
        "200": "PriceClass_200",  # + Asia, Middle East, Africa
        "All": "PriceClass_All",  # + South America, Australia
    }
    price_class = price_class_map.get(args.price_class, "PriceClass_100")

    # Use settings if not provided
    bucket_name = args.bucket
    region = args.region

    # Create boto3 session
    session_args = {}
    if args.profile:
        session_args["profile_name"] = args.profile
    elif args.access_key and args.secret_key:
        session_args["aws_access_key_id"] = args.access_key
        session_args["aws_secret_access_key"] = args.secret_key
    elif settings.storage.aws_access_key and settings.storage.aws_secret_key:
        session_args["aws_access_key_id"] = settings.storage.aws_access_key
        session_args["aws_secret_access_key"] = settings.storage.aws_secret_key

    session = boto3.Session(**session_args)
    cf_client = session.client("cloudfront")
    s3_client = session.client("s3")

    logger.info(f"Setting up CloudFront distribution for S3 bucket: {bucket_name}")

    # 1. Create CloudFront OAI
    oai_info = create_origin_access_identity(cf_client)
    oai_id = oai_info["id"]

    # 2. Update S3 bucket policy
    update_bucket_policy(s3_client, bucket_name, oai_id)

    # 3. Create CloudFront key pair (optional)
    key_pair_info = None
    if args.create_key_pair:
        logger.info("Creating CloudFront key pair...")
        key_pair_info = create_cloudfront_key_pair(cf_client)

    # 4. Create cache behaviors for different asset types
    cache_behaviors = [
        {
            "path_pattern": f"{settings.storage.profile_pictures_path}/*",
            "min_ttl": 3600,  # 1 hour
            "default_ttl": 86400,  # 1 day
            "max_ttl": 31536000,  # 1 year
        },
        {
            "path_pattern": f"{settings.storage.signatures_path}/*",
            "min_ttl": 3600,  # 1 hour
            "default_ttl": 86400,  # 1 day
            "max_ttl": 31536000,  # 1 year
        },
        {
            "path_pattern": f"{settings.storage.resumes_path}/*",
            "min_ttl": 60,  # 1 minute
            "default_ttl": 3600,  # 1 hour
            "max_ttl": 86400,  # 1 day
        },
        {
            "path_pattern": f"{settings.storage.cover_letters_path}/*",
            "min_ttl": 60,  # 1 minute
            "default_ttl": 3600,  # 1 hour
            "max_ttl": 86400,  # 1 day
        },
    ]

    # 5. Create CloudFront distribution
    distribution_info = create_cloudfront_distribution(
        cf_client,
        bucket_name,
        region,
        oai_id,
        cache_behaviors=cache_behaviors,
        aliases=args.cname,
        certificate_arn=args.cdn_cert_arn,
        price_class=price_class,
    )

    # 6. Update settings file with CloudFront configuration
    if key_pair_info and key_pair_info.get("success"):
        update_settings_file(
            distribution_info["domain"],
            key_pair_info["key_pair_id"],
            key_pair_info["private_key_path"],
        )
    else:
        update_settings_file(distribution_info["domain"])

    # 7. Success message
    logger.info(
        "\nCloudFront setup complete! Distribution may take up to 15 minutes to deploy."
    )
    logger.info(f"CloudFront Distribution ID: {distribution_info['id']}")
    logger.info(f"CloudFront Domain: {distribution_info['domain']}")

    # 8. Check for pending certificate validation
    if args.cname and args.cdn_cert_arn:
        logger.info(
            "\nTo use your custom domain, ensure your ACM certificate is validated."
        )
        logger.info(
            "If using DNS validation, add the CNAME records to your DNS configuration."
        )

    # 9. Instructions for CloudFront key pair if not created
    if args.create_key_pair and (not key_pair_info or not key_pair_info.get("success")):
        logger.info("\nTo create a CloudFront key pair manually:")
        logger.info("1. Sign in to the AWS Management Console as the root user")
        logger.info("2. Navigate to Security Credentials")
        logger.info("3. Under CloudFront key pairs, create a new key pair")
        logger.info("4. Download the private key and add it to your project")
        logger.info(
            "5. Update your .env.local file with the key pair ID and private key path"
        )


if __name__ == "__main__":
    main()
