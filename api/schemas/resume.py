"""Resume schema models for API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class ResumeBase(BaseModel):
    """Base class for resume schemas."""

    template_id: str = Field(..., description="Template ID")


class ResumeCreate(ResumeBase):
    """Schema for resume creation."""

    job_description: Optional[str] = Field(
        None, description="Job description to tailor the resume for"
    )
    selected_sections: Optional[Dict[str, str]] = Field(
        None, description="Sections to include and their processing method"
    )
    llm_preferences: Optional[Dict[str, Any]] = Field(
        None, description="LLM settings for generation"
    )


class ResumeUpdate(BaseModel):
    """Schema for resume update."""

    template_id: Optional[str] = Field(None, description="Template ID")
    job_title: Optional[str] = Field(None, description="Job title")
    company_name: Optional[str] = Field(None, description="Company name")
    job_description: Optional[str] = Field(None, description="Job description")
    content: Optional[Dict[str, Any]] = Field(None, description="Resume content")


class ResumeFilter(BaseModel):
    """Schema for API resume filtering and pagination.

    This class is used for API request validation and represents
    filtering parameters that users can specify in their requests.
    It is different from the repository-level ResumeFilter.
    """

    title: Optional[str] = Field(None, description="Filter by title")
    template_id: Optional[str] = Field(None, description="Filter by template ID")
    is_cover_letter: Optional[bool] = Field(None, description="Filter by document type")
    version: Optional[int] = Field(None, description="Filter by version")
    skip: int = Field(0, ge=0, description="Number of resumes to skip")
    limit: int = Field(10, ge=1, le=100, description="Number of resumes to return")


class ResumeResponse(BaseModel):
    """Response schema for resume."""

    id: PydanticObjectId = Field(..., description="Resume ID")
    user_id: PydanticObjectId = Field(..., description="User ID")
    profile_id: PydanticObjectId = Field(..., description="Profile ID")
    portfolio_id: PydanticObjectId = Field(..., description="Portfolio ID")
    title: str = Field(..., description="Resume title")
    template_id: str = Field(..., description="Template ID")
    job_title: Optional[str] = Field(None, description="Job title")
    company_name: Optional[str] = Field(None, description="Company name")
    job_description: Optional[str] = Field(None, description="Job description")
    content: Optional[Dict[str, Any]] = Field(None, description="Resume content")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True
        json_encoders = {PydanticObjectId: str}


class PaginatedResumeResponse(BaseModel):
    """Paginated response for resumes."""

    items: List[ResumeResponse] = Field(
        ..., description="List of resumes for the current page"
    )
    total: int = Field(
        ..., description="Total number of resumes matching the filter criteria"
    )
