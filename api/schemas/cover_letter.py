"""API schemas for cover letter endpoints."""

from datetime import datetime
from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class CoverLetterBase(BaseModel):
    """Base schema for cover letter data."""

    title: Optional[str] = None
    profile_id: Optional[PydanticObjectId] = None
    portfolio_id: Optional[PydanticObjectId] = None
    resume_id: Optional[PydanticObjectId] = None
    template_id: Optional[str] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    job_description: Optional[str] = None


class CoverLetterCreate(CoverLetterBase):
    """
    Schema for creating a new cover letter.

    By default, preferences such as template and LLM settings will be taken
    from the user's profile. These can be optionally overridden by providing
    the specific fields.
    """

    title: str = Field(..., description="Cover letter title")
    profile_id: PydanticObjectId = Field(..., description="Profile ID")
    template_id: str = Field(
        default="default",
        description="Template ID (will use profile default if not provided)",
    )
    resume_id: Optional[PydanticObjectId] = Field(
        None, description="Resume ID that this cover letter is based on"
    )
    llm_preferences: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional LLM settings for generation (will use profile preferences if not provided)",
    )


class CoverLetterUpdate(CoverLetterBase):
    """Schema for updating a cover letter."""

    content: Optional[Dict[str, Any]] = None
    cover_letter_content: Optional[str] = None


class CoverLetterResponse(CoverLetterBase):
    """Schema for cover letter response."""

    id: PydanticObjectId = Field(..., description="Cover letter ID")
    user_id: PydanticObjectId = Field(..., description="User ID")
    content: Dict[str, Any] = Field(default_factory=dict, description="Content data")
    cover_letter_content: Optional[str] = Field(
        None, description="Generated cover letter content"
    )
    has_pdf: bool = Field(default=False, description="Whether PDF is available")

    class Config:
        """Pydantic config."""

        from_attributes = True

    def __init__(self, **data):
        """Initialize the model with computed fields."""
        # Add has_pdf field based on cover_letter_pdf presence
        if "cover_letter_pdf" in data:
            data["has_pdf"] = bool(data["cover_letter_pdf"])
            # Remove the actual PDF bytes to reduce response size
            del data["cover_letter_pdf"]
        super().__init__(**data)
