"""Profile model for MongoDB using Beanie ODM."""

from datetime import UTC, datetime
from typing import Any

from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field

from config.settings import settings
from core.models.document_config import (
    BSON_DATETIME_ENCODERS,
    DOCUMENT_MODEL_CONFIG,
    NESTED_MODEL_CONFIG,
)

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
    usage_by_model: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Usage breakdown by model: {model_name: {tokens: count, cost: amount}}",
    )

    # Breakdown by operation type
    usage_by_operation: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Usage breakdown by operation type: {operation: {tokens: count, cost: amount}}",
    )

    # Usage limits and quotas
    monthly_quota: int | None = Field(
        default=None, description="Monthly token quota (None means unlimited)"
    )
    monthly_cost_limit: float | None = Field(
        default=None, description="Monthly cost limit in USD (None means unlimited)"
    )

    # Time-based tracking
    last_used: datetime | None = Field(
        default=None, description="Last time LLM was used"
    )
    current_month_tokens: int = Field(
        default=0, description="Tokens used in current month"
    )
    current_month_cost: float = Field(
        default=0.0, description="Cost accumulated in current month"
    )

    # Historical usage by month - format: {'YYYY-MM': {'tokens': count, 'cost': amount}}
    monthly_history: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Historical usage by month: {'YYYY-MM': {'tokens': count, 'cost': amount}}",
    )

    model_config = NESTED_MODEL_CONFIG


class PromptPreferences(BaseModel):
    """Preferences specifically for LLM prompt generation and content control."""

    # Project preferences
    project: dict[str, Any] = Field(
        default_factory=dict, description="Project section preferences"
    )

    # Work experience preferences
    work_experience: dict[str, Any] = Field(
        default_factory=dict, description="Work experience section preferences"
    )

    # Skills preferences
    skills: dict[str, Any] = Field(
        default_factory=dict, description="Skills section preferences"
    )

    # Career summary preferences
    career_summary: dict[str, Any] = Field(
        default_factory=dict, description="Career summary section preferences"
    )

    # Education preferences
    education: dict[str, Any] = Field(
        default_factory=dict, description="Education section preferences"
    )

    # Cover letter preferences
    cover_letter: dict[str, Any] = Field(
        default_factory=dict, description="Cover letter section preferences"
    )

    # Awards preferences
    awards: dict[str, Any] = Field(
        default_factory=dict, description="Awards section preferences"
    )

    # Publications preferences
    publications: dict[str, Any] = Field(
        default_factory=dict, description="Publications section preferences"
    )

    model_config = NESTED_MODEL_CONFIG


class SystemPreferences(BaseModel):
    """System-related preferences for UI, features, etc."""

    # Feature preferences
    features: dict[str, bool] = Field(
        default_factory=lambda: {
            "check_clearance": True,
            "auto_save": True,
            "dark_mode": False,
        },
        description="Feature toggle preferences",
    )

    # Notification preferences
    notifications: dict[str, Any] = Field(
        default_factory=dict, description="Notification preferences"
    )

    # Privacy preferences
    privacy: dict[str, Any] = Field(
        default_factory=dict, description="Privacy preferences"
    )

    # LLM preferences
    llm: dict[str, Any] = Field(
        default_factory=lambda: {
            "model_name": settings.llm.default_model,
            "temperature": settings.llm.temperature,
        },
        description="LLM configuration preferences",
    )

    # LaTeX template preferences
    templates: dict[str, str] = Field(
        default_factory=lambda: settings.preferences.default_latex_templates.copy(),
        description="LaTeX template IDs for resume and cover letter generation",
    )

    model_config = NESTED_MODEL_CONFIG


class PersonalInformation(BaseModel):
    """Personal information model."""

    full_name: str | None = None
    email: EmailStr
    phone: str | None = None
    address: str | None = None
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None

    model_config = NESTED_MODEL_CONFIG


