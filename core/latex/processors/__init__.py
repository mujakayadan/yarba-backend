"""Section processors for LaTeX document generation."""

from typing import Dict, Type

from core.latex.processors.awards import AwardsProcessor
from core.latex.processors.base import SectionProcessor
from core.latex.processors.career_summary import CareerSummaryProcessor
from core.latex.processors.certifications import CertificationsProcessor
from core.latex.processors.education import EducationProcessor
from core.latex.processors.personal_information import PersonalInformationProcessor
from core.latex.processors.projects import ProjectsProcessor
from core.latex.processors.publications import PublicationsProcessor
from core.latex.processors.skills import SkillsProcessor
from core.latex.processors.work_experience import WorkExperienceProcessor

# Map section names to their processors
SECTION_PROCESSORS: Dict[str, Type[SectionProcessor]] = {
    "personal_information": PersonalInformationProcessor,
    "career_summary": CareerSummaryProcessor,
    "skills": SkillsProcessor,
    "work_experience": WorkExperienceProcessor,
    "education": EducationProcessor,
    "projects": ProjectsProcessor,
    "awards": AwardsProcessor,
    "publications": PublicationsProcessor,
    "certifications": CertificationsProcessor,
}


def get_processor_for_section(section_name: str) -> Type[SectionProcessor]:
    """
    Get the appropriate processor for a section.

    Args:
        section_name: Name of the section

    Returns:
        A SectionProcessor class for the section
    """
    return SECTION_PROCESSORS.get(section_name, SectionProcessor)
