"""JSON schema models for structured LLM outputs.

This module contains Pydantic models used for structured JSON output
from LLM models that support JSON schema response formats.

These schemas are designed to align with the portfolio models structure
for easier mapping between LLM outputs and database models.
"""

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class PersonalInformationSchema(BaseModel):
    """Schema for personal information in structured JSON output."""

    full_name: str = Field(..., description="Full name of the person")
    email: EmailStr = Field(..., description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Physical address")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL")
    github: Optional[str] = Field(None, description="GitHub profile URL")
    website: Optional[str] = Field(None, description="Personal website URL")


class AwardSchema(BaseModel):
    """Schema for award entries in structured JSON output."""

    name: str = Field(..., description="Award title/name")
    explanation: str = Field(
        ...,
        description="Explanation of the award including issuing organization, date, and significance",
    )

    class Config:
        """Pydantic config."""

        schema_extra = {
            "example": {
                "name": "68th Iowa Reserve Chess Championship Winner",
                "explanation": "Issued by Iowa State Chess Association, Aug 2023. 4 Rounds G/60 d5, won with a perfect score of 4/4",
            }
        }


class AwardsListSchema(BaseModel):
    """Schema for a list of awards in structured JSON output."""

    awards: List[AwardSchema] = Field(..., description="List of awards or recognitions")


class ProjectSchema(BaseModel):
    """Schema for project entries in structured JSON output."""

    name: str = Field(..., description="Project name/title")
    bullet_points: List[str] = Field(
        ...,
        description="Key achievements, technologies used, or impact points from the project",
    )
    date: str = Field(..., description="Date or timeframe of the project")


class ProjectsListSchema(BaseModel):
    """Schema for a list of projects in structured JSON output."""

    projects: List[ProjectSchema] = Field(..., description="List of relevant projects")


class SkillSchema(BaseModel):
    """Schema for skill entries grouped by category."""

    category: str = Field(..., description="Skill category name")
    skills: List[str] = Field(..., description="List of skills in this category")


class SkillsListSchema(BaseModel):
    """Schema for a list of skill categories in structured JSON output."""

    skills: List[SkillSchema] = Field(
        ..., description="List of skill categories with their skills"
    )


class WorkExperienceSchema(BaseModel):
    """Schema for work experience entries in structured JSON output."""

    job_title: str = Field(..., description="Job title/position")
    company: str = Field(..., description="Company/organization name")
    location: str = Field(..., description="Location of the job")
    time: str = Field(..., description="Time period worked in this position")
    responsibilities: List[str] = Field(
        ..., description="Key responsibilities, achievements, or contributions"
    )


class WorkExperienceListSchema(BaseModel):
    """Schema for a list of work experiences in structured JSON output."""

    work_experience: List[WorkExperienceSchema] = Field(
        ..., description="List of relevant work experiences"
    )


class EducationSchema(BaseModel):
    """Schema for education entries in structured JSON output."""

    degree_type: str = Field(
        ..., description="Type of degree (e.g., Bachelor's, Master's)"
    )
    degree: str = Field(..., description="Specific degree name/field of study")
    university_name: str = Field(..., description="Educational institution name")
    time: str = Field(..., description="Time period or graduation date")
    location: str = Field(..., description="Location of the institution")
    GPA: Optional[str] = Field(None, description="GPA if relevant")
    transcript: Optional[List[str]] = Field(
        None, description="Relevant coursework or academic achievements"
    )


class EducationListSchema(BaseModel):
    """Schema for a list of education entries in structured JSON output."""

    education: List[EducationSchema] = Field(
        ..., description="List of educational backgrounds"
    )


class PublicationSchema(BaseModel):
    """Schema for publication entries in structured JSON output."""

    name: str = Field(..., description="Publication title/name")
    publisher: str = Field(..., description="Publisher or journal name")
    link: Optional[str] = Field(None, description="Link to the publication")
    time: str = Field(..., description="Publication date or timeframe")


class PublicationsListSchema(BaseModel):
    """Schema for a list of publication entries in structured JSON output."""

    publications: List[PublicationSchema] = Field(
        ..., description="List of relevant publications"
    )


class CareerSummarySchema(BaseModel):
    """Schema for career summary in structured JSON output."""

    job_titles: List[str] = Field(
        ...,
        description="List of job titles the user has held, most relevant ones for the target position",
    )
    years_of_experience: str = Field(
        ..., description="Years of experience in the field"
    )
    default_summary: str = Field(
        ..., description="Career summary text tailored to the job description"
    )
