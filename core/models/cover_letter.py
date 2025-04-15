"""CoverLetter model for MongoDB using Beanie ODM."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field

from .portfolio import Portfolio
from .profile import Profile
from .resume import Resume
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
    resume_id: PydanticObjectId
    resume: Optional[Link["Resume"]] = None

    template_id: Optional[str] = "default"

    # Content - use a single field for the content
    content: Dict[str, Any] = Field(default_factory=dict)  # Structured content

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

    # Fields used temporarily during LaTeX generation but not persisted
    company_name: Optional[str] = Field(default=None, exclude=True)
    job_title: Optional[str] = Field(default=None, exclude=True)
    cover_letter_content: Optional[str] = Field(default=None, exclude=True)
    name: Optional[str] = Field(default=None, exclude=True)
    phone: Optional[str] = Field(default=None, exclude=True)
    email: Optional[str] = Field(default=None, exclude=True)
    linkedin: Optional[str] = Field(default=None, exclude=True)
    github: Optional[str] = Field(default=None, exclude=True)
    website: Optional[str] = Field(default=None, exclude=True)
    address: Optional[str] = Field(default=None, exclude=True)

    class Settings:
        """Beanie document settings."""

        name = "cover_letters"
        use_state_management = True
        indexes = ["user_id", "profile_id", "portfolio_id", "resume_id"]
        bson_encoders = {
            datetime: lambda dt: (
                dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
            ),
        }
