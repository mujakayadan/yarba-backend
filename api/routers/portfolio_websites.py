"""Portfolio website API endpoints."""

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import HttpUrl

from api.dependencies.auth import CurrentUser
from api.dependencies.services import get_portfolio_website_service
from api.schemas.portfolio_website import (
    DeploymentStatus,
    PortfolioWebsiteConfig,
    PortfolioWebsiteRequest,
    PortfolioWebsiteResponse,
    SubdomainAvailabilityResponse,
    WebsiteAnalytics,
)
from core.exceptions.base import (
    ConflictException,
    DeploymentException,
    NotFoundException,
    ValidationException,
)
from core.models.portfolio_website import PortfolioWebsite, WebsiteConfig
from core.services.portfolio_website_service import PortfolioWebsiteService
from core.utils.object_id import require_object_id

router = APIRouter(prefix="/portfolio-websites", tags=["Portfolio Websites"])


def _to_website_config(config: PortfolioWebsiteConfig) -> WebsiteConfig:
    return WebsiteConfig.model_validate(config.model_dump())


def _to_portfolio_website_config(config: WebsiteConfig) -> PortfolioWebsiteConfig:
    return PortfolioWebsiteConfig.model_validate(config.model_dump())


def _build_deployment_status(website: PortfolioWebsite) -> DeploymentStatus:
    deployment = website.deployment
    deployment_url = deployment.deployment_url
    return DeploymentStatus(
        status=deployment.status,
        deployment_url=(
            cast(HttpUrl, str(deployment_url)) if deployment_url is not None else None
        ),
        s3_bucket_name=deployment.s3_bucket_name,
        cloudfront_distribution_id=deployment.cloudfront_distribution_id,
        cloudfront_domain=deployment.cloudfront_domain,
        build_id=deployment.build_id,
        build_logs=deployment.build_logs,
        build_duration=deployment.build_duration,
        created_at=deployment.created_at,
        started_at=deployment.started_at,
        completed_at=deployment.completed_at,
        error_message=deployment.error_message,
        error_code=deployment.error_code,
    )


def _build_portfolio_website_response(
    website: PortfolioWebsite,
    config: PortfolioWebsiteConfig | None = None,
) -> PortfolioWebsiteResponse:
    return PortfolioWebsiteResponse(
        website_url=HttpUrl(website.get_website_url()),
        subdomain=website.subdomain,
        deployment_status=_build_deployment_status(website),
        config=config or _to_portfolio_website_config(website.config),
        last_updated=website.updated_at,
    )


