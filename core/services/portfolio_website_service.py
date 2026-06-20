"""Portfolio website service for website generation and deployment."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from beanie import PydanticObjectId

from config.logging_config import get_logger

from ..exceptions.base import (
    ConflictException,
    DeploymentException,
    NotFoundException,
    ValidationException,
)
from ..models.portfolio import Portfolio
from ..models.portfolio_website import PortfolioWebsite, WebsiteConfig
from ..models.profile import Profile
from ..models.user import User
from ..repositories.portfolio_repository import PortfolioRepository
from ..repositories.portfolio_website_repository import PortfolioWebsiteRepository
from ..repositories.profile_repository import ProfileRepository
from ..repositories.user_repository import UserRepository
from ..utils.object_id import require_object_id
from .aws_deployment_service import AWSDeploymentService
from .website_generator_service import WebsiteGeneratorService


class PortfolioWebsiteService:
    """Service for portfolio website operations."""

    def __init__(
        self,
        website_repository: PortfolioWebsiteRepository,
        portfolio_repository: PortfolioRepository,
        user_repository: UserRepository,
        profile_repository: ProfileRepository,
        aws_deployment_service: AWSDeploymentService,
        website_generator_service: WebsiteGeneratorService,
    ):
        """Initialize the service."""
        self.website_repository = website_repository
        self.portfolio_repository = portfolio_repository
        self.user_repository = user_repository
        self.profile_repository = profile_repository
        self.aws_deployment_service = aws_deployment_service
        self.website_generator_service = website_generator_service
        self.logger = get_logger(self.__class__.__name__)

    async def create_portfolio_website(
        self,
        user_id: PydanticObjectId,
        config: WebsiteConfig | None = None,
        custom_subdomain: str | None = None,
    ) -> PortfolioWebsite:
        """Create a new portfolio website for a user.
        This will also trigger the initial deployment asynchronously.
        """
        # Check if user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        # Check if user already has a portfolio website
        existing_website = await self.website_repository.get_by_user_id(user_id)
        if existing_website:
            raise ConflictException("User already has a portfolio website")

        # Get user's portfolio
        portfolio = await self.portfolio_repository.get_by_user_id(user_id)
        if not portfolio:
            # Create a default portfolio if none exists
            portfolio = await self.portfolio_repository.create_for_user(user_id)

        # Get user's profile for name extraction
        profile = await self.profile_repository.get_by_user_id(user_id)

        # Generate subdomain
        if custom_subdomain:
            subdomain = custom_subdomain.lower().strip()
            if not await self.website_repository.check_subdomain_availability(
                subdomain
            ):
                raise ConflictException(f"Subdomain '{subdomain}' is already taken")
        else:
            subdomain = await self._generate_subdomain(user, profile)

        # Create website config if not provided, or convert from API schema
        if not config:
            website_config = WebsiteConfig()
        else:
            if hasattr(config, "model_dump"):
                website_config = WebsiteConfig(**config.model_dump())
            else:
                website_config = config  # Assume it's already a WebsiteConfig model

        # Create the portfolio website instance
        website = PortfolioWebsite(
            user_id=user_id,
            portfolio_id=portfolio.id,
            subdomain=subdomain,
            config=website_config,
            # Initialize deployment status (optional, could also be set by _deploy_website_async first call)
            # deployment=PortfolioDeploymentStatus(status="pending")
        )

        # Save to database
        website = await self.website_repository.create(website)

        self.logger.info(
            f"Created portfolio website record for user {user_id} with subdomain: {subdomain}. ID: {website.id}"
        )

        # Trigger initial deployment asynchronously
        # _deploy_website_async will handle updating the website object with deployment details (URL, status etc.)
        asyncio.create_task(self._deploy_website_async(require_object_id(website.id)))

        self.logger.info(
            f"Initial asynchronous deployment triggered for website {website.id}. The website object will be updated upon completion."
        )

        # Return the initially created website object.
        # The caller should understand that deployment is happening in the background.
        return website

    async def get_portfolio_website(
        self, user_id: PydanticObjectId
    ) -> PortfolioWebsite | None:
        """Get a user's portfolio website.

        Args:
            user_id: User ID

        Returns:
            Optional[PortfolioWebsite]: Website if found
        """
        return await self.website_repository.get_by_user_id(user_id)

    async def get_website_by_subdomain(self, subdomain: str) -> PortfolioWebsite | None:
        """Get a portfolio website by subdomain.

        Args:
            subdomain: Subdomain to search for

        Returns:
            Optional[PortfolioWebsite]: Website if found
        """
        return await self.website_repository.get_by_subdomain(subdomain)

    async def update_website_config(
        self,
        user_id: PydanticObjectId,
        config: WebsiteConfig,
        force_rebuild: bool = False,
    ) -> PortfolioWebsite:
        """Update website configuration.

        Args:
            user_id: User ID
            config: New website configuration
            force_rebuild: Force rebuild even if no significant changes

        Returns:
            PortfolioWebsite: Updated website

        Raises:
            NotFoundException: If website not found
        """
        website = await self.website_repository.get_by_user_id(user_id)
        if not website:
            raise NotFoundException("Portfolio website not found")

        # Convert from API schema (PortfolioWebsiteConfig) to model (WebsiteConfig) if needed
        if hasattr(config, "model_dump"):
            # It's a Pydantic model, convert it
            website_config = WebsiteConfig(**config.model_dump())
        else:
            # It's already a WebsiteConfig
            website_config = config

        website_id = require_object_id(website.id)
        old_config = website.config

        # Update configuration
        website.config = website_config
        website.updated_at = datetime.now(UTC)

        # Save changes
        updated_website = await self.website_repository.update(website_id, website)
        if not updated_website:
            raise NotFoundException("Portfolio website not found")
        website = updated_website

        # Trigger rebuild if forced or significant changes detected
        if force_rebuild or self._config_requires_rebuild(old_config, website_config):
            asyncio.create_task(self._deploy_website_async(website_id))

        return website

    async def deploy_website(
        self,
        user_id: PydanticObjectId,
        force_rebuild: bool = False,
        clean_deploy: bool = False,
    ) -> PortfolioWebsite:
        """Deploy or redeploy a portfolio website.

        Args:
            user_id: User ID
            force_rebuild: Force rebuild even if content hasn't changed
            clean_deploy: Delete all existing files before uploading (clean slate)

        Returns:
            PortfolioWebsite: Website with updated deployment status

        Raises:
            NotFoundException: If website or portfolio not found
            DeploymentException: If deployment fails
        """
        website = await self.website_repository.get_by_user_id(user_id)
        if not website:
            raise NotFoundException("Portfolio website not found")

        # Check if rebuild is needed
        portfolio = await self.portfolio_repository.get_by_id(website.portfolio_id)
        if not portfolio:
            raise NotFoundException("Portfolio not found")

        profile = await self.profile_repository.get_by_user_id(user_id)
        current_hash = self._calculate_portfolio_hash(
            portfolio, website.config, profile=profile
        )

        # Clean deploy always forces rebuild
        if (
            not force_rebuild
            and not clean_deploy
            and website.last_build_hash == current_hash
        ):
            self.logger.info(
                f"No changes detected for website {website.id}, skipping rebuild"
            )
            return website

        website_id = require_object_id(website.id)

        # Start deployment process synchronously
        await self._deploy_website_sync(website_id, clean_deploy=clean_deploy)

        # Get updated website after deployment
        updated_website = await self.website_repository.get_by_id(website_id)
        if not updated_website:
            raise NotFoundException("Website not found after deployment")

        # Check if deployment failed and raise exception
        if updated_website.deployment.status == "failed":
            error_msg = updated_website.deployment.error_message or "Deployment failed"
            raise DeploymentException(error_msg)

        return updated_website

    async def _deploy_website_async(self, website_id: PydanticObjectId) -> None:
        """Asynchronously deploy a portfolio website.

        Args:
            website_id: Website ID to deploy
        """
        try:
            # Update status to building and clear previous errors
            await self.website_repository.update_deployment_status(
                website_id,
                "building",
                started_at=datetime.now(UTC),
                completed_at=None,  # Clear previous completed_at
                build_id=f"build_{int(datetime.now().timestamp())}",
                error_message=None,  # Clear previous error
                error_code=None,  # Clear previous error code
            )

            website = await self.website_repository.get_by_id(website_id)
            if not website:
                self.logger.error(f"Website {website_id} not found during deployment")
                return

            # Get portfolio data
            portfolio = await self.portfolio_repository.get_by_id(website.portfolio_id)
            if not portfolio:
                await self.website_repository.update_deployment_status(
                    website_id,
                    "failed",
                    error_message="Portfolio not found",
                    completed_at=datetime.now(UTC),
                )
                return

            # Get user and profile data
            user = await self.user_repository.get_by_id(website.user_id)
            profile = await self.profile_repository.get_by_user_id(website.user_id)

            # Generate website files
            website_files = await self.website_generator_service.generate_website(
                portfolio=portfolio,
                subdomain=website.subdomain,
                user=user,
                profile=profile,
                config=website.config,
            )

            # Deploy to AWS
            deployment_result = await self.aws_deployment_service.deploy_website(
                subdomain=website.subdomain, files=website_files, config=website.config
            )

            completed_time = datetime.now(UTC)
            # Ensure website.deployment.started_at is not None before calculating duration
            build_duration_val = None
            if website.deployment.started_at:
                build_duration_val = int(
                    completed_time.timestamp()
                    - website.deployment.started_at.timestamp()
                )

            # Update deployment status to success and get the updated website object
            updated_website = await self.website_repository.update_deployment_status(
                website_id,
                "success",
                deployment_url=deployment_result.get("website_url"),
                s3_bucket_name=deployment_result.get("bucket_name"),
                cloudfront_distribution_id=deployment_result.get("distribution_id"),
                cloudfront_domain=deployment_result.get("cloudfront_domain"),
                completed_at=completed_time,
                build_duration=build_duration_val,
                error_message=None,  # Clear any previous error messages on success
                error_code=None,
            )

            if not updated_website:
                self.logger.error(
                    f"Website {website_id} not found after status update to success in _deploy_website_async."
                )
                # Consider raising an exception or returning if critical
                return

            # Use the fresh website object for subsequent updates
            updated_website.is_published = True
            updated_website.last_build_hash = self._calculate_portfolio_hash(
                portfolio,
                updated_website.config,
                profile=profile,
            )
            updated_website.last_deployed_at = completed_time
            await updated_website.save()

            self.logger.info(
                f"Successfully deployed website {website_id} to {updated_website.subdomain}.yarba.app"
            )

        except (
            DeploymentException
        ) as e:  # Catch specific DeploymentException from aws_deployment_service
            self.logger.error(f"Deployment failed for website {website_id}: {str(e)}")
            await self.website_repository.update_deployment_status(
                website_id,
                "failed",
                error_message=str(e),
                completed_at=datetime.now(UTC),
            )
        except Exception as e:  # Catch any other unexpected errors
            self.logger.error(
                f"An unexpected error occurred during async deployment of website {website_id}: {str(e)}"
            )
            # Update status to failed
            await self.website_repository.update_deployment_status(
                website_id,
                "failed",
                error_message=f"Unexpected error during deployment: {str(e)}",
                completed_at=datetime.now(UTC),
            )

    async def _deploy_website_sync(
        self, website_id: PydanticObjectId, clean_deploy: bool = False
    ) -> None:
        """Synchronously deploy a portfolio website.

        Args:
            website_id: Website ID to deploy
            clean_deploy: Delete all existing files before uploading (clean slate)

        Raises:
            DeploymentException: If deployment fails
        """
        try:
            # Update status to building and clear previous errors
            await self.website_repository.update_deployment_status(
                website_id,
                "building",
                started_at=datetime.now(UTC),
                completed_at=None,  # Clear previous completed_at
                build_id=f"build_{int(datetime.now().timestamp())}",
                error_message=None,  # Clear previous error
                error_code=None,  # Clear previous error code
            )

            website = await self.website_repository.get_by_id(website_id)
            if not website:
                self.logger.error(f"Website {website_id} not found during deployment")
                raise DeploymentException("Website not found during deployment")

            # Get portfolio data
            portfolio = await self.portfolio_repository.get_by_id(website.portfolio_id)
            if not portfolio:
                await self.website_repository.update_deployment_status(
                    website_id,
                    "failed",
                    error_message="Portfolio not found",
                    completed_at=datetime.now(UTC),
                )
                raise DeploymentException("Portfolio not found")

            # Get user and profile data
            user = await self.user_repository.get_by_id(website.user_id)
            profile = await self.profile_repository.get_by_user_id(website.user_id)

            # Generate website files
            website_files = await self.website_generator_service.generate_website(
                portfolio=portfolio,
                subdomain=website.subdomain,
                user=user,
                profile=profile,
                config=website.config,
            )

            # Deploy to AWS
            deployment_result = await self.aws_deployment_service.deploy_website(
                subdomain=website.subdomain,
                files=website_files,
                config=website.config,
                clean_deploy=clean_deploy,
            )

            completed_time = datetime.now(UTC)
            # Ensure website.deployment.started_at is not None before calculating duration
            build_duration_val = None
            if website.deployment.started_at:
                build_duration_val = int(
                    completed_time.timestamp()
                    - website.deployment.started_at.timestamp()
                )

            # Update deployment status and get the updated website object
            updated_website = await self.website_repository.update_deployment_status(
                website_id,
                "success",
                deployment_url=deployment_result.get("website_url"),
                s3_bucket_name=deployment_result.get("bucket_name"),
                cloudfront_distribution_id=deployment_result.get("distribution_id"),
                cloudfront_domain=deployment_result.get("cloudfront_domain"),
                completed_at=completed_time,
                build_duration=build_duration_val,
                error_message=None,  # Clear previous error on success
                error_code=None,  # Clear previous error code on success
            )

            if not updated_website:
                self.logger.error(
                    f"Website {website_id} not found after status update to success in _deploy_website_sync."
                )
                raise DeploymentException(
                    f"Website {website_id} not found after status update to success."
                )

            # Update website as published and set build hash using the fresh object
            updated_website.is_published = True
            updated_website.last_build_hash = self._calculate_portfolio_hash(
                portfolio,
                updated_website.config,
                profile=profile,
            )
            updated_website.last_deployed_at = completed_time
            await updated_website.save()

            self.logger.info(
                f"Successfully deployed website {website_id} to {updated_website.subdomain}.yarba.app"
            )

        except DeploymentException:
            # Re-raise DeploymentException as-is
            raise
        except Exception as e:
            self.logger.error(f"Failed to deploy website {website_id}: {str(e)}")

            # Update status to failed
            await self.website_repository.update_deployment_status(
                website_id,
                "failed",
                error_message=str(e),
                completed_at=datetime.now(UTC),
            )
            raise DeploymentException(f"Deployment failed: {str(e)}")

    async def check_subdomain_availability(self, subdomain: str) -> dict[str, Any]:
        """Check if a subdomain is available and suggest alternatives.

        Args:
            subdomain: Subdomain to check

        Returns:
            Dict containing availability status and suggestions
        """
        subdomain = subdomain.lower().strip()

        # Validate subdomain format
        if not self._is_valid_subdomain(subdomain):
            raise ValidationException("Invalid subdomain format")

        available = await self.website_repository.check_subdomain_availability(
            subdomain
        )

        suggestions = []
        if not available:
            suggestions = await self.website_repository.suggest_alternative_subdomains(
                subdomain
            )

        return {
            "subdomain": subdomain,
            "available": available,
            "suggested_alternatives": suggestions,
        }

    async def delete_website(self, user_id: PydanticObjectId) -> bool:
        """Delete a portfolio website and its AWS resources.

        Args:
            user_id: User ID

        Returns:
            bool: True if deleted successfully

        Raises:
            NotFoundException: If website not found
        """
        website = await self.website_repository.get_by_user_id(user_id)
        if not website:
            raise NotFoundException("Portfolio website not found")

        subdomain = website.subdomain

        # Delete from database FIRST - this must succeed
        # so user can create a new website even if AWS cleanup fails
        await self.website_repository.delete(require_object_id(website.id))
        self.logger.info(f"Deleted portfolio website record for user {user_id}")

        # Then try to delete AWS resources (best effort)
        try:
            await self.aws_deployment_service.delete_website(subdomain)
            self.logger.info(f"Deleted AWS resources for subdomain {subdomain}")
        except Exception as e:
            # Log but don't fail - orphaned S3 files are better than
            # a user stuck unable to create a new website
            self.logger.warning(
                f"Failed to delete AWS resources for {subdomain}: {str(e)}. "
                "Orphaned S3 files may need manual cleanup."
            )

        return True

    async def _generate_subdomain(self, user: User, profile: Profile | None) -> str:
        """Generate a unique subdomain for the user.

        Args:
            user: User object
            profile: User profile (optional)

        Returns:
            str: Unique subdomain
        """
        if profile and profile.personal_information.full_name:
            base_subdomain = self._clean_name_for_subdomain(
                profile.personal_information.full_name
            )
        else:
            # Fallback to username or email
            base_subdomain = user.username or user.email.split("@")[0]

        # Clean and validate
        base_subdomain = self._clean_name_for_subdomain(base_subdomain)

        # Check availability
        if await self.website_repository.check_subdomain_availability(base_subdomain):
            return base_subdomain

        # Generate alternatives
        suggestions = await self.website_repository.suggest_alternative_subdomains(
            base_subdomain, 1
        )
        if suggestions:
            return suggestions[0]

        # Final fallback
        import uuid

        return f"user{str(uuid.uuid4())[:8]}"

    def _clean_name_for_subdomain(self, name: str) -> str:
        """Clean a name to create a valid subdomain.

        Args:
            name: Raw name string

        Returns:
            str: Cleaned subdomain
        """
        import re

        # Convert to lowercase and remove special characters
        clean_name = re.sub(r"[^a-z0-9\s]", "", name.lower())
        # Remove extra spaces and join
        subdomain = "".join(clean_name.split())

        # Ensure reasonable length
        if len(subdomain) > 63:  # DNS limit
            subdomain = subdomain[:63]
        elif len(subdomain) < 3:
            subdomain = f"user{subdomain}"

        return subdomain

    def _is_valid_subdomain(self, subdomain: str) -> bool:
        """Validate subdomain format.

        Args:
            subdomain: Subdomain to validate

        Returns:
            bool: True if valid
        """
        import re

        # Check basic format requirements
        if not subdomain or len(subdomain) < 3 or len(subdomain) > 63:
            return False

        # Must start and end with alphanumeric
        if not re.match(r"^[a-z0-9].*[a-z0-9]$", subdomain):
            return False

        # Only alphanumeric and hyphens
        if not re.match(r"^[a-z0-9-]*$", subdomain):
            return False

        # No consecutive hyphens
        if "--" in subdomain:
            return False

        return True

    def _calculate_portfolio_hash(
        self,
        portfolio: Portfolio,
        config: WebsiteConfig,
        profile: Profile | None = None,
    ) -> str:
        """Calculate a hash of the portfolio, config, and profile chat fields."""
        personal = profile.personal_information if profile else None
        data = {
            "portfolio": portfolio.model_dump(
                exclude={"id", "created_at", "updated_at"}
            ),
            "config": config.model_dump(),
            "profile_chat": {
                "life_story": profile.life_story if profile else None,
                "profile_picture_key": profile.profile_picture_key if profile else None,
                "calendly_url": personal.calendly_url if personal else None,
                "full_name": personal.full_name if personal else None,
            },
        }

        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def _config_requires_rebuild(
        self, old_config: WebsiteConfig, new_config: WebsiteConfig
    ) -> bool:
        """Check if configuration changes require a rebuild.

        Args:
            old_config: Previous configuration
            new_config: New configuration

        Returns:
            bool: True if rebuild is required
        """
        # Check significant changes that affect appearance
        significant_fields = [
            "theme",
            "primary_color",
            "secondary_color",
            "enabled_sections",
            "section_order",
            "chatbot_enabled",
            "chatbot_welcome_message",
        ]

        for field in significant_fields:
            if getattr(old_config, field) != getattr(new_config, field):
                return True

        return False
