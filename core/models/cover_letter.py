"""CoverLetter model for MongoDB using Beanie ODM."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from beanie import Document, Link, PydanticObjectId
from pydantic import Field

from .portfolio import Portfolio
from .profile import Profile
from .resume import LLMSettings, Resume
from .user import User


class CoverLetter(Document):
    """CoverLetter model for MongoDB using Beanie ODM."""

    user_id: PydanticObjectId
    user: Optional[Link[User]] = None
    profile_id: PydanticObjectId
    profile: Optional[Link[Profile]] = None
    portfolio_id: Optional[PydanticObjectId] = None
    portfolio: Optional[Link[Portfolio]] = None
    resume_id: Optional[PydanticObjectId] = None
    resume: Optional[Link[Resume]] = None

    title: Optional[str] = "My Cover Letter"
    version: Optional[int] = None
    template_id: Optional[str] = "default"

    # Job targeting information
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    job_description: str = Field(default="")

    # Content can be either structured data or LaTeX string
    content: Dict[str, Any] = Field(default_factory=dict)
    cover_letter_content: Optional[str] = None
    cover_letter_pdf: Optional[bytes] = None

    # AI generation parameters
    llm_settings: LLMSettings = Field(default_factory=LLMSettings)

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
            datetime: lambda x: x,
        }
