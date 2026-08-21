"""Public portfolio content API (site-token authenticated)."""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from api.dependencies.services import (
    get_portfolio_chat_service,
    get_public_portfolio_service,
)
from api.schemas.portfolio_chat import PortfolioChatRequest, PortfolioChatResponse
from api.schemas.public_portfolio import PublicPortfolioContent
from api.schemas.safety import AbuseReportRequest, AbuseReportResponse
from core.exceptions.base import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from core.services.moderation_service import ModerationService
from core.services.portfolio_chat_service import (
    ChatVisitorMetadata,
    PortfolioChatService,
)
from core.services.public_portfolio_service import PublicPortfolioService

router = APIRouter(prefix="/public/portfolio", tags=["public-portfolio"])

PORTFOLIO_SITE_TOKEN_HEADER = "X-Portfolio-Site-Token"


def get_moderation_service() -> ModerationService:
    return ModerationService()


@router.post("/reports", response_model=AbuseReportResponse, status_code=202)
async def submit_abuse_report(
    body: AbuseReportRequest,
    request: Request,
    service: ModerationService = Depends(get_moderation_service),
) -> AbuseReportResponse:
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = (
        forwarded.split(",", 1)[0].strip()
        if forwarded
        else (request.client.host if request.client else "unknown")
    )
    return await service.submit_report(body, client_ip)


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
    request: Request,
    service: PortfolioChatService = Depends(get_portfolio_chat_service),
) -> PortfolioChatResponse:
    """Chat with a portfolio website's AI assistant."""
    visitor_metadata = ChatVisitorMetadata(
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer"),
    )
    try:
        return await service.chat(body, visitor_metadata=visitor_metadata)
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
