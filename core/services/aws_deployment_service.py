"""AWS deployment service for portfolio websites."""

import asyncio
import os
from datetime import datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from config.logging_config import get_logger
from config.settings import settings

from ..exceptions.base import DeploymentException
from ..models.portfolio_website import WebsiteConfig


class AWSDeploymentService:
    """Service for deploying portfolio websites to AWS S3 with CloudFront."""

    def __init__(self):
        """Initialize the AWS deployment service."""
        self.logger = get_logger(self.__class__.__name__)
        self.main_bucket_name = settings.storage.aws_bucket
        if not self.main_bucket_name:
            self.logger.error(
                "STORAGE_AWS_BUCKET setting is not configured in settings."
            )
            raise ValueError(
                "STORAGE_AWS_BUCKET setting is required for AWSDeploymentService."
            )

        try:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.storage.aws_access_key,
                aws_secret_access_key=settings.storage.aws_secret_key,
                region_name=settings.storage.aws_region,
            )
            self.cloudfront_client = boto3.client(
                "cloudfront",
                aws_access_key_id=settings.storage.aws_access_key,
                aws_secret_access_key=settings.storage.aws_secret_key,
                region_name=settings.storage.aws_region,
            )
        except NoCredentialsError:
            self.logger.error("AWS credentials not found")
            raise DeploymentException("AWS credentials not configured")
        except Exception as e:
            self.logger.error(f"Failed to initialize AWS S3/CloudFront clients: {e}")
            raise DeploymentException(
                f"Failed to initialize AWS S3/CloudFront clients: {e}"
            )

    async def deploy_website(
        self,
        subdomain: str,
        files: dict[str, Any],
        config: WebsiteConfig,
        clean_deploy: bool = False,
    ) -> dict[str, str]:
        """Deploy a portfolio website to AWS S3 and trigger CloudFront invalidation.
        Files are stored in the main S3 bucket under 'portfolios/{subdomain}/'.
        Invalidation uses the shared CloudFront distribution ID from settings.

        Args:
            subdomain: The subdomain for the website
            files: Dictionary of file paths to content
            config: Website configuration
            clean_deploy: If True, delete all existing files before uploading new ones
        """
        s3_portfolio_prefix = f"portfolios/{subdomain}"
        self.logger.info(
            f"Deploying website for {subdomain} to S3: s3://{self.main_bucket_name}/{s3_portfolio_prefix}"
            f" (clean_deploy={clean_deploy})"
        )

        if not settings.storage.cloudfront_distribution_id:
            self.logger.error(
                "CLOUDFRONT_DISTRIBUTION_ID is not configured in settings."
            )
            raise DeploymentException(
                "Shared CloudFront distribution ID is not configured."
            )

        try:
            # Clean deploy: delete all existing files first
            if clean_deploy:
                self.logger.info(
                    f"Clean deploy: deleting existing files for {subdomain}"
                )
                await self._delete_s3_objects_with_prefix(
                    self.main_bucket_name, s3_portfolio_prefix
                )

            await self._upload_files_to_s3(
                self.main_bucket_name, s3_portfolio_prefix, files
            )

            domain_name = os.getenv("VERCEL_DOMAIN_NAME", "yarba.app")
            website_url = f"https://{subdomain}.{domain_name}"

            self.logger.info(
                f"S3 upload for {subdomain} successful. Triggering CloudFront invalidation."
            )

            invalidation_paths = [f"/{s3_portfolio_prefix}/*"]
            await self._create_cloudfront_invalidation(
                distribution_id=settings.storage.cloudfront_distribution_id,
                items=invalidation_paths,
            )
            self.logger.info(
                f"CloudFront invalidation requested for {subdomain}: {invalidation_paths}"
            )

            return {
                "website_url": website_url,
                "bucket_name": self.main_bucket_name,
                "s3_path": s3_portfolio_prefix,
            }

        except Exception as e:
            self.logger.error(f"Deployment for {subdomain} failed: {e}")
            raise DeploymentException(f"Deployment failed for {subdomain}: {e}")

    async def delete_website(self, subdomain: str) -> bool:
        """Delete S3 objects for a portfolio and invalidate CloudFront cache.
        Objects are deleted from 'portfolios/{subdomain}/' in the main S3 bucket.
        """
        s3_portfolio_prefix = f"portfolios/{subdomain}"
        self.logger.info(
            f"Deleting S3 objects for {subdomain} from: s3://{self.main_bucket_name}/{s3_portfolio_prefix}"
        )

        try:
            await self._delete_s3_objects_with_prefix(
                self.main_bucket_name, s3_portfolio_prefix
            )

            if settings.storage.cloudfront_distribution_id:
                invalidation_paths = [f"/{s3_portfolio_prefix}/*"]
                await self._create_cloudfront_invalidation(
                    distribution_id=settings.storage.cloudfront_distribution_id,
                    items=invalidation_paths,
                )
                self.logger.info(
                    f"CloudFront invalidation for deleted {subdomain} paths: {invalidation_paths}"
                )
            else:
                self.logger.warning(
                    f"CLOUDFRONT_DISTRIBUTION_ID not set; skipping invalidation for deleted {subdomain}."
                )

            self.logger.info(f"S3 objects for {subdomain} deleted successfully.")
            return True

        except Exception as e:
            self.logger.error(f"Deletion of {subdomain} failed: {e}")
            return False

    async def _upload_files_to_s3(
        self, bucket_name: str, s3_path_prefix: str, files: dict[str, Any]
    ) -> None:
        """Upload website files to S3 bucket under a specific path prefix."""
        for file_path, content in files.items():
            s3_key = f"{s3_path_prefix.strip('/')}/{file_path.lstrip('/')}"
            try:
                content_type = self._get_content_type(file_path)
                # Handle binary files marked by the website generator
                if isinstance(content, dict) and content.get("binary"):
                    body = content["content"]
                else:
                    body = (
                        content.encode("utf-8") if isinstance(content, str) else content
                    )

                await asyncio.to_thread(
                    self.s3_client.put_object,
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=body,
                    ContentType=content_type,
                    CacheControl=(
                        "max-age=86400"
                        if file_path.endswith(
                            (
                                ".css",
                                ".js",
                                ".png",
                                ".jpg",
                                ".jpeg",
                                ".ico",
                                ".gltf",
                                ".bin",
                                ".webp",
                            )
                        )
                        else "max-age=3600"
                    ),
                )
                self.logger.debug(
                    f"Uploaded {file_path} to s3://{bucket_name}/{s3_key}"
                )
            except ClientError as e:
                self.logger.error(f"S3 upload failed for {file_path}: {e}")
                raise DeploymentException(f"S3 upload failed for {file_path}: {e}")

    def _get_content_type(self, file_path: str) -> str:
        """Get appropriate content type for file."""
        if file_path.endswith(".html"):
            return "text/html"
        if file_path.endswith(".css"):
            return "text/css"
        if file_path.endswith(".js"):
            return "application/javascript"
        if file_path.endswith(".json"):
            return "application/json"
        if file_path.endswith(".xml"):
            return "application/xml"
        if file_path.endswith(".txt"):
            return "text/plain"
        if file_path.endswith(".ico"):
            return "image/x-icon"
        if file_path.endswith(".png"):
            return "image/png"
        if file_path.endswith((".jpg", ".jpeg")):
            return "image/jpeg"
        if file_path.endswith(".webp"):
            return "image/webp"
        if file_path.endswith(".gltf"):
            return "model/gltf+json"
        if file_path.endswith(".bin"):
            return "application/octet-stream"
        if file_path.endswith(".svg"):
            return "image/svg+xml"
        return "application/octet-stream"

    async def _delete_s3_objects_with_prefix(
        self, bucket_name: str, prefix: str
    ) -> None:
        """Delete all S3 objects with a given prefix from the bucket."""
        try:
            objects_to_delete = []
            paginator = self.s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(
                Bucket=bucket_name, Prefix=prefix.strip("/")
            ):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        objects_to_delete.append({"Key": obj["Key"]})

            if objects_to_delete:
                self.s3_client.delete_objects(
                    Bucket=bucket_name,
                    Delete={"Objects": objects_to_delete, "Quiet": True},
                )
                self.logger.info(
                    f"{len(objects_to_delete)} S3 objects deleted with prefix '{prefix}' from bucket '{bucket_name}'."
                )
            else:
                self.logger.info(
                    f"No S3 objects found with prefix '{prefix}' in bucket '{bucket_name}' to delete."
                )
        except ClientError as e:
            self.logger.error(
                f"Failed to delete S3 objects with prefix '{prefix}' from {bucket_name}: {e}"
            )
            raise DeploymentException(
                f"S3 object deletion failed for prefix '{prefix}': {e}"
            )

    async def _create_cloudfront_invalidation(
        self, distribution_id: str, items: list[str]
    ) -> None:
        """Create a CloudFront invalidation for specified items."""
        if not distribution_id:
            self.logger.error(
                "Cannot create invalidation: CloudFront distribution ID is missing."
            )
            raise DeploymentException(
                "CloudFront distribution ID required for invalidation."
            )
        if not items:
            self.logger.warning("No items for CloudFront invalidation. Skipping.")
            return

        caller_reference = f"invalidation-{distribution_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

        formatted_items = [
            item if item.startswith("/") else f"/{item}" for item in items
        ]

        try:
            await asyncio.to_thread(
                self.cloudfront_client.create_invalidation,
                DistributionId=distribution_id,
                InvalidationBatch={
                    "Paths": {
                        "Quantity": len(formatted_items),
                        "Items": formatted_items,
                    },
                    "CallerReference": caller_reference,
                },
            )
            self.logger.info(
                f"CloudFront invalidation for {distribution_id}, paths: {formatted_items}. Ref: {caller_reference}"
            )
        except ClientError as e:
            self.logger.error(
                f"CloudFront invalidation failed for {distribution_id}: {e}"
            )
            raise DeploymentException(f"CloudFront invalidation creation failed: {e}")
