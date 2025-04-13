"""Resume model for MongoDB using Beanie ODM."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field

from .portfolio import Portfolio
from .profile import Profile
from .user import User


class ResumeSection(BaseModel):
    """Base class for resume sections."""

    title: str
    content: str
    order: int = 0
    is_visible: bool = True

    model_config = {"validate_assignment": True}


class LLMSettings(BaseModel):
    """LLM settings for resume generation."""

    model_type: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    p_value: Optional[float] = None
    max_tokens: Optional[int] = None
    system_prompt_version: Optional[str] = None

    model_config = {"validate_assignment": True}


class Resume(Document):
    """Resume model for MongoDB using Beanie ODM."""

    user_id: PydanticObjectId
    user: Optional[Link[User]] = None
    profile_id: PydanticObjectId
    profile: Optional[Link[Profile]] = None
    portfolio_id: PydanticObjectId
    portfolio: Optional[Link[Portfolio]] = None

    title: Optional[str] = "My Resume"
    version: Optional[int] = None
    template_id: Optional[str] = None

    # Job targeting information
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    job_description: str = Field(default="")

    # Content can be either structured data or LaTeX string
    content: Dict[str, Any] = Field(default_factory=dict)

    # Custom sections
    custom_sections: List[ResumeSection] = Field(default_factory=list)

    # Generated PDFs
    resume_pdf_key: Optional[str] = Field(
        default=None, description="S3 key for the resume PDF"
    )

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

        name = "resumes"
        use_state_management = True
        indexes = ["user_id", "profile_id", "portfolio_id"]
        bson_encoders = {
            datetime: lambda x: x,
        }
