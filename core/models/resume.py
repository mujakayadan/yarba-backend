"""Resume model for MongoDB using Beanie ODM."""

from datetime import UTC, datetime
from typing import Any

from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field

from core.models.document_config import (
    BSON_DATETIME_ENCODERS,
    DOCUMENT_MODEL_CONFIG,
    NESTED_MODEL_CONFIG,
)

from .portfolio import Portfolio
from .profile import Profile
from .user import User


class ResumeSection(BaseModel):
    """Base class for resume sections."""

    title: str
    content: str
    order: int = 0
    is_visible: bool = True

    model_config = NESTED_MODEL_CONFIG


class LLMSettings(BaseModel):
    """LLM settings for resume generation."""

    model_name: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None

    model_config = NESTED_MODEL_CONFIG


class LLMUsageStats(BaseModel):
    """LLM usage statistics for a specific resume."""

    total_tokens: int = Field(
        default=0, description="Total number of tokens used for this resume"
    )
    total_input_tokens: int = Field(
        default=0, description="Total number of input tokens"
    )
    total_output_tokens: int = Field(
        default=0, description="Total number of output tokens"
    )
    total_cost: float = Field(
        default=0.0, description="Total cost in USD for this resume"
    )

    # Breakdown by operation
    usage_by_operation: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Usage breakdown by operation type: {operation: {tokens: count, cost: amount}}",
    )

    # Breakdown by model
    usage_by_model: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Usage breakdown by model: {model_name: {tokens: count, cost: amount}}",
    )

    last_used: datetime | None = Field(
        default=None, description="Last time LLM was used for this resume"
    )

    model_config = NESTED_MODEL_CONFIG


class ResumeSelectionProjection(BaseModel):
    """Projection model for fetching minimal resume data for selection lists."""

    id: PydanticObjectId = Field(..., alias="_id")
    # company_name: Optional[str] = None # No longer needed for display name if using title
    # job_title: Optional[str] = None # No longer needed for display name if using title
    title: str | None = "My Resume"  # Added for display name and sorting
    created_at: datetime | None = None  # Added for sorting
    updated_at: datetime | None = None  # Added for sorting

    class Settings:
        projection = {
            # "company_name": 1, # No longer needed
            # "job_title": 1, # No longer needed
            "title": 1,
            "created_at": 1,
            "updated_at": 1,
        }


class Resume(Document):
    """Resume model for MongoDB using Beanie ODM."""

    user_id: PydanticObjectId
    user: Link[User] | None = None
    profile_id: PydanticObjectId
    profile: Link[Profile] | None = None
    portfolio_id: PydanticObjectId
    portfolio: Link[Portfolio] | None = None

    title: str | None = "My Resume"
    version: int = 1
    template_id: str | None = None

    # Job targeting information
    company_name: str | None = None
    job_title: str | None = None
    job_description: str = Field(default="")
    job_description_url: str | None = None

    # Content can be either structured data or LaTeX string
    content: dict[str, Any] = Field(default_factory=dict)

    # Custom sections
    custom_sections: list[ResumeSection] = Field(default_factory=list)

    # Generated PDFs
    resume_pdf_key: str | None = Field(
        default=None, description="S3 key for the resume PDF"
    )

    # Cover letters associated with this resume
    cover_letter_ids: list[PydanticObjectId] = Field(
        default_factory=list, description="IDs of cover letters based on this resume"
    )

    # AI generation parameters
    llm_settings: LLMSettings = Field(default_factory=LLMSettings)

    # LLM usage statistics for this specific resume
    llm_usage: LLMUsageStats = Field(
        default_factory=LLMUsageStats,
        description="LLM usage statistics for this resume",
    )

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = DOCUMENT_MODEL_CONFIG

    class Settings:
        """Beanie document settings."""

        name = "resumes"
        use_state_management = True
        indexes = ["user_id", "profile_id", "portfolio_id"]
        bson_encoders = BSON_DATETIME_ENCODERS
