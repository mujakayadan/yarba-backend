"""Portfolio site token model for public read-only portfolio access."""

from datetime import UTC, datetime

from beanie import Document, PydanticObjectId
from pydantic import Field

from core.models.document_config import BSON_DATETIME_ENCODERS


class PortfolioSiteToken(Document):
    """Read-only site token bound to a user's portfolio."""

    token_hash: str = Field(description="SHA-256 hash of the raw token")
    user_id: PydanticObjectId = Field(description="Owner user ID")
    portfolio_id: PydanticObjectId | None = Field(
        default=None, description="Optional linked portfolio ID"
    )
    label: str = Field(default="", description="Human-readable label, e.g. site domain")
    scopes: list[str] = Field(
        default_factory=lambda: ["portfolio:read"],
        description="Granted scopes",
    )
    is_active: bool = Field(default=True, description="Whether the token is valid")
    last_used_at: datetime | None = Field(
        default=None, description="Last successful use timestamp"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "portfolio_site_tokens"
        indexes = ["token_hash", "user_id"]
        bson_encoders = BSON_DATETIME_ENCODERS
