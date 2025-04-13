"""CoverLetter model for MongoDB using Beanie ODM."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field

from .portfolio import Portfolio
from .profile import Profile
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
    user: Optional[Link[User]] = None
    profile_id: Optional[PydanticObjectId] = None
    profile: Optional[Link[Profile]] = None
    portfolio_id: Optional[PydanticObjectId] = None
    portfolio: Optional[Link[Portfolio]] = None

    title: str = "My Cover Letter"
    version: Optional[int] = None
    template_id: Optional[str] = "default"

    # Job targeting information
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    hiring_manager: Optional[str] = None
    job_description: Optional[str] = None

    # Content can be either structured data or LaTeX string
    content: Dict[str, Any] = Field(default_factory=dict)

    # Custom sections
    custom_sections: List[CoverLetterSection] = Field(default_factory=list)

    # Generated PDFs
    cover_letter_pdf_key: Optional[str] = Field(
        default=None, description="S3 key for the cover letter PDF"
    )

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
        indexes = ["user_id", "profile_id", "portfolio_id"]
        bson_encoders = {
            datetime: lambda x: x,
        }
