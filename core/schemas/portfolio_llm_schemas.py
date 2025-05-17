"""Pydantic schemas for LLM interactions related to Portfolios."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl

# These schemas mirror core/models/portfolio.py but are simplified for LLM interaction,
# especially avoiding Field(default=...) where it causes issues with OpenAI's JSON mode.


class CareerSummaryLLMSchema(BaseModel):
    """LLM schema for Career Summary."""

    job_titles: List[str] = Field(default_factory=list)
    default_job_title: str
    years_of_experience: str
    default_summary: str

    class Config:
        extra = "forbid"


class WorkExperienceLLMSchema(BaseModel):
    """LLM schema for Work Experience."""

    job_title: str
    company: str
    location: Optional[str] = None
    time: Optional[str] = None
    responsibilities: List[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class EducationLLMSchema(BaseModel):
    """LLM schema for Education."""

    degree_type: Optional[str] = None
    degree: str
    university_name: str
    time: Optional[str] = None
    location: Optional[str] = None
    GPA: Optional[str] = None
    transcript: List[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class ProjectLLMSchema(BaseModel):
    """LLM schema for Projects."""

    name: str
    bullet_points: List[str] = Field(default_factory=list)
    date: Optional[str] = None
    link: Optional[str] = None

    class Config:
        extra = "forbid"


class AwardLLMSchema(BaseModel):
    """LLM schema for Awards."""

    name: str
    explanation: Optional[str] = None

    class Config:
        extra = "forbid"


class PublicationLLMSchema(BaseModel):
    """LLM schema for Publications."""

    name: str
    publisher: Optional[str] = None
    link: Optional[str] = None

    class Config:
        extra = "forbid"


class CustomSectionItemLLMSchema(BaseModel):
    """LLM schema for a single item within a custom section."""

    title: str
    content: Union[str, List[str], str] = Field(
        description="Content of the custom section. Can be a single string, a list of strings (bullet points), or a JSON string representing a list of objects or a complex object."
    )

    class Config:
        extra = "forbid"


class CustomSectionsLLMSchema(BaseModel):
    """LLM schema for Custom Sections container."""

    sections: List[CustomSectionItemLLMSchema] = Field(
        default_factory=list,
        description="List of custom sections, each a dictionary with a title and content.",
    )

    class Config:
        extra = "forbid"


class SkillLLMSchema(BaseModel):
    """LLM schema for Skills."""

    category: str
    skills: List[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class PortfolioLLMSchema(BaseModel):
    """Pydantic schema for the expected output from LLM for portfolio parsing/generation."""

    # Note: user_id, profile_id, created_at, updated_at are usually handled by the application/database,
    # so the LLM should not typically generate them directly. They are omitted here.

    career_summary: Optional[CareerSummaryLLMSchema] = None
    skills: List[SkillLLMSchema] = Field(default_factory=list)
    work_experience: List[WorkExperienceLLMSchema] = Field(default_factory=list)
    education: List[EducationLLMSchema] = Field(default_factory=list)
    projects: List[ProjectLLMSchema] = Field(default_factory=list)
    awards: List[AwardLLMSchema] = Field(default_factory=list)
    publications: List[PublicationLLMSchema] = Field(default_factory=list)
    certifications: List[str] = Field(
        default_factory=list
    )  # Assuming certifications are a list of strings
    custom_sections: Optional[CustomSectionsLLMSchema] = (
        None  # Or Dict[str, Any] if more free-form
    )
    # professional_title: Optional[str] = None # If this is distinct from career_summary.job_title

    class Config:
        extra = "forbid"
        # title = "Portfolio LLM Output Schema" # Optional title for the schema if generated
