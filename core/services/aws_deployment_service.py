"""AWS deployment service for portfolio websites."""

import asyncio
import json
from typing import Dict, Optional

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
        self.main_bucket_name = (
            settings.storage.aws_bucket
        )  # Changed back to aws_bucket
        if not self.main_bucket_name:
            self.logger.error(
                "STORAGE_AWS_BUCKET setting is not configured in settings."
            )  # Updated error message to reflect env var
            raise ValueError(
                "STORAGE_AWS_BUCKET setting is required for AWSDeploymentService."
            )  # Updated error message

        # Initialize AWS clients
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

            self.route53_client = boto3.client(
                "route53",
                aws_access_key_id=settings.storage.aws_access_key,
                aws_secret_access_key=settings.storage.aws_secret_key,
                region_name=settings.storage.aws_region,
            )

            self.sts_client = boto3.client(
                "sts",
                aws_access_key_id=settings.storage.aws_access_key,
                aws_secret_access_key=settings.storage.aws_secret_key,
                region_name=settings.storage.aws_region,  # STS is global but region can be specified
            )

        except NoCredentialsError:
            self.logger.error("AWS credentials not found")
            raise DeploymentException("AWS credentials not configured")
        except Exception as e:
            self.logger.error(f"Failed to initialize AWS clients: {e}")
            raise DeploymentException(f"Failed to initialize AWS clients: {e}")

    async def deploy_website(
        self,
        subdomain: str,
        files: Dict[str, str],
        config: WebsiteConfig,
    ) -> Dict[str, str]:
        """
        Deploy a portfolio website to AWS.
        Files will be stored in the main bucket under 'portfolios/{subdomain}/'.

        Args:
            subdomain: Subdomain for the website
            files: Dictionary of file paths to file content
            config: Website configuration

        Returns:
            Dict containing deployment information

        Raises:
            DeploymentException: If deployment fails
        """
        s3_portfolio_prefix = f"portfolios/{subdomain}"
        self.logger.info(
            f"Deploying website for subdomain {subdomain} to S3 path: s3://{self.main_bucket_name}/{s3_portfolio_prefix}"
        )

        try:
            # Bucket creation is no longer done per portfolio. Main bucket is used.
            # await self._create_s3_bucket(bucket_name) # REMOVED

            # Upload files to S3 under the specific prefix
            await self._upload_files_to_s3(
                self.main_bucket_name, s3_portfolio_prefix, files
            )

            # The _configure_s3_website_hosting method's role changes.
            # It previously tried to set public bucket policies and bucket website config.
            # For a shared bucket and OAC, these are not desirable or are handled differently.
            # The primary concern now is the OAC-specific bucket policy,
            # which is handled after CloudFront distribution creation.
            # We can remove or significantly simplify _configure_s3_website_hosting.
            # For now, let's remove its call. If specific shared bucket configurations
            # are needed, they should be handled carefully.
            # s3_config_status = await self._configure_s3_website_hosting(self.main_bucket_name)
            # if not s3_config_status["success"]:
            #     self.logger.error(f"Main S3 bucket configuration check failed: {s3_config_status['message']}")
            #     raise DeploymentException(f"Failed to configure main S3 bucket: {s3_config_status['message']}")
            # else:
            #     self.logger.info(f"Main S3 bucket configuration for {self.main_bucket_name} checked. Status: {s3_config_status['message']}")

            # Create/update CloudFront distribution
            # Pass the main_bucket_name and the specific s3_portfolio_prefix (or just subdomain for origin path construction)
            distribution_info = await self._create_cloudfront_distribution(
                bucket_name_for_origin=self.main_bucket_name,  # This is the actual S3 bucket
                subdomain=subdomain,  # Used for OAC naming, Aliases, and OriginPath construction
                s3_origin_path=f"/{s3_portfolio_prefix}",  # CloudFront Origin Path
            )

            # if settings.storage.aws_acm_certificate_arn and not config.custom_domain:
            #     await self._setup_route53_subdomain(subdomain, distribution_info["domain_name"])
            # elif not settings.storage.aws_acm_certificate_arn:
            #     self.logger.info(f"Skipping Route 53 setup for {subdomain} as no ACM certificate was provided or DNS is managed elsewhere. Website will be on CloudFront domain.")

            website_url = f"https://{subdomain}.yarba.app"  # Assume CNAME will be manually set up or handled by other means
            # Fallback to CloudFront domain if direct subdomain access isn't the primary URL for some reason
            # website_url = distribution_info["website_url"] # This might be the direct CF domain or the alias if Route53 was managed by script

            self.logger.info(
                f"Successfully deployed website. It should be accessible at {website_url} (after DNS propagation if CNAME is set externally) or directly via {distribution_info['domain_name']}"
            )

            # Create CloudFront invalidation
            await self._create_cloudfront_invalidation(
                distribution_info["distribution_id"]
            )

            return {
                "website_url": website_url,
                "bucket_name": self.main_bucket_name,  # Reports main bucket
                "s3_path": s3_portfolio_prefix,  # Reports path within main bucket
                "distribution_id": distribution_info["distribution_id"],
                "cloudfront_domain": distribution_info["domain_name"],
                "distribution_arn": distribution_info["distribution_arn"],
            }

        except Exception as e:
            self.logger.error(
                f"Failed to deploy website for subdomain {subdomain}: {e}"
            )
            raise DeploymentException(f"Deployment failed: {e}")

    async def delete_website(self, subdomain: str) -> bool:
        """
        Delete a portfolio website and its AWS resources.
        This will delete files from 'portfolios/{subdomain}/' in the main S3 bucket.

        Args:
            subdomain: Subdomain of the website to delete

        Returns:
            bool: True if deletion was successful
        """
        s3_portfolio_prefix = f"portfolios/{subdomain}"
        self.logger.info(
            f"Deleting website for subdomain {subdomain} from S3 path: s3://{self.main_bucket_name}/{s3_portfolio_prefix}"
        )
        try:
            # Delete CloudFront distribution
            await self._delete_cloudfront_distribution(
                subdomain
            )  # subdomain is enough to find distribution

            # Delete Route 53 record (if applicable)
            await self._delete_route53_subdomain(subdomain)

            # Empty and delete S3 "folder" (objects with prefix)
            # _delete_s3_bucket needs to be adapted to delete objects by prefix, not the bucket itself
            await self._delete_s3_objects_with_prefix(
                self.main_bucket_name, s3_portfolio_prefix
            )

            self.logger.info(f"Successfully deleted website resources for {subdomain}")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to delete website for subdomain {subdomain}: {e}"
            )
            return False  # Or re-raise as DeploymentException depending on desired error handling

    async def _upload_files_to_s3(
        self, bucket_name: str, s3_path_prefix: str, files: Dict[str, str]
    ) -> None:
        """Upload website files to S3 bucket under a specific path prefix."""
        for file_path, content in files.items():
            s3_key = f"{s3_path_prefix}/{file_path.lstrip('/')}"
            try:
                # Determine content type
                content_type = self._get_content_type(file_path)

                # Upload file
                self.s3_client.put_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=content.encode("utf-8"),
                    ContentType=content_type,
                    CacheControl=(
                        "max-age=86400"
                        if file_path.endswith((".css", ".js", ".png", ".jpg", ".ico"))
                        else "max-age=3600"
                    ),
                )

                self.logger.debug(f"Uploaded {file_path} to S3")

            except ClientError as e:
                self.logger.error(f"Failed to upload {file_path} to S3: {e}")
                raise DeploymentException(f"Failed to upload file {file_path}: {e}")

    def _get_content_type(self, file_path: str) -> str:
        """Get appropriate content type for file."""
        if file_path.endswith(".html"):
            return "text/html"
        elif file_path.endswith(".css"):
            return "text/css"
        elif file_path.endswith(".js"):
            return "application/javascript"
        elif file_path.endswith(".json"):
            return "application/json"
        elif file_path.endswith(".xml"):
            return "application/xml"
        elif file_path.endswith(".txt"):
            return "text/plain"
        elif file_path.endswith(".ico"):
            return "image/x-icon"
        elif file_path.endswith((".png", ".jpg", ".jpeg")):
            return (
                "image/jpeg" if file_path.endswith((".jpg", ".jpeg")) else "image/png"
            )
        else:
            return "application/octet-stream"

    async def _configure_s3_website_hosting(self, bucket_name: str) -> dict:
        # This method's original purpose (public policy, bucket website config) is
        # largely incompatible or unnecessary with a shared bucket + OAC model.
        # Public policy is a no-go for the shared bucket.
        # Bucket-level website config might conflict if main bucket serves other content at root.
        # OAC policy is now handled by _update_s3_bucket_policy_for_oac.
        # We can simplify this to be a no-op or remove its call from deploy_website.
        self.logger.info(
            f"Skipping general S3 website hosting configuration for shared bucket {bucket_name} as OAC is used."
        )
        return {
            "success": True,
            "message": "Skipped general S3 website hosting configuration for shared bucket.",
        }

    async def _create_cloudfront_distribution(
        self, bucket_name_for_origin: str, subdomain: str, s3_origin_path: str
    ) -> Dict[str, str]:
        """Create or update CloudFront distribution with OAC, targeting a path in S3."""
        try:
            # Determine the correct S3 origin domain name
            region_to_use = (
                settings.storage.aws_region
                if settings.storage.aws_region
                else "us-east-1"
            )
            s3_origin_server_name = (
                f"{bucket_name_for_origin}.s3.{region_to_use}.amazonaws.com"
            )
            self.logger.info(
                f"Using S3 origin server name: {s3_origin_server_name}"
            )  # Added log

            existing_distribution = await self._get_existing_distribution(subdomain)

            s3_portfolio_prefix = s3_origin_path.lstrip(
                "/"
            )  # Used for S3 policy, no leading slash

            if existing_distribution:
                self.logger.info(
                    f"Found existing CloudFront distribution {existing_distribution['Id']} for {subdomain}. Verifying and updating configuration."
                )
                distribution_id = existing_distribution["Id"]
                distribution_arn = existing_distribution["ARN"]
                cloudfront_domain_name = existing_distribution[
                    "DomainName"
                ]  # Actual CF domain

                oac_name = (
                    f"{subdomain}-portfolio-OAC-{int(asyncio.get_event_loop().time())}"
                )
                try:
                    oac_response = self.cloudfront_client.create_origin_access_control(
                        OriginAccessControlConfig={
                            "Name": oac_name,
                            "Description": f"OAC for {subdomain} accessing {s3_origin_server_name}{s3_origin_path}",
                            "SigningBehavior": "always",
                            "SigningProtocol": "sigv4",
                            "OriginAccessControlOriginType": "s3",
                        }
                    )
                    oac_id = oac_response["OriginAccessControl"]["Id"]
                    self.logger.info(
                        f"Created new OAC {oac_id} for updating existing distribution {distribution_id}."
                    )
                except ClientError as oac_error:
                    self.logger.error(
                        f"Failed to create OAC for updating distribution {distribution_id}: {oac_error}"
                    )
                    raise DeploymentException(
                        f"Failed to create OAC for distribution update: {oac_error}"
                    )

                try:
                    dist_config_response = (
                        self.cloudfront_client.get_distribution_config(
                            Id=distribution_id
                        )
                    )
                    current_config = dist_config_response["DistributionConfig"]
                    current_etag = dist_config_response["ETag"]
                except ClientError as e:
                    self.logger.error(
                        f"Failed to get config for existing distribution {distribution_id}: {e}"
                    )
                    raise DeploymentException(
                        f"Failed to get config for existing distribution: {e}"
                    )

                updated_origins_items = []
                # ID of the S3 origin we want to configure for this portfolio
                s3_origin_id_for_portfolio_target = f"{subdomain}-s3-origin"
                origin_to_use_for_cache_behavior = (
                    s3_origin_id_for_portfolio_target  # Default to our standard ID
                )

                found_and_repurposed_existing_s3_origin = False

                for origin_item in current_config.get("Origins", {}).get("Items", []):
                    origin_id = origin_item.get("Id", "")
                    origin_domain = origin_item.get("DomainName", "")
                    is_s3_origin = ".s3." in origin_domain

                    # Heuristic: Is this an S3 origin that seems to be for this subdomain?
                    is_s3_origin_for_this_subdomain = is_s3_origin and (
                        subdomain.lower() in origin_id.lower()
                        or subdomain.lower() in origin_domain.lower()
                    )

                    if (
                        is_s3_origin_for_this_subdomain
                        and not found_and_repurposed_existing_s3_origin
                    ):
                        self.logger.info(
                            f"Re-purposing existing S3 origin (ID: {origin_id}, Domain: {origin_domain}) for portfolio '{subdomain}'. It will be updated to use the correct S3 bucket, path, and OAC, keeping its current ID."
                        )
                        updated_item = {
                            "Id": origin_id,  # Keep original ID
                            "DomainName": s3_origin_server_name,  # New S3 bucket
                            "OriginPath": s3_origin_path,  # New S3 path
                            "OriginAccessControlId": oac_id,  # New OAC
                            "S3OriginConfig": {"OriginAccessIdentity": ""},
                            "CustomHeaders": {
                                "Quantity": 0
                            },  # Add missing CustomHeaders
                        }
                        updated_origins_items.append(updated_item)
                        origin_to_use_for_cache_behavior = (
                            origin_id  # Use this origin's actual ID for cache behavior
                        )
                        found_and_repurposed_existing_s3_origin = True
                    elif (
                        origin_id == s3_origin_id_for_portfolio_target
                        and not found_and_repurposed_existing_s3_origin
                    ):  # Our standard ID, but we didn't find another to repurpose first
                        self.logger.info(
                            f"Found our standard S3 origin (ID: {origin_id}). Updating it."
                        )
                        updated_item = {
                            "Id": origin_id,
                            "DomainName": s3_origin_server_name,
                            "OriginPath": s3_origin_path,
                            "OriginAccessControlId": oac_id,
                            "S3OriginConfig": {"OriginAccessIdentity": ""},
                            "CustomHeaders": {
                                "Quantity": 0
                            },  # Add missing CustomHeaders
                        }
                        updated_origins_items.append(updated_item)
                        origin_to_use_for_cache_behavior = origin_id
                        found_and_repurposed_existing_s3_origin = (
                            True  # Technically found, not repurposed
                        )
                    elif (
                        is_s3_origin_for_this_subdomain
                        and found_and_repurposed_existing_s3_origin
                    ):
                        # We already repurposed one S3 origin for this portfolio. Remove other S3 origins for this subdomain.
                        self.logger.info(
                            f"Removing superfluous S3 origin (ID: {origin_id}, Domain: {origin_domain}) for portfolio '{subdomain}'."
                        )
                        # Do not add to updated_origins_items
                    else:
                        # This is some other origin (e.g., non-S3, or an S3 origin completely unrelated). Keep it.
                        self.logger.info(
                            f"Keeping existing unrelated origin: {origin_id}"
                        )
                        updated_origins_items.append(origin_item)

                # If no S3 origin was found and repurposed/updated, add our standard one now.
                if not found_and_repurposed_existing_s3_origin:
                    self.logger.info(
                        f"No existing S3 origin found for portfolio '{subdomain}'. Adding new S3 origin with ID '{s3_origin_id_for_portfolio_target}'."
                    )
                    new_origin_item = {
                        "Id": s3_origin_id_for_portfolio_target,
                        "DomainName": s3_origin_server_name,
                        "OriginPath": s3_origin_path,
                        "OriginAccessControlId": oac_id,
                        "S3OriginConfig": {"OriginAccessIdentity": ""},
                        "CustomHeaders": {"Quantity": 0},  # Add missing CustomHeaders
                    }
                    updated_origins_items.append(new_origin_item)
                    # origin_to_use_for_cache_behavior is already s3_origin_id_for_portfolio_target

                current_config["Origins"]["Items"] = updated_origins_items
                current_config["Origins"]["Quantity"] = len(updated_origins_items)

                # Ensure DefaultCacheBehavior TargetOriginId points to the correct S3 origin's ID
                if current_config.get("DefaultCacheBehavior"):
                    current_config["DefaultCacheBehavior"][
                        "TargetOriginId"
                    ] = origin_to_use_for_cache_behavior
                else:
                    self.logger.error(
                        "DefaultCacheBehavior missing in existing distribution config!"
                    )

                current_config["DefaultRootObject"] = "index.html"
                current_config.setdefault(
                    "Comment",
                    f"Portfolio website for {subdomain} (files in {bucket_name_for_origin}{s3_origin_path})",
                )

                current_config.setdefault("Aliases", {"Quantity": 0, "Items": []})
                if f"{subdomain}.yarba.app" not in current_config["Aliases"]["Items"]:
                    current_config["Aliases"]["Items"].append(f"{subdomain}.yarba.app")
                current_config["Aliases"]["Quantity"] = len(
                    current_config["Aliases"]["Items"]
                )

                # Ensure ViewerCertificate is present, especially if Aliases are used
                if not current_config.get("ViewerCertificate"):
                    current_config["ViewerCertificate"] = (
                        {
                            "ACMCertificateArn": settings.storage.aws_acm_certificate_arn,
                            "SSLSupportMethod": "sni-only",
                            "MinimumProtocolVersion": "TLSv1.2_2021",
                        }
                        if settings.storage.aws_acm_certificate_arn
                        else {"CloudFrontDefaultCertificate": True}
                    )
                if (
                    not settings.storage.aws_acm_certificate_arn
                    and "ACMCertificateArn" in current_config["ViewerCertificate"]
                ):
                    # If no ACM cert is configured now, but one was set, switch to default cert
                    current_config["ViewerCertificate"] = {
                        "CloudFrontDefaultCertificate": True
                    }
                    current_config.pop(
                        "Aliases", None
                    )  # Aliases won't work reliably without a matching cert
                    self.logger.warning(
                        f"No ACM cert for {subdomain} in current settings; removing Aliases if any and using default CloudFront cert."
                    )

                # Log the complete distribution config before attempting update
                try:
                    config_to_log = json.dumps(
                        current_config, indent=2, default=str
                    )  # Use default=str for any non-serializable objects
                    self.logger.debug(
                        f"Attempting to update distribution {distribution_id} with ETag {current_etag} and Config:\n{config_to_log}"
                    )
                except Exception as log_e:
                    self.logger.error(
                        f"Error serializing distribution config for logging: {log_e}"
                    )

                try:
                    self.cloudfront_client.update_distribution(
                        DistributionConfig=current_config,
                        Id=distribution_id,
                        IfMatch=current_etag,
                    )
                    self.logger.info(
                        f"Updated existing CloudFront distribution {distribution_id} to use OAC {oac_id} and OriginPath {s3_origin_path}."
                    )
                except ClientError as e:
                    self.logger.error(
                        f"Failed to update existing distribution {distribution_id}: {e}"
                    )
                    raise DeploymentException(
                        f"Failed to update existing distribution: {e}"
                    )

                await self._update_s3_bucket_policy_for_oac(
                    bucket_name_to_update=self.main_bucket_name,
                    s3_path_prefix_for_policy=s3_portfolio_prefix,
                    cloudfront_distribution_arn=distribution_arn,
                )

                website_url = (
                    f"https://{subdomain}.yarba.app"
                    if f"{subdomain}.yarba.app"
                    in current_config.get("Aliases", {}).get("Items", [])
                    else f"https://{cloudfront_domain_name}"
                )

                return {
                    "distribution_id": distribution_id,
                    "domain_name": cloudfront_domain_name,
                    "website_url": website_url,
                    "distribution_arn": distribution_arn,
                }

            # No existing distribution, proceed with creation logic
            self.logger.info(
                f"No existing CloudFront distribution found for {subdomain}. Creating a new one."
            )
            oac_name = (
                f"{subdomain}-portfolio-OAC-{int(asyncio.get_event_loop().time())}"
            )
            try:
                oac_response = self.cloudfront_client.create_origin_access_control(
                    OriginAccessControlConfig={
                        "Name": oac_name,
                        "Description": f"OAC for {subdomain} accessing {s3_origin_server_name}{s3_origin_path}",
                        "SigningBehavior": "always",
                        "SigningProtocol": "sigv4",
                        "OriginAccessControlOriginType": "s3",
                    }
                )
                oac_id = oac_response["OriginAccessControl"]["Id"]
                self.logger.info(
                    f"Created new OAC {oac_id} for creating new distribution."
                )
            except ClientError as oac_error:
                self.logger.error(
                    f"Failed to create OAC for new distribution: {oac_error}"
                )
                raise DeploymentException(
                    f"Failed to create OAC for new distribution: {oac_error}"
                )

            distribution_config = {
                "CallerReference": f"{subdomain}-portfolio-{int(asyncio.get_event_loop().time())}",
                "Comment": f"Portfolio website for {subdomain} (files in {bucket_name_for_origin}{s3_origin_path})",
                "DefaultCacheBehavior": {
                    "TargetOriginId": f"{subdomain}-s3-origin",  # Origin ID can be more descriptive
                    "ViewerProtocolPolicy": "redirect-to-https",
                    "MinTTL": 0,
                    "DefaultTTL": 86400,
                    "MaxTTL": 31536000,
                    "AllowedMethods": {
                        "Quantity": 2,
                        "Items": ["GET", "HEAD"],
                        "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
                    },
                    "ForwardedValues": {
                        "QueryString": False,
                        "Cookies": {"Forward": "none"},
                        "Headers": {"Quantity": 0},
                    },
                    "Compress": True,
                    "TrustedSigners": {"Enabled": False, "Quantity": 0},
                },
                "Origins": {
                    "Quantity": 1,
                    "Items": [
                        {
                            "Id": f"{subdomain}-s3-origin",
                            "DomainName": s3_origin_server_name,  # Use corrected domain name
                            "OriginPath": s3_origin_path,  # CRITICAL: Set the Origin Path
                            "OriginAccessControlId": oac_id,
                        }
                    ],
                },
                "Enabled": True,
                "Aliases": {"Quantity": 1, "Items": [f"{subdomain}.yarba.app"]},
                "DefaultRootObject": "index.html",
                "ViewerCertificate": (
                    {
                        "ACMCertificateArn": settings.storage.aws_acm_certificate_arn,
                        "SSLSupportMethod": "sni-only",
                        "MinimumProtocolVersion": "TLSv1.2_2021",
                    }
                    if settings.storage.aws_acm_certificate_arn
                    else {"CloudFrontDefaultCertificate": True}
                ),
                "CustomErrorResponses": {
                    "Quantity": 2,
                    "Items": [
                        {
                            "ErrorCode": 404,
                            "ResponsePagePath": "/index.html",
                            "ResponseCode": "200",
                            "ErrorCachingMinTTL": 300,
                        },
                        {
                            "ErrorCode": 403,
                            "ResponsePagePath": "/index.html",
                            "ResponseCode": "200",
                            "ErrorCachingMinTTL": 300,
                        },
                    ],
                },
                "PriceClass": "PriceClass_100",
            }

            if not settings.storage.aws_acm_certificate_arn:
                distribution_config.pop("Aliases", None)
                self.logger.warning(
                    f"No ACM certificate ARN for {subdomain}. Custom domain alias will not be used."
                )

            response = self.cloudfront_client.create_distribution(
                DistributionConfig=distribution_config
            )

            distribution_id = response["Distribution"]["Id"]
            distribution_arn = response["Distribution"]["ARN"]
            domain_name = response["Distribution"]["DomainName"]

            self.logger.info(
                f"Created CloudFront distribution {distribution_id} for {subdomain}"
            )

            # Update S3 bucket policy for this OAC to access the specific prefix
            await self._update_s3_bucket_policy_for_oac(
                bucket_name_to_update=self.main_bucket_name,
                s3_path_prefix_for_policy=s3_portfolio_prefix,  # Corrected from s3_origin_path to use the prefix without leading slash
                cloudfront_distribution_arn=distribution_arn,
            )

            if (
                settings.storage.aws_acm_certificate_arn
                and f"{subdomain}.yarba.app"
                in distribution_config.get("Aliases", {}).get("Items", [])
            ):
                website_url = f"https://{subdomain}.yarba.app"
            else:
                website_url = f"https://{domain_name}"

            return {
                "distribution_id": distribution_id,
                "domain_name": domain_name,
                "website_url": website_url,
                "distribution_arn": distribution_arn,
            }

        except ClientError as e:
            self.logger.error(
                f"Failed to create CloudFront distribution for {subdomain}: {e}"
            )
            # Consider specific error handling for OAC already exists if a clear exception type is found
            raise DeploymentException(f"Failed to create CloudFront distribution: {e}")

    async def _update_s3_bucket_policy_for_oac(
        self,
        bucket_name_to_update: str,
        s3_path_prefix_for_policy: str,
        cloudfront_distribution_arn: str,
    ) -> None:
        """Update S3 bucket policy to grant access to CloudFront OAC for a specific path."""
        try:
            # aws_account_id = self.sts_client.get_caller_identity().get('Account') # Not needed for this policy structure

            # Construct the specific resource path
            # s3_path_prefix_for_policy should be like "portfolios/subdomain"
            resource_arn_path = f"arn:aws:s3:::{bucket_name_to_update}/{s3_path_prefix_for_policy.strip('/')}/*"

            self.logger.info(
                f"Attempting to set S3 bucket policy for OAC. Bucket: {bucket_name_to_update}, Resource Path: {resource_arn_path}, Distribution ARN: {cloudfront_distribution_arn}"
            )

            # It's critical to manage existing bucket policies correctly.
            # This example attempts to put a policy. If a policy exists, PutBucketPolicy overwrites.
            # A robust solution should get existing policy, add/update this statement, then put.
            # For now, assuming this is the primary or only CloudFront-related policy statement,
            # or that overwriting with this specific focused policy is acceptable.

            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": f"AllowCloudFrontOAC{cloudfront_distribution_arn.split('/')[-1]}",  # Unique Sid
                        "Effect": "Allow",
                        "Principal": {"Service": "cloudfront.amazonaws.com"},
                        "Action": "s3:GetObject",
                        "Resource": resource_arn_path,
                        "Condition": {
                            "StringEquals": {
                                "AWS:SourceArn": cloudfront_distribution_arn
                            }
                        },
                    }
                ],
            }

            # Fetch existing policy to append/update (safer approach)
            try:
                existing_policy_str = self.s3_client.get_bucket_policy(
                    Bucket=bucket_name_to_update
                )["Policy"]
                existing_policy = json.loads(existing_policy_str)

                # Remove any old statement with the same Sid to avoid conflicts if re-running
                existing_policy["Statement"] = [
                    stmt
                    for stmt in existing_policy["Statement"]
                    if stmt.get("Sid") != bucket_policy["Statement"][0]["Sid"]
                ]

                # Add the new statement
                existing_policy["Statement"].append(bucket_policy["Statement"][0])
                final_policy_to_apply = existing_policy
                self.logger.info(
                    f"Merging new OAC policy statement with existing policy for bucket {bucket_name_to_update}"
                )

            except self.s3_client.exceptions.NoSuchBucketPolicy:
                self.logger.info(
                    f"No existing bucket policy found for {bucket_name_to_update}. Applying new OAC policy."
                )
                final_policy_to_apply = bucket_policy
            except Exception as e_get_policy:
                self.logger.warning(
                    f"Could not get existing bucket policy for {bucket_name_to_update}: {e_get_policy}. Will attempt to set new policy directly."
                )
                final_policy_to_apply = bucket_policy

            self.s3_client.put_bucket_policy(
                Bucket=bucket_name_to_update, Policy=json.dumps(final_policy_to_apply)
            )
            self.logger.info(
                f"Updated S3 bucket policy for {bucket_name_to_update} to allow OAC access for {s3_path_prefix_for_policy} from {cloudfront_distribution_arn}"
            )

        except ClientError as e:
            self.logger.error(
                f"Failed to update S3 bucket policy for OAC access to {bucket_name_to_update} (path: {s3_path_prefix_for_policy}): {e}"
            )
            raise DeploymentException(
                f"Failed to set S3 bucket policy for CloudFront OAC (path: {s3_path_prefix_for_policy}): {e}"
            )
        except Exception as e:
            self.logger.error(
                f"Unexpected error updating S3 policy for OAC (path: {s3_path_prefix_for_policy}): {e}"
            )
            raise DeploymentException(
                f"Unexpected error setting S3 policy for OAC (path: {s3_path_prefix_for_policy}): {e}"
            )

    async def _get_existing_distribution(self, subdomain: str) -> Optional[Dict]:
        """Get existing CloudFront distribution for subdomain."""
        try:
            response = self.cloudfront_client.list_distributions()

            for distribution in response.get("DistributionList", {}).get("Items", []):
                aliases = distribution.get("Aliases", {}).get("Items", [])
                if f"{subdomain}.yarba.app" in aliases:
                    return distribution

            return None

        except ClientError as e:
            self.logger.warning(f"Failed to list CloudFront distributions: {e}")
            return None

    async def _setup_route53_subdomain(
        self, subdomain: str, cloudfront_domain: str
    ) -> None:
        """Set up Route 53 subdomain pointing to CloudFront distribution."""
        try:
            # Get hosted zone for yarba.app
            hosted_zone_id = await self._get_hosted_zone_id("yarba.app")

            if not hosted_zone_id:
                self.logger.warning("yarba.app hosted zone not found in Route 53")
                return

            # Create CNAME record
            change_batch = {
                "Changes": [
                    {
                        "Action": "UPSERT",
                        "ResourceRecordSet": {
                            "Name": f"{subdomain}.yarba.app",
                            "Type": "CNAME",
                            "TTL": 300,
                            "ResourceRecords": [{"Value": cloudfront_domain}],
                        },
                    }
                ]
            }

            response = self.route53_client.change_resource_record_sets(
                HostedZoneId=hosted_zone_id, ChangeBatch=change_batch
            )

            self.logger.info(f"Created Route 53 record for {subdomain}.yarba.app")

        except ClientError as e:
            self.logger.warning(
                f"Failed to create Route 53 record for {subdomain}: {e}"
            )
            # Don't raise exception as this isn't critical for basic functionality

    async def _get_hosted_zone_id(self, domain: str) -> Optional[str]:
        """Get Route 53 hosted zone ID for domain."""
        try:
            response = self.route53_client.list_hosted_zones()

            for zone in response.get("HostedZones", []):
                if zone["Name"].rstrip(".") == domain:
                    return zone["Id"].split("/")[-1]  # Extract ID from full ARN

            return None

        except ClientError as e:
            self.logger.warning(f"Failed to get hosted zone for {domain}: {e}")
            return None

    async def _delete_cloudfront_distribution(self, subdomain: str) -> None:
        """Delete CloudFront distribution for subdomain."""
        try:
            distribution = await self._get_existing_distribution(subdomain)

            if not distribution:
                self.logger.info(f"No CloudFront distribution found for {subdomain}")
                return

            distribution_id = distribution["Id"]

            # First disable the distribution
            distribution_config = self.cloudfront_client.get_distribution_config(
                Id=distribution_id
            )
            config = distribution_config["DistributionConfig"]
            config["Enabled"] = False

            self.cloudfront_client.update_distribution(
                Id=distribution_id,
                DistributionConfig=config,
                IfMatch=distribution_config["ETag"],
            )

            self.logger.info(f"Disabled CloudFront distribution {distribution_id}")

            # Note: Full deletion requires waiting for distribution to be disabled
            # This is typically handled as a background task

        except ClientError as e:
            self.logger.warning(
                f"Failed to delete CloudFront distribution for {subdomain}: {e}"
            )

    async def _delete_route53_subdomain(self, subdomain: str) -> None:
        """Delete Route 53 subdomain record."""
        try:
            hosted_zone_id = await self._get_hosted_zone_id("yarba.app")

            if not hosted_zone_id:
                return

            # Get existing record to delete
            response = self.route53_client.list_resource_record_sets(
                HostedZoneId=hosted_zone_id
            )

            for record_set in response.get("ResourceRecordSets", []):
                if record_set["Name"] == f"{subdomain}.yarba.app.":
                    change_batch = {
                        "Changes": [
                            {"Action": "DELETE", "ResourceRecordSet": record_set}
                        ]
                    }

                    self.route53_client.change_resource_record_sets(
                        HostedZoneId=hosted_zone_id, ChangeBatch=change_batch
                    )

                    self.logger.info(
                        f"Deleted Route 53 record for {subdomain}.yarba.app"
                    )
                    break

        except ClientError as e:
            self.logger.warning(
                f"Failed to delete Route 53 record for {subdomain}: {e}"
            )

    async def _delete_s3_objects_with_prefix(
        self, bucket_name: str, prefix: str
    ) -> None:
        """Delete all S3 objects with a given prefix from the bucket."""
        try:
            objects_to_delete = []
            paginator = self.s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        objects_to_delete.append({"Key": obj["Key"]})

            if objects_to_delete:
                self.s3_client.delete_objects(
                    Bucket=bucket_name,
                    Delete={"Objects": objects_to_delete, "Quiet": True},
                )
                self.logger.info(
                    f"Deleted {len(objects_to_delete)} objects with prefix '{prefix}' from S3 bucket {bucket_name}"
                )
            else:
                self.logger.info(
                    f"No objects found with prefix '{prefix}' in S3 bucket {bucket_name} to delete."
                )

        except ClientError as e:
            self.logger.warning(
                f"Failed to delete objects with prefix '{prefix}' from S3 bucket {bucket_name}: {e}"
            )
            # Depending on severity, you might want to raise an exception here.
            # For a delete operation, logging a warning might be acceptable if some objects fail.

    async def _create_cloudfront_invalidation(self, distribution_id: str) -> None:
        """Create a CloudFront invalidation for all paths."""
        try:
            caller_reference = (
                f"invalidate-{distribution_id}-{int(asyncio.get_event_loop().time())}"
            )
            self.cloudfront_client.create_invalidation(
                DistributionId=distribution_id,
                InvalidationBatch={
                    "Paths": {"Quantity": 1, "Items": ["/*"]},
                    "CallerReference": caller_reference,
                },
            )
            self.logger.info(
                f"Created CloudFront invalidation for distribution {distribution_id} with paths '/*'. CallerReference: {caller_reference}"
            )
        except ClientError as e:
            self.logger.warning(
                f"Failed to create CloudFront invalidation for {distribution_id}: {e}"
            )
            # Don't let invalidation failure stop the whole process, but log it.
        except Exception as e:
            self.logger.error(
                f"Unexpected error creating CloudFront invalidation for {distribution_id}: {e}"
            )
