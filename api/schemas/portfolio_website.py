"""Portfolio website schemas for deployment and management."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

NESTED_MODEL_CONFIG = ConfigDict(validate_assignment=True)


class PortfolioWebsiteConfig(BaseModel):
    """Configuration for portfolio website generation."""

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

    model_config = NESTED_MODEL_CONFIG


class DeploymentStatus(BaseModel):
    """Deployment status information."""

    status: str = Field(
        description="Deployment status: pending, building, success, failed"
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
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Error information
    error_message: str | None = None
    error_code: str | None = None

    model_config = NESTED_MODEL_CONFIG


class PortfolioWebsiteRequest(BaseModel):
    """Request schema for portfolio website operations."""

    config: PortfolioWebsiteConfig = Field(default_factory=PortfolioWebsiteConfig)
    force_rebuild: bool = Field(
        default=False, description="Force rebuild even if no changes"
    )


class PortfolioWebsiteResponse(BaseModel):
    """Response schema for portfolio website operations."""

    website_url: HttpUrl
    subdomain: str
    deployment_status: DeploymentStatus
    config: PortfolioWebsiteConfig
    last_updated: datetime


class SubdomainAvailabilityResponse(BaseModel):
    """Response for subdomain availability check."""

    subdomain: str
    available: bool
    suggested_alternatives: list[str] = Field(default=[])


class WebsiteAnalytics(BaseModel):
    """Website analytics data."""

    page_views: int = Field(default=0)
    unique_visitors: int = Field(default=0)
    bounce_rate: float = Field(default=0.0)
    avg_session_duration: float = Field(default=0.0)  # in seconds
    top_pages: list[dict[str, int]] = Field(default=[])
    traffic_sources: dict[str, int] = Field(default={})

    # Time period
    period_start: datetime
    period_end: datetime

    model_config = NESTED_MODEL_CONFIG
