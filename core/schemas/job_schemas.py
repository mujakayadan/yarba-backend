"""Schemas related to Job information extraction."""

from pydantic import BaseModel, Field


class JobInfoSchema(BaseModel):
    """Schema for the expected output when extracting job info from description."""

    company_name: str = Field(
        ...,
        description="Extracted company name, lowercase with underscores. Fallback: 'unknown_company'",
    )
    job_title: str = Field(
        ...,
        description="Extracted job title, lowercase with underscores. Fallback: 'unknown_position'",
    )
