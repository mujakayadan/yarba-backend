"""Profile model for MongoDB using Beanie ODM."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field

from .user import User


class Preferences(BaseModel):
    """User preferences model."""

    # Project preferences
    project_details: Dict[str, Any] = Field(
        default_factory=lambda: {"max_projects": 4, "bullet_points_per_project": 3}
    )

    # Work experience preferences
    work_experience_details: Dict[str, Any] = Field(
        default_factory=lambda: {"max_jobs": 4, "bullet_points_per_job": 3}
    )

    # Skills preferences
    skills_details: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_categories": 5,
            "min_skills_per_category": 3,
            "max_skills_per_category": 10,
        }
    )

    # Career summary preferences
    career_summary_details: Dict[str, Any] = Field(
        default_factory=lambda: {"min_words": 15, "max_words": 25}
    )

    # Education preferences
    education_details: Dict[str, Any] = Field(
        default_factory=lambda: {"max_entries": 3, "max_courses": 4}
    )

    # Other section preferences
    cover_letter_details: Dict[str, Any] = Field(
        default_factory=lambda: {"paragraphs": 5, "target_age": 25}
    )
    awards_details: Dict[str, Any] = Field(default_factory=lambda: {"max_awards": 4})
    publications_details: Dict[str, Any] = Field(
        default_factory=lambda: {"max_publications": 3}
    )

    # Feature preferences
    feature_preferences: Dict[str, bool] = Field(
        default_factory=lambda: {
            "check_clearance": True,
            "auto_save": True,
            "dark_mode": False,
        }
    )

    # Notification preferences
    notifications: Dict[str, Any] = Field(default_factory=dict)

    # Privacy preferences
    privacy: Dict[str, Any] = Field(default_factory=dict)

    # LLM preferences
    llm_preferences: Dict[str, Any] = Field(
        default_factory=lambda: {
            "model_type": "Claude",
            "model_name": "claude-3-5-sonnet-20240620",
            "temperature": 0.1,
        }
    )

    # Section processing preferences
    section_preferences: Dict[str, str] = Field(
        default_factory=lambda: {
            "personal_information": "Hardcode",
            "career_summary": "Process",
            "skills": "Process",
            "work_experience": "Process",
            "education": "Process",
            "projects": "Process",
            "awards": "Hardcode",
            "publications": "Hardcode",
        }
    )

    model_config = {"validate_assignment": True}


class PersonalInformation(BaseModel):
    """Personal information model."""

    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None

    model_config = {"validate_assignment": True}


class Profile(Document):
    """Profile model for MongoDB using Beanie ODM."""

    user_id: PydanticObjectId
    user: Optional[Link[User]] = None

    # Personal information
    personal_information: PersonalInformation

    # Additional information
    signature: Optional[bytes] = None
    life_story: Optional[str] = None

    # API Keys configuration
    supported_api_keys: List[str] = Field(
        default=[
            "OPENAI_API_KEY",
            "GEMINI_API_KEY",
            "ANTHROPIC_API_KEY",
            "MISTRAL_API_KEY",
        ],
        description="List of supported API key types",
    )
    api_keys: Dict[str, str] = Field(
        default_factory=dict, description="Hashed API keys for various services"
    )

    # User preferences
    preferences: Preferences = Field(default_factory=Preferences)

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

        name = "profiles"
        use_state_management = True
        bson_encoders = {
            datetime: lambda x: x,
        }
