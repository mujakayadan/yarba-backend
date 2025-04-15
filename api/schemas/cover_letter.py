"""API schemas for cover letter endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

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
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True
        json_encoders = {PydanticObjectId: str}

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)

        # Add has_pdf field based on PDF key existence
        data["has_pdf"] = bool(data.get("cover_letter_pdf_key"))

        # Remove sensitive or internal fields
        for field in ["cover_letter_pdf_key"]:
            if field in data:
                del data[field]

        return data


class SortOptions:
    """Sort options for cover letter filtering."""

    UPDATED_DESC = "updated_desc"
    UPDATED_ASC = "updated_asc"
    CREATED_DESC = "created_desc"
    CREATED_ASC = "created_asc"
    TEMPLATE_ASC = "template_asc"
    TEMPLATE_DESC = "template_desc"


class CoverLetterFilter(BaseModel):
    """Schema for API cover letter filtering and pagination.

    This class is used for API request validation and represents
    filtering parameters that users can specify in their requests.
    It is different from the repository-level CoverLetterFilter.
    """

    template_id: Optional[str] = Field(None, description="Filter by template ID")
    resume_id: Optional[PydanticObjectId] = Field(
        None, description="Filter by resume ID"
    )
    sort_by: Optional[str] = Field(
        SortOptions.UPDATED_DESC,
        description="Sort field and direction (updated_desc, updated_asc, created_desc, created_asc, template_asc, template_desc)",
    )
    skip: int = Field(0, ge=0, description="Number of cover letters to skip")
    limit: int = Field(
        10, ge=1, le=100, description="Number of cover letters to return"
    )


class PaginatedCoverLetterResponse(BaseModel):
    """Paginated response for cover letters."""

    items: List[CoverLetterResponse] = Field(
        ..., description="List of cover letters for the current page"
    )
    total: int = Field(
        ..., description="Total number of cover letters matching the filter criteria"
    )
