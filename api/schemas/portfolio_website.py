"""Portfolio website schemas for deployment and management."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


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


class DeploymentStatus(BaseModel):
    """Deployment status information."""

    status: str = Field(
        description="Deployment status: pending, building, success, failed"
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
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Error information
    error_message: Optional[str] = None
    error_code: Optional[str] = None

    model_config = {"validate_assignment": True}


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
    suggested_alternatives: List[str] = Field(default=[])


class WebsiteAnalytics(BaseModel):
    """Website analytics data."""

    page_views: int = Field(default=0)
    unique_visitors: int = Field(default=0)
    bounce_rate: float = Field(default=0.0)
    avg_session_duration: float = Field(default=0.0)  # in seconds
    top_pages: List[Dict[str, int]] = Field(default=[])
    traffic_sources: Dict[str, int] = Field(default={})

    # Time period
    period_start: datetime
    period_end: datetime

    model_config = {"validate_assignment": True}
