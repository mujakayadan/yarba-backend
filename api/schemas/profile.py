from datetime import datetime
from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, EmailStr, Field


class LLMUsageResponse(BaseModel):
    """Response model for LLM usage."""

    total_tokens: int
    total_cost: float
    usage_by_model: Dict[str, Dict[str, float]]
    usage_by_operation: Dict[str, Dict[str, float]]
    monthly_quota: Optional[int]
    monthly_cost_limit: Optional[float]
    current_month_tokens: int
    current_month_cost: float
    last_used: Optional[datetime] = None
    monthly_history: Optional[Dict[str, Dict[str, float]]] = None


class LLMUsageSummary(BaseModel):
    """Simplified response model for LLM usage summary statistics."""

    total_tokens: int
    total_cost: float
    current_month_tokens: int
    current_month_cost: float
    monthly_quota: Optional[int]
    monthly_cost_limit: Optional[float]
    usage_limit_percentage: float
    cost_limit_percentage: float
    model_count: int
    operation_count: int


class PersonalInfoCreate(BaseModel):
    """Schema for creating personal information."""

    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None


class PersonalInfoUpdate(BaseModel):
    """Schema for updating personal information. All fields optional."""

    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None


class PromptPreferencesUpdate(BaseModel):
    """Schema for updating prompt preferences. All fields are optional."""

    project: Optional[Dict[str, Any]] = None
    work_experience: Optional[Dict[str, Any]] = None
    skills: Optional[Dict[str, Any]] = None
    career_summary: Optional[Dict[str, Any]] = None
    education: Optional[Dict[str, Any]] = None
    cover_letter: Optional[Dict[str, Any]] = None
    awards: Optional[Dict[str, Any]] = None
    publications: Optional[Dict[str, Any]] = None


class SystemPreferencesUpdate(BaseModel):
    """Schema for updating system preferences. All fields are optional."""

    features: Optional[Dict[str, bool]] = None
    notifications: Optional[Dict[str, Any]] = None
    privacy: Optional[Dict[str, Any]] = None
    llm: Optional[Dict[str, Any]] = None
    templates: Optional[Dict[str, str]] = None


class ProfileCreate(BaseModel):
    """Schema for creating a profile. Requires only personal info."""

    personal_information: PersonalInfoCreate


class ProfileUpdate(BaseModel):
    """Schema for updating a profile (currently only supports personal info update via this specific schema)."""

    personal_information: Optional[PersonalInfoUpdate] = None


class ProfilePatch(BaseModel):
    """Schema for patching specific top-level profile fields."""

    life_story: Optional[str] = None
    api_keys: Optional[dict] = None


class LifeStoryPatch(BaseModel):
    """Schema for patching just the life story field."""

    life_story: str = Field(..., description="User's life story content")


class ProfileResponse(BaseModel):
    """Response schema for a Profile."""

    id: PydanticObjectId
    user_id: PydanticObjectId
    personal_information: PersonalInfoCreate
    signature_key: Optional[str] = None
    life_story: Optional[str] = None
    profile_picture_key: Optional[str] = None
    prompt_preferences: Optional[Dict]
    system_preferences: Optional[Dict]
    llm_usage: Optional[LLMUsageResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {PydanticObjectId: str}


class ProfilePictureUpdateResponse(BaseModel):
    """Response model for profile picture update."""

    profile_picture_key: Optional[str] = None


class SignatureResponse(BaseModel):
    """Response model for signature storage key and URL."""

    signature_key: Optional[str] = None
    signature_url: Optional[str] = None
