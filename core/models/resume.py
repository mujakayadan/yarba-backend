"""Resume model for MongoDB using Beanie ODM."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field

from .user import User
from .profile import Profile
from .portfolio import Portfolio


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
    portfolio_id: Optional[PydanticObjectId] = None
    portfolio: Optional[Link[Portfolio]] = None

    title: str = "My Resume"
    version: int = 1
    template_id: str = "default"

    # Job targeting information
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    job_description: Optional[str] = None

    # Content can be either structured data or LaTeX string
    content: Dict[str, Any] = Field(default_factory=dict)

    # Custom sections
    custom_sections: List[ResumeSection] = Field(default_factory=list)

    # Generated PDFs
    resume_pdf: Optional[bytes] = None
    cover_letter_content: Optional[str] = None
    cover_letter_pdf: Optional[bytes] = None

    # AI generation parameters
    llm_settings: LLMSettings = Field(default_factory=LLMSettings)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

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

    async def get_user(self):
        """Get the user associated with this resume."""
        if not self.user:
            self.user = await User.get(self.user_id)
        return self.user

    async def get_profile(self):
        """Get the profile associated with this resume."""
        if not self.profile:
            self.profile = await Profile.get(self.profile_id)
        return self.profile

    async def get_portfolio(self):
        """Get the portfolio associated with this resume."""
        if not self.portfolio and self.portfolio_id:
            self.portfolio = await Portfolio.get(self.portfolio_id)
        return self.portfolio
