"""Schemas for agent access token management."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.models.agent_access_token import VALID_SCOPES


class AgentTokenCreate(BaseModel):
    """Request to create a new agent access token."""

    label: str = Field(..., min_length=1, max_length=128)
    scopes: list[str] = Field(..., min_length=1)
    expires_in_days: int | None = Field(default=90, ge=1, le=365)

    model_config = ConfigDict(extra="forbid")

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, scopes: list[str]) -> list[str]:
        invalid = set(scopes) - VALID_SCOPES
        if invalid:
            raise ValueError(f"Invalid scopes: {sorted(invalid)}")
        return scopes


class AgentTokenCreated(BaseModel):
    """Response when a token is created (raw token shown once)."""

    id: str
    label: str
    scopes: list[str]
    expires_at: datetime | None
    raw_token: str

    model_config = ConfigDict(extra="forbid")


class AgentTokenInfo(BaseModel):
    """Token metadata without secrets."""

    id: str
    label: str
    scopes: list[str]
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(extra="forbid")
