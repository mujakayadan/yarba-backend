"""Portfolio website model for MongoDB using Beanie ODM."""

import os
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from beanie import Document, Indexed, Link, PydanticObjectId
from pydantic import BaseModel, Field, HttpUrl

from core.models.document_config import BSON_DATETIME_ENCODERS, NESTED_MODEL_CONFIG
from core.models.portfolio import Portfolio
from core.models.user import User


class ModerationStatus(StrEnum):
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    SUSPENDED = "suspended"


class WebsiteConfig(BaseModel):
    """Website configuration embedded document."""

    theme: str = Field(default="modern", description="Website theme to use")
    primary_color: str = Field(
        default="#3B82F6", description="Primary color for the theme"
    )
    secondary_color: str = Field(
        default="#1F2937", description="Secondary color for the theme"
    )

    # SEO Configuration
    meta_title: str | None = None
    meta_description: str | None = None
    meta_keywords: list[str] = Field(default=[])

    # Social Media Configuration
    social_media_enabled: bool = Field(default=True)

    # Sections Configuration
    enabled_sections: list[str] = Field(
        default=["about", "experience", "education", "skills", "projects", "contact"],
        description="List of enabled sections on the portfolio",
    )
    section_order: list[str] = Field(
        default=["about", "experience", "education", "skills", "projects", "contact"],
        description="Order of sections on the portfolio",
    )

    # Contact Configuration
    contact_form_enabled: bool = Field(default=True)

    # Chatbot Configuration
    chatbot_enabled: bool = Field(
        default=False,
        description="Whether the portfolio chatbot widget is shown on the site",
    )
    chatbot_welcome_message: str | None = Field(
        default=None,
        description="Optional custom welcome message for the chatbot",
    )
    chatbot_store_conversations: bool = Field(
        default=False,
        description="Whether visitor chat messages are stored for owner review",
    )

    model_config = NESTED_MODEL_CONFIG


class DeploymentInfo(BaseModel):
    """Deployment information embedded document."""

    status: str = Field(
        default="pending",
        description="Deployment status: pending, building, success, failed",
    )
    deployment_url: HttpUrl | None = None
    s3_bucket_name: str | None = None
    cloudfront_distribution_id: str | None = None
    cloudfront_domain: str | None = None

    # Build information
    build_id: str | None = None
    build_logs: str | None = None
    build_duration: int | None = None  # in seconds

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Error information
    error_message: str | None = None
    error_code: str | None = None

    model_config = NESTED_MODEL_CONFIG


class WebsiteAnalytics(BaseModel):
    """Website analytics embedded document."""

    page_views: int = Field(default=0)
    unique_visitors: int = Field(default=0)
    bounce_rate: float = Field(default=0.0)
    avg_session_duration: float = Field(default=0.0)  # in seconds
    top_pages: list[dict[str, int]] = Field(default=[])
    traffic_sources: dict[str, int] = Field(default={})

    # Time period
    period_start: datetime = Field(default_factory=lambda: datetime.now(UTC))
    period_end: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = NESTED_MODEL_CONFIG


class PortfolioWebsite(Document):
    """Portfolio website model for storing website information and deployment status."""

    user_id: PydanticObjectId = Field(
        description="ID of the user who owns this portfolio website."
    )
    portfolio_id: PydanticObjectId = Field(
        description="ID of the portfolio associated with this website."
    )

    # Relationships
    user: Link[User] | None = None
    portfolio: Link[Portfolio] | None = None

    # Website identification
    subdomain: Annotated[str, Indexed(unique=True)] = Field(
        description="Subdomain for the portfolio website (e.g., 'johnsmith')",
    )

    # Website configuration
    config: WebsiteConfig = Field(
        default_factory=WebsiteConfig,
        description="Website configuration and customization settings",
    )

    # Deployment information
    deployment: DeploymentInfo = Field(
        default_factory=DeploymentInfo,
        description="Current deployment status and information",
    )

    # Analytics
    analytics: WebsiteAnalytics = Field(
        default_factory=WebsiteAnalytics,
        description="Website analytics and traffic data",
    )

    # Status flags
    is_published: bool = Field(
        default=False, description="Whether the website is published and accessible"
    )
    is_indexable: bool = Field(
        default=True, description="Whether search engines can index this website"
    )
    moderation_status: ModerationStatus = ModerationStatus.ACTIVE
    moderation_message: str | None = None
    suspended_at: datetime | None = None
    suspension_reason: str | None = None
    clean_redeploy_required: bool = False

    # Cache information
    last_build_hash: str | None = Field(
        default=None,
        description="Hash of the portfolio data when last built (for cache invalidation)",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the portfolio website was created.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the portfolio website was last updated.",
    )
    last_deployed_at: datetime | None = Field(
        default=None, description="When the website was last successfully deployed."
    )

    class Settings:
        """Beanie document settings."""

        name = "portfolio_websites"
        use_state_management = True
        indexes = [
            "user_id",
            "portfolio_id",
            "subdomain",
            "is_published",
            ("user_id", "subdomain"),  # Compound index for efficient queries
        ]
        bson_encoders = BSON_DATETIME_ENCODERS

    def get_website_url(self) -> str:
        """Get the full website URL."""
        # Custom domains are not currently processed, so always use the subdomain-based URL.
        domain_name = os.getenv("VERCEL_DOMAIN_NAME", "yarba.app")
        return f"https://{self.subdomain}.{domain_name}"

    def generate_subdomain_from_name(self, full_name: str) -> str:
        """Generate a subdomain from the user's full name."""
        import re

        # Clean the name and convert to lowercase
        clean_name = re.sub(r"[^a-zA-Z\s]", "", full_name.lower())
        # Remove extra spaces and join
        subdomain = "".join(clean_name.split())

        # Ensure it's not empty and has reasonable length
        if not subdomain or len(subdomain) < 3:
            subdomain = f"user{str(self.user_id)[-6:]}"
        elif len(subdomain) > 63:  # DNS subdomain limit
            subdomain = subdomain[:63]

        return subdomain
