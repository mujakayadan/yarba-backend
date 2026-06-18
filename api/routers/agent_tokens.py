"""Agent access token management (JWT-only; PATs cannot mint PATs)."""

from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.dependencies.auth import CurrentActiveUser
from api.schemas.agent_token import AgentTokenCreate, AgentTokenCreated, AgentTokenInfo
from config.logging_config import get_logger
from core.database.factory import get_agent_access_token_repository
from core.models.agent_access_token import AgentAccessToken
from core.repositories.agent_access_token_repository import AgentAccessTokenRepository
from core.utils.agent_access_token import generate_raw_token, hash_token
from core.utils.object_id import require_object_id

router = APIRouter()
logger = get_logger(__name__)


def _reject_pat_caller(request: Request) -> None:
    if getattr(request.state, "auth_token_type", None) == "pat":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent tokens cannot manage other agent tokens",
        )


def _to_info(token: AgentAccessToken) -> AgentTokenInfo:
    return AgentTokenInfo(
        id=str(token.id),
        label=token.label,
        scopes=token.scopes,
        is_active=token.is_active,
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
        created_at=token.created_at,
    )


@router.post("", response_model=AgentTokenCreated, status_code=status.HTTP_201_CREATED)
async def create_agent_token(
    body: AgentTokenCreate,
    request: Request,
    current_user: CurrentActiveUser,
    token_repo: AgentAccessTokenRepository = Depends(get_agent_access_token_repository),
) -> AgentTokenCreated:
    """Create a personal access token for apply automation agents."""
    _reject_pat_caller(request)

    raw_token = generate_raw_token()
    expires_at = None
    if body.expires_in_days is not None:
        expires_at = datetime.now(UTC) + timedelta(days=body.expires_in_days)

    record = AgentAccessToken(
        token_hash=hash_token(raw_token),
        user_id=require_object_id(current_user.id),
        label=body.label,
        scopes=body.scopes,
        expires_at=expires_at,
    )
    await token_repo.create(record)
    logger.info("Created agent token %s for user %s", record.id, current_user.id)

    return AgentTokenCreated(
        id=str(record.id),
        label=record.label,
        scopes=record.scopes,
        expires_at=record.expires_at,
        raw_token=raw_token,
    )


@router.get("", response_model=list[AgentTokenInfo])
async def list_agent_tokens(
    request: Request,
    current_user: CurrentActiveUser,
    token_repo: AgentAccessTokenRepository = Depends(get_agent_access_token_repository),
) -> list[AgentTokenInfo]:
    """List agent tokens for the current user."""
    _reject_pat_caller(request)
    tokens = await token_repo.list_by_user(require_object_id(current_user.id))
    return [_to_info(token) for token in tokens]


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_agent_token(
    token_id: str,
    request: Request,
    current_user: CurrentActiveUser,
    token_repo: AgentAccessTokenRepository = Depends(get_agent_access_token_repository),
) -> None:
    """Revoke an agent access token."""
    _reject_pat_caller(request)

    record = await token_repo.get_by_id(PydanticObjectId(token_id))
    if not record or record.user_id != require_object_id(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Token not found"
        )

    record.is_active = False
    record.updated_at = datetime.now(UTC)
    await record.save()
