"""Public portfolio content API (site-token authenticated)."""

from fastapi import APIRouter, Depends, Header, HTTPException, status

from api.dependencies.services import get_public_portfolio_service
from api.schemas.public_portfolio import PublicPortfolioContent
from core.exceptions.base import NotFoundException, UnauthorizedException
from core.services.public_portfolio_service import PublicPortfolioService

router = APIRouter(prefix="/public/portfolio", tags=["public-portfolio"])

PORTFOLIO_SITE_TOKEN_HEADER = "X-Portfolio-Site-Token"


@router.get(
    "/content",
    response_model=PublicPortfolioContent,
    summary="Get public portfolio content",
    description=(
        "Return sanitized portfolio and profile data for an external portfolio site. "
        f"Requires the `{PORTFOLIO_SITE_TOKEN_HEADER}` header."
    ),
)
async def get_public_portfolio_content(
    x_portfolio_site_token: str | None = Header(
        default=None, alias=PORTFOLIO_SITE_TOKEN_HEADER
    ),
    service: PublicPortfolioService = Depends(get_public_portfolio_service),
) -> PublicPortfolioContent:
    """Get portfolio content for a validated site token."""
    try:
        return await service.get_content_by_token(x_portfolio_site_token or "")
    except UnauthorizedException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except NotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
