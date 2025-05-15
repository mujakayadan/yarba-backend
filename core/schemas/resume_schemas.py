from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class PersonalInformationSchema(BaseModel):
    full_name: str = Field(..., description="Full name of the person")
    email: str = Field(..., description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Physical address")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL")
    github: Optional[str] = Field(None, description="GitHub profile URL")
    website: Optional[str] = Field(None, description="Personal website URL")

    class Config:
        extra = "forbid"


class CareerSummarySchema(BaseModel):
    job_title: str = Field(
        ..., description="Selected job title that best matches the target position"
    )
    # years_of_experience: Optional[str] = None # NOTE: Removed as per prompt instructions
    default_summary: str = Field(
        ..., description="Career summary text tailored to the job description"
    )

    class Config:
        extra = "forbid"


class SkillCategorySchema(BaseModel):
    category: str = Field(..., description="Skill category name")
    skills: List[str] = Field(..., description="List of skills in this category")

    class Config:
        extra = "forbid"


class WorkExperienceSchema(BaseModel):
    job_title: str = Field(..., description="Job title/position")
    company: str = Field(..., description="Company/organization name")
    location: str = Field(..., description="Location of the job")
    time: str = Field(..., description="Time period worked in this position")
    responsibilities: List[str] = Field(
        ..., description="Key responsibilities, achievements, or contributions"
    )

    class Config:
        extra = "forbid"


class EducationSchema(BaseModel):
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

    class Config:
        extra = "forbid"


class ProjectSchema(BaseModel):
    name: str = Field(..., description="Project name/title")
    bullet_points: List[str] = Field(
        ...,
        description="Key achievements, technologies used, or impact points from the project",
    )
    date: str = Field(..., description="Date or timeframe of the project")
    link: Optional[str] = Field(
        default=None, description="Optional link to the project (URL as string)"
    )

    class Config:
        extra = "forbid"


class PublicationSchema(BaseModel):
    name: str = Field(..., description="Publication title/name")
    publisher: str = Field(..., description="Publisher or journal name")
    link: Optional[str] = Field(None, description="Link to the publication")
    time: str = Field(..., description="Publication date or timeframe")

    class Config:
        extra = "forbid"


class AwardSchema(BaseModel):
    name: str = Field(..., description="Award title/name")
    explanation: str = Field(
        ...,
        description="Explanation of the award including issuing organization, date, and significance",
    )

    class Config:
        extra = "forbid"
        # Keep example if desired, or remove if not needed here
        json_schema_extra = {
            "example": {
                "name": "68th Iowa Reserve Chess Championship Winner",
                "explanation": "Issued by Iowa State Chess Association, Aug 2023. 4 Rounds G/60 d5, won with a perfect score of 4/4",
            }
        }


class ResumeOutputSchema(BaseModel):
    """Defines the overall structure for the generated resume JSON output."""

    personal_information: PersonalInformationSchema = Field(
        ..., description="Candidate's personal contact information"
    )
    career_summary: CareerSummarySchema = Field(
        ..., description="Tailored career summary for the target job"
    )
    skills: List[SkillCategorySchema] = Field(
        ..., description="List of relevant skill categories and skills"
    )
    work_experience: List[WorkExperienceSchema] = Field(
        ..., description="List of relevant work experiences"
    )
    education: List[EducationSchema] = Field(
        ..., description="List of educational background"
    )
    projects: List[ProjectSchema] = Field(..., description="List of relevant projects")
    publications: List[PublicationSchema] = Field(
        ..., description="List of relevant publications"
    )
    awards: List[AwardSchema] = Field(
        ..., description="List of relevant awards and honors"
    )

    class Config:
        extra = "forbid"
