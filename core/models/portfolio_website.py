"""Portfolio website model for MongoDB using Beanie ODM."""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field, HttpUrl

from core.models.portfolio import Portfolio
from core.models.user import User


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
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: List[str] = Field(default=[])

    # Social Media Configuration
    social_media_enabled: bool = Field(default=True)

    # Sections Configuration
    enabled_sections: List[str] = Field(
        default=["about", "experience", "education", "skills", "projects", "contact"],
        description="List of enabled sections on the portfolio",
    )
    section_order: List[str] = Field(
        default=["about", "experience", "education", "skills", "projects", "contact"],
        description="Order of sections on the portfolio",
    )

    # Contact Configuration
    contact_form_enabled: bool = Field(default=True)

    model_config = {"validate_assignment": True}


class DeploymentInfo(BaseModel):
    """Deployment information embedded document."""

    status: str = Field(
        default="pending",
        description="Deployment status: pending, building, success, failed",
    )
    deployment_url: Optional[HttpUrl] = None
    s3_bucket_name: Optional[str] = None
    cloudfront_distribution_id: Optional[str] = None
    cloudfront_domain: Optional[str] = None

    # Build information
    build_id: Optional[str] = None
    build_logs: Optional[str] = None
    build_duration: Optional[int] = None  # in seconds

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Error information
    error_message: Optional[str] = None
    error_code: Optional[str] = None

    model_config = {"validate_assignment": True}


class WebsiteAnalytics(BaseModel):
    """Website analytics embedded document."""

    page_views: int = Field(default=0)
    unique_visitors: int = Field(default=0)
    bounce_rate: float = Field(default=0.0)
    avg_session_duration: float = Field(default=0.0)  # in seconds
    top_pages: List[Dict[str, int]] = Field(default=[])
    traffic_sources: Dict[str, int] = Field(default={})

    # Time period
    period_start: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"validate_assignment": True}


class PortfolioWebsite(Document):
    """Portfolio website model for storing website information and deployment status."""

    user_id: PydanticObjectId = Field(
        description="ID of the user who owns this portfolio website."
    )
    portfolio_id: PydanticObjectId = Field(
        description="ID of the portfolio associated with this website."
    )

    # Relationships
    user: Optional[Link[User]] = None
    portfolio: Optional[Link[Portfolio]] = None

    # Website identification
    subdomain: str = Field(
        description="Subdomain for the portfolio website (e.g., 'johnsmith')",
        unique=True,
        index=True,
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

    # Cache information
    last_build_hash: Optional[str] = Field(
        default=None,
        description="Hash of the portfolio data when last built (for cache invalidation)",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the portfolio website was created.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the portfolio website was last updated.",
    )
    last_deployed_at: Optional[datetime] = Field(
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
        bson_encoders = {
            datetime: lambda dt: (
                dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
            ),
        }

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
