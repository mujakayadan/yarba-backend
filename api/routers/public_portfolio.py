"""Public portfolio content API (site-token authenticated)."""

from fastapi import APIRouter, Depends, Header, HTTPException, status

from api.dependencies.services import (
    get_portfolio_chat_service,
    get_public_portfolio_service,
)
from api.schemas.portfolio_chat import PortfolioChatRequest, PortfolioChatResponse
from api.schemas.public_portfolio import PublicPortfolioContent
from core.exceptions.base import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from core.services.portfolio_chat_service import PortfolioChatService
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


@router.post(
    "/chat",
    response_model=PortfolioChatResponse,
    summary="Chat with portfolio AI assistant",
    description=(
        "Send a message to the portfolio chatbot for a published subdomain. "
        "Requires chatbot to be enabled on the portfolio website."
    ),
)
async def portfolio_chat(
    body: PortfolioChatRequest,
    service: PortfolioChatService = Depends(get_portfolio_chat_service),
) -> PortfolioChatResponse:
    """Chat with a portfolio website's AI assistant."""
    try:
        return await service.chat(body)
    except BadRequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ForbiddenException as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except NotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
