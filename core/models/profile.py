"""Profile model for MongoDB using Beanie ODM."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from beanie import Document, Indexed, Link, PydanticObjectId
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


class PromptPreferences(BaseModel):
    """Preferences specifically for LLM prompt generation and content control."""

    # Project preferences
    project: Dict[str, Any] = Field(
        default_factory=dict, description="Project section preferences"
    )

    # Work experience preferences
    work_experience: Dict[str, Any] = Field(
        default_factory=dict, description="Work experience section preferences"
    )

    # Skills preferences
    skills: Dict[str, Any] = Field(
        default_factory=dict, description="Skills section preferences"
    )

    # Career summary preferences
    career_summary: Dict[str, Any] = Field(
        default_factory=dict, description="Career summary section preferences"
    )

    # Education preferences
    education: Dict[str, Any] = Field(
        default_factory=dict, description="Education section preferences"
    )

    # Cover letter preferences
    cover_letter: Dict[str, Any] = Field(
        default_factory=dict, description="Cover letter section preferences"
    )

    # Awards preferences
    awards: Dict[str, Any] = Field(
        default_factory=dict, description="Awards section preferences"
    )

    # Publications preferences
    publications: Dict[str, Any] = Field(
        default_factory=dict, description="Publications section preferences"
    )

    model_config = {"validate_assignment": True}


class SystemPreferences(BaseModel):
    """System-related preferences for UI, features, etc."""

    # Feature preferences
    features: Dict[str, bool] = Field(
        default_factory=lambda: {
            "check_clearance": True,
            "auto_save": True,
            "dark_mode": False,
        },
        description="Feature toggle preferences",
    )

    # Notification preferences
    notifications: Dict[str, Any] = Field(
        default_factory=dict, description="Notification preferences"
    )

    # Privacy preferences
    privacy: Dict[str, Any] = Field(
        default_factory=dict, description="Privacy preferences"
    )

    # LLM preferences
    llm: Dict[str, Any] = Field(
        default_factory=lambda: {
            "model_name": settings.llm.default_model,
            "temperature": settings.llm.temperature,
        },
        description="LLM configuration preferences",
    )

    # LaTeX template preferences
    templates: Dict[str, str] = Field(
        default_factory=lambda: settings.preferences.default_latex_templates.copy(),
        description="LaTeX template IDs for resume and cover letter generation",
    )

    model_config = {"validate_assignment": True}


class Preferences(BaseModel):
    """Legacy user preferences model, kept for backward compatibility."""

    # Project preferences - LEGACY
    project_details: Dict[str, Any] = Field(default_factory=dict)

    # Work experience preferences - LEGACY
    work_experience_details: Dict[str, Any] = Field(default_factory=dict)

    # Skills preferences - LEGACY
    skills_details: Dict[str, Any] = Field(default_factory=dict)

    # Career summary preferences - LEGACY
    career_summary_details: Dict[str, Any] = Field(default_factory=dict)

    # Education preferences - LEGACY
    education_details: Dict[str, Any] = Field(default_factory=dict)

    # Other section preferences - LEGACY
    cover_letter_details: Dict[str, Any] = Field(default_factory=dict)
    awards_details: Dict[str, Any] = Field(default_factory=dict)
    publications_details: Dict[str, Any] = Field(default_factory=dict)

    # Feature preferences - LEGACY
    feature_preferences: Dict[str, bool] = Field(default_factory=dict)

    # Notification preferences - LEGACY
    notifications: Dict[str, Any] = Field(default_factory=dict)

    # Privacy preferences - LEGACY
    privacy: Dict[str, Any] = Field(default_factory=dict)

    # LLM preferences - LEGACY
    llm_preferences: Dict[str, Any] = Field(default_factory=dict)

    # LaTeX template preferences - LEGACY
    default_latex_templates: Dict[str, str] = Field(
        default_factory=dict,
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


class FlatPreference:
    """
    A simple class to provide dot-notation access to flat preferences.

    This allows direct access to preferences like:
    - profile.flat_prefs.project_max_projects
    - profile.flat_prefs.career_summary_min_words
    """

    def __init__(self, profile: "Profile"):
        """Initialize with a profile object."""
        self._profile = profile

    def __getattr__(self, name: str) -> Any:
        """
        Get a preference value using flat dot notation.

        Checks in the following order:
        1. prompt_preferences (new structure)
        2. system_preferences (new structure)
        3. preferences (legacy structure)
        4. Returns None if not found
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

        # Try legacy structure
        legacy_prefs = getattr(self._profile, "preferences", None)
        if legacy_prefs:
            # Check with _details suffix
            section_details = f"{section}_details"
            if hasattr(legacy_prefs, section_details):
                section_dict = getattr(legacy_prefs, section_details, {})
                if section_dict and key in section_dict:
                    return section_dict.get(key)

            # Check without suffix
            if hasattr(legacy_prefs, section):
                section_dict = getattr(legacy_prefs, section, {})
                if section_dict and key in section_dict:
                    return section_dict.get(key)

        # Nothing found
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

    # New preference structure
    prompt_preferences: PromptPreferences = Field(
        default_factory=PromptPreferences,
        description="Preferences specifically for LLM prompt generation and content control",
    )

    system_preferences: SystemPreferences = Field(
        default_factory=SystemPreferences,
        description="System-related preferences for UI, features, etc.",
    )

    # Legacy preferences (for backward compatibility)
    preferences: Preferences = Field(
        default_factory=Preferences,
        description="Legacy preference structure (will be migrated)",
    )

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

    @property
    def flat_prefs(self) -> FlatPreference:
        """
        Provide direct access to preferences using dot notation.

        Example usage:
            profile.flat_prefs.project_max_projects  # access project.max_projects
            profile.flat_prefs.career_summary_min_words  # access career_summary.min_words
        """
        return FlatPreference(self)

    # Replace save methods with a pre_save hook
    async def on_save(self) -> None:
        """Pre-save hook to update timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        """Beanie document settings."""

        name = "profiles"
        use_state_management = True
        bson_encoders = {
            datetime: lambda dt: (
                dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
            ),
        }
