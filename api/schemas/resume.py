"""Resume schema models for API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class ResumeBase(BaseModel):
    """Base class for resume schemas."""

    job_description: str = Field(
        ..., description="Job description to tailor the resume for"
    )


class ResumeCreate(BaseModel):
    """
    Schema for resume creation.

    Only job description is required - all other information will be extracted from the
    job description or taken from the user's profile preferences automatically.
    """

    job_description: str = Field(
        ..., description="Job description to tailor the resume for"
    )
    generate_pdf: bool = Field(
        False, description="Whether to generate PDF immediately after resume creation"
    )


class ResumeUpdate(BaseModel):
    """Schema for resume update."""

    job_title: Optional[str] = Field(None, description="Job title")
    company_name: Optional[str] = Field(None, description="Company name")
    job_description: Optional[str] = Field(None, description="Job description")
    template_id: Optional[str] = Field(None, description="Template ID")
    content: Optional[Dict[str, Any]] = Field(None, description="Resume content")


class SortOptions(str):
    """Enum-like class for sorting options."""

    UPDATED_DESC = "updated_desc"
    UPDATED_ASC = "updated_asc"
    CREATED_DESC = "created_desc"
    CREATED_ASC = "created_asc"
    TITLE_ASC = "title_asc"
    TITLE_DESC = "title_desc"


class ResumeFilter(BaseModel):
    """Schema for API resume filtering and pagination.

    This class is used for API request validation and represents
    filtering parameters that users can specify in their requests.
    It is different from the repository-level ResumeFilter.
    """

    title: Optional[str] = Field(None, description="Filter by title")
    template_id: Optional[str] = Field(None, description="Filter by template ID")
    is_cover_letter: Optional[bool] = Field(None, description="Filter by document type")
    sort_by: Optional[str] = Field(
        SortOptions.UPDATED_DESC,
        description="Sort field and direction (updated_desc, updated_asc, created_desc, created_asc, title_asc, title_desc)",
    )
    skip: int = Field(0, ge=0, description="Number of resumes to skip")
    limit: int = Field(10, ge=1, le=100, description="Number of resumes to return")


class ResumeResponse(BaseModel):
    """Response schema for resume."""

    id: PydanticObjectId = Field(..., description="Resume ID")
    user_id: PydanticObjectId = Field(..., description="User ID")
    profile_id: PydanticObjectId = Field(..., description="Profile ID")
    portfolio_id: PydanticObjectId = Field(..., description="Portfolio ID")
    title: str = Field(..., description="Resume title")
    template_id: Optional[str] = Field(None, description="Template ID")
    job_title: Optional[str] = Field(None, description="Job title")
    company_name: Optional[str] = Field(None, description="Company name")
    job_description: Optional[str] = Field(None, description="Job description")
    content: Optional[Dict[str, Any]] = Field(None, description="Resume content")
    has_pdf: bool = Field(False, description="Whether the resume has a PDF")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True
        json_encoders = {PydanticObjectId: str}

    def model_dump(self, **kwargs):
        """Custom dump method to add has_pdf field and remove internal fields."""
        # Get the standard model dump
        data = super().model_dump(**kwargs)

        # With Pydantic v2, we need a different approach to access the original data
        original_obj = getattr(self, "__dict__", {}).get(
            "__pydantic_fields_set__", None
        )

        # Try different methods to get resume_pdf_key
        if hasattr(self, "resume_pdf_key"):
            # Direct attribute access if available
            data["has_pdf"] = bool(self.resume_pdf_key)
        elif hasattr(self, "__pydantic_private__"):
            # Traditional private data approach
            original_data = self.__pydantic_private__.get("data", {})
            data["has_pdf"] = bool(original_data.get("resume_pdf_key"))
        elif hasattr(self, "__dict__") and "_obj" in self.__dict__:
            # Access via the underlying object if using from_attributes
            data["has_pdf"] = bool(
                getattr(self.__dict__["_obj"], "resume_pdf_key", None)
            )

        # Remove any sensitive or internal fields
        for field in ["resume_pdf_key"]:
            if field in data:
                del data[field]

        return data


class PaginatedResumeResponse(BaseModel):
    """Paginated response for resumes."""

    items: List[ResumeResponse] = Field(
        ..., description="List of resumes for the current page"
    )
    total: int = Field(
        ..., description="Total number of resumes matching the filter criteria"
    )
