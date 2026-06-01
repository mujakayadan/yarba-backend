"""CoverLetter model for MongoDB using Beanie ODM."""

from datetime import UTC, datetime

from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field

from .portfolio import Portfolio
from .profile import Profile
from .resume import LLMUsageStats, Resume
from .user import User


class CoverLetterSection(BaseModel):
    """Base class for cover letter sections."""

    title: str
    content: str
    order: int = 0
    is_visible: bool = True

    model_config = {"validate_assignment": True}


class CoverLetter(Document):
    """CoverLetter model for MongoDB using Beanie ODM."""

    user_id: PydanticObjectId
    user: Link[User] | None = None
    profile_id: PydanticObjectId | None = None
    profile: Link[Profile] | None = None
    portfolio_id: PydanticObjectId | None = None
    portfolio: Link[Portfolio] | None = None
    resume_id: PydanticObjectId
    resume: Link["Resume"] | None = None

    template_id: str | None = "default"

    # Content - use a single field for the content
    content: str | None = None  # Changed from Dict[str, Any] to Optional[str]

    # Generated PDFs
    cover_letter_pdf_key: str | None = Field(
        default=None, description="S3 key for the cover letter PDF"
    )

    # LLM usage statistics for this specific cover letter
    llm_usage: LLMUsageStats = Field(
        default_factory=LLMUsageStats,
        description="LLM usage statistics for this cover letter",
    )

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {
        "validate_assignment": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda x: x.isoformat(),
        },
    }

    class Settings:
        """Beanie document settings."""

        name = "cover_letters"
        use_state_management = True
        indexes = ["user_id", "profile_id", "portfolio_id", "resume_id"]
        bson_encoders = {
            datetime: lambda dt: (dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt),
        }
