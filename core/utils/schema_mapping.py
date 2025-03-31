"""Utility functions for mapping between JSON schema objects and database models."""

from typing import List, Optional, Type, TypeVar, Union

from pydantic import EmailStr

from core.models.portfolio import (
    Award,
    CareerSummary,
    Education,
    Portfolio,
    Project,
    Publication,
    Skill,
    WorkExperience,
)
from core.models.profile import PersonalInformation, Profile
from core.schemas import (
    AwardsListSchema,
    CareerSummarySchema,
    EducationListSchema,
    PersonalInformationSchema,
    ProjectsListSchema,
    PublicationsListSchema,
    SkillsListSchema,
    WorkExperienceListSchema,
)

T = TypeVar("T")


def create_default_personal_info() -> PersonalInformation:
    """Create a default PersonalInformation object with placeholder values.

    This is used when personal information is missing but required.

    Returns:
        PersonalInformation with default placeholder values
    """
    return PersonalInformation(
        full_name="Default User",
        email="user@example.com",
        phone=None,
        address=None,
        linkedin=None,
        github=None,
        website=None,
    )


def ensure_profile_has_personal_info(profile: Profile) -> Profile:
    """Ensure a profile has personal_information, adding default if missing.

    Args:
        profile: The profile to check and possibly update

    Returns:
        Updated profile with personal_information field
    """
    if (
        not hasattr(profile, "personal_information")
        or profile.personal_information is None
    ):
        profile.personal_information = create_default_personal_info()

    return profile


def map_personal_info(
    schema: Optional[PersonalInformationSchema],
) -> PersonalInformation:
    """Map PersonalInformationSchema to PersonalInformation model.

    Args:
        schema: The schema object to map

    Returns:
        PersonalInformation model (default if schema is None or wrong type)
    """
    if not isinstance(schema, PersonalInformationSchema):
        return create_default_personal_info()

    return PersonalInformation(
        full_name=schema.full_name,
        email=schema.email,
        phone=schema.phone,
        address=schema.address,
        linkedin=schema.linkedin,
        github=schema.github,
        website=schema.website,
    )


def map_awards(schema: Optional[AwardsListSchema]) -> List[Award]:
    """Map AwardsListSchema to list of Award models.

    Args:
        schema: The schema object to map

    Returns:
        List of Award models or empty list if schema is None or wrong type
    """
    if not isinstance(schema, AwardsListSchema) or not schema.awards:
        return []

    return [
        Award(name=award.name, explanation=award.explanation) for award in schema.awards
    ]


def map_projects(schema: Optional[ProjectsListSchema]) -> List[Project]:
    """Map ProjectsListSchema to list of Project models.

    Args:
        schema: The schema object to map

    Returns:
        List of Project models or empty list if schema is None or wrong type
    """
    if not isinstance(schema, ProjectsListSchema) or not schema.projects:
        return []

    return [
        Project(
            name=project.name, bullet_points=project.bullet_points, date=project.date
        )
        for project in schema.projects
    ]


def map_work_experience(
    schema: Optional[WorkExperienceListSchema],
) -> List[WorkExperience]:
    """Map WorkExperienceListSchema to list of WorkExperience models.

    Args:
        schema: The schema object to map

    Returns:
        List of WorkExperience models or empty list if schema is None or wrong type
    """
    if not isinstance(schema, WorkExperienceListSchema) or not schema.work_experience:
        return []

    return [
        WorkExperience(
            job_title=exp.job_title,
            company=exp.company,
            location=exp.location,
            time=exp.time,
            responsibilities=exp.responsibilities,
        )
        for exp in schema.work_experience
    ]


def map_education(schema: Optional[EducationListSchema]) -> List[Education]:
    """Map EducationListSchema to list of Education models.

    Args:
        schema: The schema object to map

    Returns:
        List of Education models or empty list if schema is None or wrong type
    """
    if not isinstance(schema, EducationListSchema) or not schema.education:
        return []

    return [
        Education(
            degree_type=edu.degree_type,
            degree=edu.degree,
            university_name=edu.university_name,
            time=edu.time,
            location=edu.location,
            GPA=edu.GPA or "",
            transcript=edu.transcript or [],
        )
        for edu in schema.education
    ]


def map_publications(schema: Optional[PublicationsListSchema]) -> List[Publication]:
    """Map PublicationsListSchema to list of Publication models.

    Args:
        schema: The schema object to map

    Returns:
        List of Publication models or empty list if schema is None or wrong type
    """
    if not isinstance(schema, PublicationsListSchema) or not schema.publications:
        return []

    return [
        Publication(
            name=pub.name, publisher=pub.publisher, link=pub.link or "", time=pub.time
        )
        for pub in schema.publications
    ]


def map_skills(schema: Optional[SkillsListSchema]) -> List[Skill]:
    """Map SkillsListSchema to list of Skill models.

    Args:
        schema: The schema object to map

    Returns:
        List of Skill models or empty list if schema is None or wrong type
    """
    if not isinstance(schema, SkillsListSchema) or not schema.skills:
        return []

    return [
        Skill(category=skill.category, skills=skill.skills) for skill in schema.skills
    ]


def map_career_summary(schema: Optional[CareerSummarySchema]) -> CareerSummary:
    """Map CareerSummarySchema to CareerSummary model.

    Args:
        schema: The schema object to map

    Returns:
        CareerSummary model (default if schema is None or wrong type)
    """
    if not isinstance(schema, CareerSummarySchema):
        # Create default CareerSummary
        return CareerSummary(job_titles=[], years_of_experience="", default_summary="")

    return CareerSummary(
        job_titles=schema.job_titles,
        years_of_experience=schema.years_of_experience,
        default_summary=schema.default_summary,
    )


def map_schema_to_portfolio(
    portfolio: Portfolio,
    section_name: str,
    schema_result: Union[
        AwardsListSchema,
        ProjectsListSchema,
        WorkExperienceListSchema,
        EducationListSchema,
        PublicationsListSchema,
        SkillsListSchema,
        CareerSummarySchema,
        None,
    ],
) -> Portfolio:
    """Map schema result to appropriate portfolio section.

    Args:
        portfolio: Portfolio object to update
        section_name: Name of the section to update
        schema_result: Schema result from LLM

    Returns:
        Updated portfolio object
    """
    if schema_result is None:
        # Handle case where schema_result is None
        return portfolio

    if section_name == "awards":
        portfolio.awards = map_awards(schema_result)
    elif section_name == "projects":
        portfolio.projects = map_projects(schema_result)
    elif section_name == "work_experience":
        portfolio.work_experience = map_work_experience(schema_result)
    elif section_name == "education":
        portfolio.education = map_education(schema_result)
    elif section_name == "publications":
        portfolio.publications = map_publications(schema_result)
    elif section_name == "skills":
        portfolio.skills = map_skills(schema_result)
    elif section_name == "career_summary":
        portfolio.career_summary = map_career_summary(schema_result)

    return portfolio