class FlatPreference:
    """A simple class to provide dot-notation access to flat preferences.

    This allows direct access to preferences like:
    - profile.flat_prefs.project_max_projects
    - profile.flat_prefs.career_summary_min_words
    """

    def __init__(self, profile: "Profile"):
        """Initialize with a profile object."""
        self._profile = profile

    def __getattr__(self, name: str) -> Any:
        """Get a preference value using flat dot notation.

        Checks in the following order:
        1. prompt_preferences (new structure)
        2. system_preferences (new structure)
        3. Returns None if not found
        """
        # Map from flat_name to section/key
        parts = name.split("_", 1)

        if len(parts) < 2:
            raise AttributeError(f"Invalid preference name: {name}")

        section, key = parts[0], parts[1]

        # Try new structure first (prompt_preferences)
        prompt_prefs = getattr(self._profile, "prompt_preferences", None)
        if prompt_prefs and hasattr(prompt_prefs, section):
            section_dict = getattr(prompt_prefs, section, {})
            if section_dict and key in section_dict:
                return section_dict.get(key)

        # Try system_preferences
        system_prefs = getattr(self._profile, "system_preferences", None)
        if system_prefs and hasattr(system_prefs, section):
            section_dict = getattr(system_prefs, section, {})
            if section_dict and key in section_dict:
                return section_dict.get(key)

        # Try system_preferences.templates directly for default template IDs
        # e.g., flat_prefs.default_resume_template_id
        if section == "default" and system_prefs and hasattr(system_prefs, "templates"):
            template_key = f"{section}_{key}"  # e.g., default_resume_template_id
            templates_dict = getattr(system_prefs, "templates", {})
            if templates_dict and template_key in templates_dict:
                return templates_dict.get(template_key)

        # Try system_preferences.features directly for feature flags
        # e.g., flat_prefs.check_clearance
        if system_prefs and hasattr(system_prefs, "features"):
            features_dict = getattr(system_prefs, "features", {})
            if features_dict and name in features_dict:  # Check the original flat name
                return features_dict.get(name)

        # If not found in new structures, return None or raise error?
        # For now, returning None to avoid breaking existing code expecting None
        return None

    def get(self, name: str, default: Any = None) -> Any:
        """Get preference with a default fallback value."""
        try:
            value = getattr(self, name)
            return value if value is not None else default
        except (AttributeError, KeyError):
            return default


class Profile(Document):
    """Profile model for MongoDB using Beanie ODM."""

    user_id: PydanticObjectId
    user: Link[User] | None = None

    # Personal information
    personal_information: PersonalInformation

    # Additional information
    signature_key: str | None = Field(
        default=None, description="S3 key for the user's signature"
    )
    life_story: str | None = None
    profile_picture_key: str | None = Field(
        default=None, description="S3 key for the profile picture"
    )

    # API Keys configuration
    api_keys: dict[str, str] = Field(
        default_factory=dict, description="Hashed API keys for various services"
    )

    # New preference structure
    prompt_preferences: PromptPreferences = Field(
        default_factory=PromptPreferences,
        description="Preferences specifically for LLM prompt generation and content control",
    )

    system_preferences: SystemPreferences = Field(
        default_factory=SystemPreferences,
        description="System-related preferences for UI, features, etc.",
    )

    # LLM usage tracking
    llm_usage: LLMUsage = Field(
        default_factory=LLMUsage, description="LLM usage and cost tracking"
    )

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = DOCUMENT_MODEL_CONFIG

    @property
    def flat_prefs(self) -> FlatPreference:
        """Provide direct access to preferences using dot notation.

        Example usage:
            profile.flat_prefs.project_max_projects  # access project.max_projects
            profile.flat_prefs.career_summary_min_words  # access career_summary.min_words
        """
        return FlatPreference(self)

    # Replace save methods with a pre_save hook
    async def on_save(self) -> None:
        """Pre-save hook to update timestamp."""
        self.updated_at = datetime.now(UTC)

    class Settings:
        """Beanie document settings."""

        name = "profiles"
        use_state_management = True
        bson_encoders = BSON_DATETIME_ENCODERS
