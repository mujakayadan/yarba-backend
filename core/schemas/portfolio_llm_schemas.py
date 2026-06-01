"""Pydantic schemas for LLM interactions related to Portfolios."""

from pydantic import BaseModel, Field

# These schemas mirror core/models/portfolio.py but are simplified for LLM interaction,
# especially avoiding Field(default=...) where it causes issues with OpenAI's JSON mode.


class CareerSummaryLLMSchema(BaseModel):
    """LLM schema for Career Summary."""

    job_titles: list[str] = Field(default_factory=list)
    default_job_title: str
    years_of_experience: str
    default_summary: str

    class Config:
        extra = "forbid"


class WorkExperienceLLMSchema(BaseModel):
    """LLM schema for Work Experience."""

    job_title: str
    company: str
    location: str | None = None
    time: str | None = None
    responsibilities: list[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class EducationLLMSchema(BaseModel):
    """LLM schema for Education."""

    degree_type: str | None = None
    degree: str
    university_name: str
    time: str | None = None
    location: str | None = None
    GPA: str | None = None
    transcript: list[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class ProjectLLMSchema(BaseModel):
    """LLM schema for Projects."""

    name: str
    bullet_points: list[str] = Field(default_factory=list)
    date: str | None = None
    link: str | None = None

    class Config:
        extra = "forbid"


class AwardLLMSchema(BaseModel):
    """LLM schema for Awards."""

    name: str
    explanation: str | None = None

    class Config:
        extra = "forbid"


class PublicationLLMSchema(BaseModel):
    """LLM schema for Publications."""

    name: str
    publisher: str | None = None
    link: str | None = None

    class Config:
        extra = "forbid"


class CustomSectionItemLLMSchema(BaseModel):
    """LLM schema for a single item within a custom section."""

    title: str
    content: str | list[str] | str = Field(
        description="Content of the custom section. Can be a single string, a list of strings (bullet points), or a JSON string representing a list of objects or a complex object."
    )

    class Config:
        extra = "forbid"


class CustomSectionsLLMSchema(BaseModel):
    """LLM schema for Custom Sections container."""

    sections: list[CustomSectionItemLLMSchema] = Field(
        default_factory=list,
        description="List of custom sections, each a dictionary with a title and content.",
    )

    class Config:
        extra = "forbid"


class SkillLLMSchema(BaseModel):
    """LLM schema for Skills."""

    category: str
    skills: list[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class PortfolioLLMSchema(BaseModel):
    """Pydantic schema for the expected output from LLM for portfolio parsing/generation."""

    # Note: user_id, profile_id, created_at, updated_at are usually handled by the application/database,
    # so the LLM should not typically generate them directly. They are omitted here.

    career_summary: CareerSummaryLLMSchema | None = None
    skills: list[SkillLLMSchema] = Field(default_factory=list)
    work_experience: list[WorkExperienceLLMSchema] = Field(default_factory=list)
    education: list[EducationLLMSchema] = Field(default_factory=list)
    projects: list[ProjectLLMSchema] = Field(default_factory=list)
    awards: list[AwardLLMSchema] = Field(default_factory=list)
    publications: list[PublicationLLMSchema] = Field(default_factory=list)
    certifications: list[str] = Field(
        default_factory=list
    )  # Assuming certifications are a list of strings
    custom_sections: CustomSectionsLLMSchema | None = (
        None  # Or Dict[str, Any] if more free-form
    )
    # professional_title: Optional[str] = None # If this is distinct from career_summary.job_title

    class Config:
        extra = "forbid"
        # title = "Portfolio LLM Output Schema" # Optional title for the schema if generated
