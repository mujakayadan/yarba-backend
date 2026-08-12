"""Schemas for public portfolio content API."""

from pydantic import BaseModel, ConfigDict, Field


class PublicPersonalInfo(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None
    profile_picture_url: str | None = None


class PublicCareerSummary(BaseModel):
    job_titles: list[str] = Field(default_factory=list)
    default_job_title: str = ""
    default_summary: str = ""
    years_of_experience: str = ""


class PublicWorkExperience(BaseModel):
    job_title: str = ""
    company: str = ""
    location: str = ""
    time: str = ""
    start_date: str | None = None
    end_date: str | None = None
    current: bool = False
    responsibilities: list[str] = Field(default_factory=list)


class PublicEducation(BaseModel):
    degree_type: str = ""
    degree: str = ""
    university_name: str = ""
    time: str = ""
    location: str = ""
    gpa: str = ""
    transcript: list[str] = Field(default_factory=list)


class PublicSkillCategory(BaseModel):
    category: str = ""
    skills: list[str] = Field(default_factory=list)


class PublicProject(BaseModel):
    name: str = ""
    bullet_points: list[str] = Field(default_factory=list)
    date: str = ""
    link: str | None = None


class PublicAward(BaseModel):
    name: str = ""
    explanation: str = ""


class PublicPublication(BaseModel):
    name: str = ""
    publisher: str = ""
    link: str = ""
    time: str = ""


class PublicPortfolioContent(BaseModel):
    """Sanitized portfolio payload for public site consumption."""

    model_config = ConfigDict(from_attributes=True)

    personal: PublicPersonalInfo
    career_summary: PublicCareerSummary
    life_story: str | None = None
    work_experience: list[PublicWorkExperience] = Field(default_factory=list)
    education: list[PublicEducation] = Field(default_factory=list)
    skills: list[PublicSkillCategory] = Field(default_factory=list)
    projects: list[PublicProject] = Field(default_factory=list)
    awards: list[PublicAward] = Field(default_factory=list)
    publications: list[PublicPublication] = Field(default_factory=list)