@router.post(
    "/create",
    response_model=PortfolioWebsiteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create portfolio website",
    description="Create a new portfolio website for the authenticated user.",
)
async def create_portfolio_website(
    request: PortfolioWebsiteRequest,
    current_user: CurrentUser,
    custom_subdomain: str | None = None,
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Create a new portfolio website."""
    try:
        website = await website_service.create_portfolio_website(
            user_id=require_object_id(current_user.id),
            config=_to_website_config(request.config),
            custom_subdomain=custom_subdomain,
        )

        return _build_portfolio_website_response(website, config=request.config)

    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/",
    response_model=PortfolioWebsiteResponse | None,
    summary="Get user's portfolio website",
    description="Get the portfolio website for the authenticated user.",
)
async def get_portfolio_website(
    response: Response,
    current_user: CurrentUser,
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Get user's portfolio website."""
    website = await website_service.get_portfolio_website(
        require_object_id(current_user.id)
    )

    if not website:
        response.headers["Cache-Control"] = "private, no-store"
        return None

    # Add caching headers based on deployment status
    if website.deployment.status in ["building"]:
        # Short cache for building status (5 seconds)
        response.headers["Cache-Control"] = "private, max-age=5, must-revalidate"
        response.headers["X-Recommended-Poll-Interval"] = "5"
    elif website.deployment.status in ["success", "failed"]:
        # Longer cache for completed states (30 seconds)
        response.headers["Cache-Control"] = "private, max-age=30"
        response.headers["X-Recommended-Poll-Interval"] = "30"
    else:
        # Default cache (10 seconds)
        response.headers["Cache-Control"] = "private, max-age=10"
        response.headers["X-Recommended-Poll-Interval"] = "10"

    return _build_portfolio_website_response(website)


@router.put(
    "/config",
    response_model=PortfolioWebsiteResponse,
    summary="Update website configuration",
    description="Update the configuration of the user's portfolio website.",
)
async def update_website_config(
    request: PortfolioWebsiteRequest,
    current_user: CurrentUser,
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Update website configuration."""
    try:
        website = await website_service.update_website_config(
            user_id=require_object_id(current_user.id),
            config=_to_website_config(request.config),
            force_rebuild=request.force_rebuild,
        )

        return _build_portfolio_website_response(website, config=request.config)

    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/deploy",
    response_model=PortfolioWebsiteResponse,
    summary="Deploy portfolio website",
    description="Deploy or redeploy the user's portfolio website.",
)
async def deploy_website(
    current_user: CurrentUser,
    force_rebuild: bool = False,
    clean_deploy: bool = False,
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Deploy or redeploy portfolio website.

    Args:
        force_rebuild: Force rebuild even if content hasn't changed
        clean_deploy: Delete all existing files and redeploy from scratch (like delete + create)
    """
    try:
        website = await website_service.deploy_website(
            user_id=require_object_id(current_user.id),
            force_rebuild=force_rebuild,
            clean_deploy=clean_deploy,
        )

        return _build_portfolio_website_response(website)

    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DeploymentException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment failed: {str(e)}",
        )


@router.get(
    "/subdomain/check/{subdomain}",
    response_model=SubdomainAvailabilityResponse,
    summary="Check subdomain availability",
    description="Check if a subdomain is available for use.",
)
async def check_subdomain_availability(
    subdomain: str,
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Check subdomain availability."""
    try:
        result = await website_service.check_subdomain_availability(subdomain)

        return SubdomainAvailabilityResponse(
            subdomain=result["subdomain"],
            available=result["available"],
            suggested_alternatives=result["suggested_alternatives"],
        )

    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/public/{subdomain}",
    response_model=PortfolioWebsiteResponse,
    summary="Get public portfolio website",
    description="Get a public portfolio website by subdomain (for public viewing).",
)
async def get_public_website(
    subdomain: str,
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Get public portfolio website by subdomain."""
    website = await website_service.get_website_by_subdomain(subdomain)

    if not website or not website.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio website not found or not published",
        )

    return _build_portfolio_website_response(website)


@router.delete(
    "/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete portfolio website",
    description="Delete the user's portfolio website and all associated resources.",
)
async def delete_website(
    current_user: CurrentUser,
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Delete portfolio website."""
    try:
        success = await website_service.delete_website(
            require_object_id(current_user.id)
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete website",
            )

    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/deployment-status",
    response_model=DeploymentStatus,
    summary="Get deployment status",
    description="Get the current deployment status of the user's portfolio website.",
)
async def get_deployment_status(
    response: Response,
    current_user: CurrentUser,
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Get deployment status."""
    website = await website_service.get_portfolio_website(
        require_object_id(current_user.id)
    )

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio website not found"
        )

    # Add caching headers based on deployment status
    if website.deployment.status in ["building"]:
        # Very short cache for building status (2 seconds)
        response.headers["Cache-Control"] = "private, max-age=2, must-revalidate"
        response.headers["X-Recommended-Poll-Interval"] = "2"
    elif website.deployment.status in ["success", "failed"]:
        # Longer cache for completed states (60 seconds)
        response.headers["Cache-Control"] = "private, max-age=60"
        response.headers["X-Recommended-Poll-Interval"] = "60"
    else:
        # Default cache (5 seconds)
        response.headers["Cache-Control"] = "private, max-age=5"
        response.headers["X-Recommended-Poll-Interval"] = "5"

    return _build_deployment_status(website)


@router.get(
    "/analytics",
    response_model=WebsiteAnalytics,
    summary="Get website analytics",
    description="Get analytics data for the user's portfolio website.",
)
async def get_website_analytics(
    current_user: CurrentUser,
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Get website analytics."""
    website = await website_service.get_portfolio_website(
        require_object_id(current_user.id)
    )

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio website not found"
        )

    return WebsiteAnalytics(
        page_views=website.analytics.page_views,
        unique_visitors=website.analytics.unique_visitors,
        bounce_rate=website.analytics.bounce_rate,
        avg_session_duration=website.analytics.avg_session_duration,
        top_pages=website.analytics.top_pages,
        traffic_sources=website.analytics.traffic_sources,
        period_start=website.analytics.period_start,
        period_end=website.analytics.period_end,
    )
