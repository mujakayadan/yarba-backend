"""API schemas for cover letter endpoints."""

from datetime import datetime
from typing import Any, Dict, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class CoverLetterBase(BaseModel):
    """Base schema for cover letter data."""

    profile_id: Optional[PydanticObjectId] = None
    portfolio_id: Optional[PydanticObjectId] = None
    resume_id: Optional[PydanticObjectId] = None
    template_id: Optional[str] = None


class CoverLetterCreate(BaseModel):
    """
    Schema for creating a new cover letter.

    Only resume_id is required - all other information including profile, portfolio,
    template, etc. will be retrieved from the active user profile automatically.
    """

    resume_id: PydanticObjectId = Field(
        ..., description="Resume ID that this cover letter is based on"
    )
    generate_pdf: bool = Field(
        False,
        description="Whether to generate PDF immediately after cover letter creation",
    )


class CoverLetterUpdate(CoverLetterBase):
    """Schema for updating a cover letter."""

    content: Optional[Dict[str, Any]] = None


class CoverLetterResponse(CoverLetterBase):
    """Schema for cover letter response."""

    id: PydanticObjectId = Field(..., description="Cover letter ID")
    user_id: PydanticObjectId = Field(..., description="User ID")
    content: Dict[str, Any] = Field(default_factory=dict, description="Content data")
    has_pdf: bool = Field(default=False, description="Whether PDF is available")

    class Config:
        """Pydantic config."""

        from_attributes = True

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)

        # Add has_pdf field based on PDF key existence
        data["has_pdf"] = bool(data.get("cover_letter_pdf_key"))

        # Remove sensitive or internal fields
        for field in ["cover_letter_pdf_key"]:
            if field in data:
                del data[field]

        return data
