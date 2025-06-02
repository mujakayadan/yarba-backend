"""Portfolio website API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies.auth import get_current_user
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
from core.models.user import User
from core.services.portfolio_website_service import PortfolioWebsiteService

router = APIRouter(prefix="/portfolio-websites", tags=["Portfolio Websites"])


@router.post(
    "/create",
    response_model=PortfolioWebsiteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create portfolio website",
    description="Create a new portfolio website for the authenticated user.",
)
async def create_portfolio_website(
    request: PortfolioWebsiteRequest,
    custom_subdomain: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Create a new portfolio website."""
    try:
        website = await website_service.create_portfolio_website(
            user_id=current_user.id,
            config=request.config,
            custom_subdomain=custom_subdomain,
        )

        return PortfolioWebsiteResponse(
            website_url=website.get_website_url(),
            subdomain=website.subdomain,
            deployment_status=DeploymentStatus(
                status=website.deployment.status,
                deployment_url=website.deployment.deployment_url,
                s3_bucket_name=website.deployment.s3_bucket_name,
                cloudfront_distribution_id=website.deployment.cloudfront_distribution_id,
                cloudfront_domain=website.deployment.cloudfront_domain,
                build_id=website.deployment.build_id,
                created_at=website.deployment.created_at,
                started_at=website.deployment.started_at,
                completed_at=website.deployment.completed_at,
                error_message=website.deployment.error_message,
                error_code=website.deployment.error_code,
            ),
            config=request.config,
            last_updated=website.updated_at,
        )

    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/",
    response_model=Optional[PortfolioWebsiteResponse],
    summary="Get user's portfolio website",
    description="Get the portfolio website for the authenticated user.",
)
async def get_portfolio_website(
    current_user: User = Depends(get_current_user),
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Get user's portfolio website."""
    website = await website_service.get_portfolio_website(current_user.id)

    if not website:
        return None

    return PortfolioWebsiteResponse(
        website_url=website.get_website_url(),
        subdomain=website.subdomain,
        deployment_status=DeploymentStatus(
            status=website.deployment.status,
            deployment_url=website.deployment.deployment_url,
            s3_bucket_name=website.deployment.s3_bucket_name,
            cloudfront_distribution_id=website.deployment.cloudfront_distribution_id,
            cloudfront_domain=website.deployment.cloudfront_domain,
            build_id=website.deployment.build_id,
            created_at=website.deployment.created_at,
            started_at=website.deployment.started_at,
            completed_at=website.deployment.completed_at,
            error_message=website.deployment.error_message,
            error_code=website.deployment.error_code,
        ),
        config=PortfolioWebsiteConfig(
            theme=website.config.theme,
            primary_color=website.config.primary_color,
            secondary_color=website.config.secondary_color,
            meta_title=website.config.meta_title,
            meta_description=website.config.meta_description,
            meta_keywords=website.config.meta_keywords,
            social_media_enabled=website.config.social_media_enabled,
            custom_domain=website.config.custom_domain,
            enabled_sections=website.config.enabled_sections,
            section_order=website.config.section_order,
            contact_form_enabled=website.config.contact_form_enabled,
        ),
        last_updated=website.updated_at,
    )


@router.put(
    "/config",
    response_model=PortfolioWebsiteResponse,
    summary="Update website configuration",
    description="Update the configuration of the user's portfolio website.",
)
async def update_website_config(
    request: PortfolioWebsiteRequest,
    current_user: User = Depends(get_current_user),
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Update website configuration."""
    try:
        website = await website_service.update_website_config(
            user_id=current_user.id,
            config=request.config,
            force_rebuild=request.force_rebuild,
        )

        return PortfolioWebsiteResponse(
            website_url=website.get_website_url(),
            subdomain=website.subdomain,
            deployment_status=DeploymentStatus(
                status=website.deployment.status,
                deployment_url=website.deployment.deployment_url,
                s3_bucket_name=website.deployment.s3_bucket_name,
                cloudfront_distribution_id=website.deployment.cloudfront_distribution_id,
                cloudfront_domain=website.deployment.cloudfront_domain,
                build_id=website.deployment.build_id,
                created_at=website.deployment.created_at,
                started_at=website.deployment.started_at,
                completed_at=website.deployment.completed_at,
                error_message=website.deployment.error_message,
                error_code=website.deployment.error_code,
            ),
            config=request.config,
            last_updated=website.updated_at,
        )

    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/deploy",
    response_model=PortfolioWebsiteResponse,
    summary="Deploy portfolio website",
    description="Deploy or redeploy the user's portfolio website.",
)
async def deploy_website(
    force_rebuild: bool = False,
    current_user: User = Depends(get_current_user),
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Deploy or redeploy portfolio website."""
    try:
        website = await website_service.deploy_website(
            user_id=current_user.id,
            force_rebuild=force_rebuild,
        )

        return PortfolioWebsiteResponse(
            website_url=website.get_website_url(),
            subdomain=website.subdomain,
            deployment_status=DeploymentStatus(
                status=website.deployment.status,
                deployment_url=website.deployment.deployment_url,
                s3_bucket_name=website.deployment.s3_bucket_name,
                cloudfront_distribution_id=website.deployment.cloudfront_distribution_id,
                cloudfront_domain=website.deployment.cloudfront_domain,
                build_id=website.deployment.build_id,
                created_at=website.deployment.created_at,
                started_at=website.deployment.started_at,
                completed_at=website.deployment.completed_at,
                error_message=website.deployment.error_message,
                error_code=website.deployment.error_code,
            ),
            config=PortfolioWebsiteConfig(
                theme=website.config.theme,
                primary_color=website.config.primary_color,
                secondary_color=website.config.secondary_color,
                meta_title=website.config.meta_title,
                meta_description=website.config.meta_description,
                meta_keywords=website.config.meta_keywords,
                social_media_enabled=website.config.social_media_enabled,
                custom_domain=website.config.custom_domain,
                enabled_sections=website.config.enabled_sections,
                section_order=website.config.section_order,
                contact_form_enabled=website.config.contact_form_enabled,
            ),
            last_updated=website.updated_at,
        )

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

    return PortfolioWebsiteResponse(
        website_url=website.get_website_url(),
        subdomain=website.subdomain,
        deployment_status=DeploymentStatus(
            status=website.deployment.status,
            deployment_url=website.deployment.deployment_url,
            s3_bucket_name=website.deployment.s3_bucket_name,
            cloudfront_distribution_id=website.deployment.cloudfront_distribution_id,
            cloudfront_domain=website.deployment.cloudfront_domain,
            build_id=website.deployment.build_id,
            created_at=website.deployment.created_at,
            started_at=website.deployment.started_at,
            completed_at=website.deployment.completed_at,
            error_message=website.deployment.error_message,
            error_code=website.deployment.error_code,
        ),
        config=PortfolioWebsiteConfig(
            theme=website.config.theme,
            primary_color=website.config.primary_color,
            secondary_color=website.config.secondary_color,
            meta_title=website.config.meta_title,
            meta_description=website.config.meta_description,
            meta_keywords=website.config.meta_keywords,
            social_media_enabled=website.config.social_media_enabled,
            custom_domain=website.config.custom_domain,
            enabled_sections=website.config.enabled_sections,
            section_order=website.config.section_order,
            contact_form_enabled=website.config.contact_form_enabled,
        ),
        last_updated=website.updated_at,
    )


@router.delete(
    "/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete portfolio website",
    description="Delete the user's portfolio website and all associated resources.",
)
async def delete_website(
    current_user: User = Depends(get_current_user),
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Delete portfolio website."""
    try:
        success = await website_service.delete_website(current_user.id)

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
    current_user: User = Depends(get_current_user),
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Get deployment status."""
    website = await website_service.get_portfolio_website(current_user.id)

    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio website not found"
        )

    return DeploymentStatus(
        status=website.deployment.status,
        deployment_url=website.deployment.deployment_url,
        s3_bucket_name=website.deployment.s3_bucket_name,
        cloudfront_distribution_id=website.deployment.cloudfront_distribution_id,
        cloudfront_domain=website.deployment.cloudfront_domain,
        build_id=website.deployment.build_id,
        build_logs=website.deployment.build_logs,
        build_duration=website.deployment.build_duration,
        created_at=website.deployment.created_at,
        started_at=website.deployment.started_at,
        completed_at=website.deployment.completed_at,
        error_message=website.deployment.error_message,
        error_code=website.deployment.error_code,
    )


@router.get(
    "/analytics",
    response_model=WebsiteAnalytics,
    summary="Get website analytics",
    description="Get analytics data for the user's portfolio website.",
)
async def get_website_analytics(
    current_user: User = Depends(get_current_user),
    website_service: PortfolioWebsiteService = Depends(get_portfolio_website_service),
):
    """Get website analytics."""
    website = await website_service.get_portfolio_website(current_user.id)

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
