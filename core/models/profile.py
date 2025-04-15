"""Profile model for MongoDB using Beanie ODM."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field

from config.settings import settings

from .user import User


class LLMUsage(BaseModel):
    """LLM usage and cost tracking for users."""

    # Summary of total usage
    total_tokens: int = Field(default=0, description="Total number of tokens used")
    total_input_tokens: int = Field(
        default=0, description="Total number of input tokens"
    )
    total_output_tokens: int = Field(
        default=0, description="Total number of output tokens"
    )
    total_cost: float = Field(default=0.0, description="Total cost in USD")

    # Breakdown by model
    usage_by_model: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Usage breakdown by model: {model_name: {tokens: count, cost: amount}}",
    )

    # Breakdown by operation type
    usage_by_operation: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Usage breakdown by operation type: {operation: {tokens: count, cost: amount}}",
    )

    # Usage limits and quotas
    monthly_quota: Optional[int] = Field(
        default=None, description="Monthly token quota (None means unlimited)"
    )
    monthly_cost_limit: Optional[float] = Field(
        default=None, description="Monthly cost limit in USD (None means unlimited)"
    )

    # Time-based tracking
    last_used: Optional[datetime] = Field(
        default=None, description="Last time LLM was used"
    )
    current_month_tokens: int = Field(
        default=0, description="Tokens used in current month"
    )
    current_month_cost: float = Field(
        default=0.0, description="Cost accumulated in current month"
    )

    # Historical usage by month - format: {'YYYY-MM': {'tokens': count, 'cost': amount}}
    monthly_history: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Historical usage by month: {'YYYY-MM': {'tokens': count, 'cost': amount}}",
    )

    model_config = {"validate_assignment": True}


class Preferences(BaseModel):
    """User preferences model."""

    # Project preferences
    project_details: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_projects": settings.preferences.project_max_projects,
            "bullet_points_per_project": settings.preferences.project_bullet_points_per_project,
        }
    )

    # Work experience preferences
    work_experience_details: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_jobs": settings.preferences.work_experience_max_jobs,
            "bullet_points_per_job": settings.preferences.work_experience_bullet_points_per_job,
        }
    )

    # Skills preferences
    skills_details: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_categories": settings.preferences.skills_max_categories,
            "min_skills_per_category": settings.preferences.skills_min_per_category,
            "max_skills_per_category": settings.preferences.skills_max_per_category,
        }
    )

    # Career summary preferences
    career_summary_details: Dict[str, Any] = Field(
        default_factory=lambda: {
            "min_words": settings.preferences.career_summary_min_words,
            "max_words": settings.preferences.career_summary_max_words,
        }
    )

    # Education preferences
    education_details: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_entries": settings.preferences.education_max_entries,
            "max_courses": settings.preferences.education_max_courses,
        }
    )

    # Other section preferences
    cover_letter_details: Dict[str, Any] = Field(
        default_factory=lambda: {
            "paragraphs": settings.preferences.cover_letter_paragraphs,
            "target_age": settings.preferences.cover_letter_target_grade_level,
        }
    )
    awards_details: Dict[str, Any] = Field(
        default_factory=lambda: {"max_awards": settings.preferences.awards_max_awards}
    )
    publications_details: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_publications": settings.preferences.publications_max_publications
        }
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
            "model_name": settings.llm.default_model,
            "temperature": settings.llm.temperature,
        }
    )

    # Section processing preferences
    section_preferences: Dict[str, str] = Field(
        default_factory=lambda: settings.preferences.section_preferences.copy()
    )

    # LaTeX template preferences
    default_latex_templates: Dict[str, str] = Field(
        default_factory=lambda: settings.preferences.default_latex_templates.copy(),
        description="LaTeX template IDs for resume and cover letter generation",
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
    signature_key: Optional[str] = Field(
        default=None, description="S3 key for the user's signature"
    )
    life_story: Optional[str] = None
    profile_picture_key: Optional[str] = Field(
        default=None, description="S3 key for the profile picture"
    )

    # API Keys configuration
    api_keys: Dict[str, str] = Field(
        default_factory=dict, description="Hashed API keys for various services"
    )

    # User preferences
    preferences: Preferences = Field(default_factory=Preferences)

    # LLM usage tracking
    llm_usage: LLMUsage = Field(
        default_factory=LLMUsage, description="LLM usage and cost tracking"
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

        name = "profiles"
        use_state_management = True
        bson_encoders = {
            datetime: lambda dt: (
                dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
            ),
        }
