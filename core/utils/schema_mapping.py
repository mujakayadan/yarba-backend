"""Utility functions for mapping between resume generation output schema and database models."""

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
from core.models.profile import PersonalInformation
from core.schemas.resume_schemas import (
    AwardSchema,
    CareerSummarySchema,
    EducationSchema,
    PersonalInformationSchema,
    ProjectSchema,
    PublicationSchema,
    ResumeOutputSchema,
    SkillCategorySchema,
    WorkExperienceSchema,
)

# --- Individual Section Mappers --- #


def _map_personal_info(
    schema: PersonalInformationSchema,
) -> PersonalInformation:
    """Map PersonalInformationSchema to PersonalInformation model."""
    # Handles potential None values from schema
    return PersonalInformation(
        full_name=schema.full_name or "Default User",
        email=schema.email or "user@example.com",
        phone=schema.phone,
        address=schema.address,
        linkedin=schema.linkedin,
        github=schema.github,
        website=schema.website,
    )


def _map_career_summary(
    schema: CareerSummarySchema,
) -> CareerSummary:
    """Map CareerSummarySchema to CareerSummary model."""
    # NOTE: years_of_experience comes from the Profile, not the LLM output schema currently.
    # We map the LLM's selected job_title to the job_titles list.
    return CareerSummary(
        job_titles=[schema.job_title] if schema.job_title else [],
        years_of_experience="",  # This should be populated later from the Profile
        default_summary=schema.default_summary or "",
    )


def _map_skills(schemas: list[SkillCategorySchema]) -> list[Skill]:
    """Map list of SkillCategorySchema to list of Skill models."""
    if not schemas:
        return []
    return [
        Skill(category=skill.category, skills=skill.skills)
        for skill in schemas
        if skill and skill.category  # Basic validation
    ]


def _map_work_experience(schemas: list[WorkExperienceSchema]) -> list[WorkExperience]:
    """Map list of WorkExperienceSchema to list of WorkExperience models."""
    if not schemas:
        return []
    return [
        WorkExperience(
            job_title=exp.job_title,
            company=exp.company,
            location=exp.location,
            time=exp.time,
            responsibilities=exp.responsibilities,
        )
        for exp in schemas
        if exp  # Basic validation
    ]


def _map_education(schemas: list[EducationSchema]) -> list[Education]:
    """Map list of EducationSchema to list of Education models."""
    if not schemas:
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
        for edu in schemas
        if edu  # Basic validation
    ]


def _map_projects(schemas: list[ProjectSchema]) -> list[Project]:
    """Map list of ProjectSchema to list of Project models."""
    if not schemas:
        return []
    return [
        Project(
            name=project.name,
            bullet_points=project.bullet_points,
            date=project.date,
            link=project.link,
        )
        for project in schemas
        if project  # Basic validation
    ]


def _map_publications(schemas: list[PublicationSchema]) -> list[Publication]:
    """Map list of PublicationSchema to list of Publication models."""
    if not schemas:
        return []
    return [
        Publication(
            name=pub.name,
            publisher=pub.publisher,
            link=pub.link or "",
            time=pub.time,
        )
        for pub in schemas
        if pub  # Basic validation
    ]


def _map_awards(schemas: list[AwardSchema]) -> list[Award]:
    """Map list of AwardSchema to list of Award models."""
    if not schemas:
        return []
    return [
        Award(name=award.name, explanation=award.explanation)
        for award in schemas
        if award  # Basic validation
    ]


# --- Main Mapping Function --- #


def map_resume_output_to_models(
    resume_output: ResumeOutputSchema,
) -> tuple[Portfolio, PersonalInformation]:
    """Map the complete ResumeOutputSchema to Portfolio and PersonalInformation models.

    Args:
        resume_output: The structured resume data from LLM output.

    Returns:
        A tuple containing the populated Portfolio model and PersonalInformation model.
    """
    # Map Personal Information first
    personal_info_model = _map_personal_info(
        resume_output.personal_information
        if resume_output.personal_information
        else PersonalInformationSchema(
            full_name="", email=""
        )  # Provide default if missing
    )

    # Map each portfolio section
    portfolio = Portfolio(
        # Map career summary, ensuring it exists
        career_summary=_map_career_summary(
            resume_output.career_summary
            if resume_output.career_summary
            else CareerSummarySchema(
                job_title="", default_summary=""
            )  # Provide default
        ),
        # Map lists, handling potential None or empty lists from schema
        skills=_map_skills(resume_output.skills or []),
        work_experience=_map_work_experience(resume_output.work_experience or []),
        education=_map_education(resume_output.education or []),
        projects=_map_projects(resume_output.projects or []),
        publications=_map_publications(resume_output.publications or []),
        awards=_map_awards(resume_output.awards or []),
        # Note: other portfolio fields like 'templates' or 'settings' are not mapped here
    )

    return portfolio, personal_info_model
