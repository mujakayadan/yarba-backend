"""Pydantic schemas for resume data structures."""

from pydantic import BaseModel, Field


class PersonalInformationSchema(BaseModel):
    """Schema for personal information section of a resume."""

    full_name: str = Field(..., description="Full name of the person")
    email: str = Field(..., description="Email address")
    phone: str | None = Field(None, description="Phone number")
    address: str | None = Field(None, description="Physical address")
    linkedin: str | None = Field(None, description="LinkedIn profile URL")
    github: str | None = Field(None, description="GitHub profile URL")
    website: str | None = Field(None, description="Personal website URL")

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"


class CareerSummarySchema(BaseModel):
    """Schema for career summary section of a resume."""

    job_title: str = Field(
        ..., description="Selected job title that best matches the target position"
    )
    # years_of_experience: Optional[str] = None # NOTE: Removed as per prompt instructions
    default_summary: str = Field(
        ..., description="Career summary text tailored to the job description"
    )

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"


class SkillCategorySchema(BaseModel):
    """Schema for a category of skills."""

    category: str = Field(..., description="Skill category name")
    skills: list[str] = Field(..., description="List of skills in this category")

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"


class WorkExperienceSchema(BaseModel):
    """Schema for work experience section of a resume."""

    job_title: str = Field(..., description="Job title/position")
    company: str = Field(..., description="Company/organization name")
    location: str = Field(..., description="Location of the job")
    time: str = Field(..., description="Time period worked in this position")
    responsibilities: list[str] = Field(
        ..., description="Key responsibilities, achievements, or contributions"
    )

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"


class EducationSchema(BaseModel):
    """Schema for education section of a resume."""

    degree_type: str = Field(
        ..., description="Type of degree (e.g., Bachelor's, Master's)"
    )
    degree: str = Field(..., description="Specific degree name/field of study")
    university_name: str = Field(..., description="Educational institution name")
    time: str = Field(..., description="Time period or graduation date")
    location: str = Field(..., description="Location of the institution")
    GPA: str | None = Field(None, description="GPA if relevant")
    transcript: list[str] | None = Field(
        None, description="Relevant coursework or academic achievements"
    )

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"


class ProjectSchema(BaseModel):
    """Schema for project section of a resume."""

    name: str = Field(..., description="Project name/title")
    bullet_points: list[str] = Field(
        ...,
        description=(
            "Key achievements, technologies used, or impact points from the project"
        ),
    )
    date: str = Field(..., description="Date or timeframe of the project")
    link: str | None = Field(
        default=None, description="Optional link to the project (URL as string)"
    )

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"


class PublicationSchema(BaseModel):
    """Schema for publication section of a resume."""

    name: str = Field(..., description="Publication title/name")
    publisher: str = Field(..., description="Publisher or journal name")
    link: str | None = Field(None, description="Link to the publication")
    time: str = Field(..., description="Publication date or timeframe")

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"


class AwardSchema(BaseModel):
    """Schema for award section of a resume."""

    name: str = Field(..., description="Award title/name")
    explanation: str = Field(
        ...,
        description=(
            "Explanation of the award including issuing organization, date, "
            "and significance"
        ),
    )

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"
        # Keep example if desired, or remove if not needed here
        json_schema_extra = {
            "example": {
                "name": "68th Iowa Reserve Chess Championship Winner",
                "explanation": (
                    "Issued by Iowa State Chess Association, Aug 2023. "
                    "4 Rounds G/60 d5, won with a perfect score of 4/4"
                ),
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
    skills: list[SkillCategorySchema] = Field(
        ..., description="List of relevant skill categories and skills"
    )
    work_experience: list[WorkExperienceSchema] = Field(
        ..., description="List of relevant work experiences"
    )
    education: list[EducationSchema] = Field(
        ..., description="List of educational background"
    )
    projects: list[ProjectSchema] = Field(..., description="List of relevant projects")
    publications: list[PublicationSchema] = Field(
        ..., description="List of relevant publications"
    )
    awards: list[AwardSchema] = Field(
        ..., description="List of relevant awards and honors"
    )

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"
