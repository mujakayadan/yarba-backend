"""Resume schema models for API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ResumeBase(BaseModel):
    """Base class for resume schemas."""

    title: str = Field(..., description="Resume title")
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

    title: Optional[str] = Field(None, description="Resume title")
    template_id: Optional[str] = Field(None, description="Template ID")
    job_title: Optional[str] = Field(None, description="Job title")
    company_name: Optional[str] = Field(None, description="Company name")
    job_description: Optional[str] = Field(None, description="Job description")
    content: Optional[Dict[str, Any]] = Field(None, description="Resume content")


class ResumeFilter(BaseModel):
    """Schema for resume filtering."""

    title: Optional[str] = Field(None, description="Filter by title")
    template_id: Optional[str] = Field(None, description="Filter by template ID")
    is_cover_letter: Optional[bool] = Field(None, description="Filter by document type")
    skip: int = Field(0, ge=0, description="Number of resumes to skip")
    limit: int = Field(10, ge=1, le=100, description="Number of resumes to return")


class ResumeResponse(ResumeBase):
    """Response schema for resume."""

    id: str = Field(..., description="Resume ID")
    user_id: str = Field(..., description="User ID")
    profile_id: str = Field(..., description="Profile ID")
    portfolio_id: str = Field(..., description="Portfolio ID")
    job_title: Optional[str] = Field(None, description="Job title")
    company_name: Optional[str] = Field(None, description="Company name")
    job_description: Optional[str] = Field(None, description="Job description")
    content: Optional[Dict[str, Any]] = Field(None, description="Resume content")
    is_cover_letter: bool = Field(False, description="Whether this is a cover letter")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True


# Cover letter schemas
class CoverLetterCreate(ResumeBase):
    """Schema for cover letter creation."""

    job_description: Optional[str] = Field(
        None, description="Job description to tailor the cover letter for"
    )
    llm_preferences: Optional[Dict[str, Any]] = Field(
        None, description="LLM settings for generation"
    )


class CoverLetterResponse(ResumeResponse):
    """Response schema for cover letter."""

    is_cover_letter: bool = Field(True, description="Whether this is a cover letter")
