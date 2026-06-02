from datetime import datetime
from typing import Any

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LLMUsageResponse(BaseModel):
    """Response model for LLM usage."""

    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    usage_by_model: dict[str, dict[str, float]] = Field(default_factory=dict)
    usage_by_operation: dict[str, dict[str, float]] = Field(default_factory=dict)
    monthly_quota: int | None = None
    monthly_cost_limit: float | None = None
    current_month_tokens: int = 0
    current_month_cost: float = 0.0
    last_used: datetime | None = None
    monthly_history: dict[str, dict[str, float]] = Field(default_factory=dict)


class LLMUsageSummary(BaseModel):
    """Simplified response model for LLM usage summary statistics."""

    total_tokens: int
    total_cost: float
    current_month_tokens: int
    current_month_cost: float
    monthly_quota: int | None
    monthly_cost_limit: float | None
    usage_limit_percentage: float
    cost_limit_percentage: float
    model_count: int
    operation_count: int


class PersonalInfoCreate(BaseModel):
    """Schema for creating personal information."""

    full_name: str
    email: EmailStr
    phone: str | None = None
    address: str | None = None
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None


class PersonalInfoUpdate(BaseModel):
    """Schema for updating personal information. All fields optional."""

    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None


class PromptPreferencesUpdate(BaseModel):
    """Schema for updating prompt preferences. All fields are optional."""

    project: dict[str, Any] | None = None
    work_experience: dict[str, Any] | None = None
    skills: dict[str, Any] | None = None
    career_summary: dict[str, Any] | None = None
    education: dict[str, Any] | None = None
    cover_letter: dict[str, Any] | None = None
    awards: dict[str, Any] | None = None
    publications: dict[str, Any] | None = None


class SystemPreferencesUpdate(BaseModel):
    """Schema for updating system preferences. All fields are optional."""

    features: dict[str, bool] | None = None
    notifications: dict[str, Any] | None = None
    privacy: dict[str, Any] | None = None
    llm: dict[str, Any] | None = None
    templates: dict[str, str] | None = None


class ProfileCreate(BaseModel):
    """Schema for creating a profile. Requires only personal info."""

    personal_information: PersonalInfoCreate
    preferences: dict | None = None


class ProfileUpdate(BaseModel):
    """Schema for updating a profile (currently only supports personal info update via this specific schema)."""

    personal_information: PersonalInfoUpdate | None = None


class ProfilePatch(BaseModel):
    """Schema for patching specific top-level profile fields."""

    life_story: str | None = None
    api_keys: dict | None = None


class LifeStoryPatch(BaseModel):
    """Schema for patching just the life story field."""

    life_story: str = Field(..., description="User's life story content")


class ProfileResponse(BaseModel):
    """Response schema for a Profile."""

    id: PydanticObjectId
    user_id: PydanticObjectId
    personal_information: PersonalInfoCreate
    signature_key: str | None = None
    life_story: str | None = None
    profile_picture_key: str | None = None
    prompt_preferences: dict | None
    system_preferences: dict | None
    llm_usage: LLMUsageResponse | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SignatureResponse(BaseModel):
    """Response model for signature storage key and URL."""

    signature_key: str | None = None
    signature_url: str | None = None
