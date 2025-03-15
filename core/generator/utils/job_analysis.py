"""Job analysis utilities."""

from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from config.settings import Settings

logger = get_logger(__name__)
settings = Settings()


def check_clearance_requirement(job_description: str) -> bool:
    """
    Check if the job description contains security clearance requirements.

    Args:
        job_description: Job description text

    Returns:
        bool: True if clearance is required, False otherwise
    """
    if not job_description:
        return False

    clearance_keywords = settings.app.clearance_keywords
    return any(
        keyword.lower() in job_description.lower() for keyword in clearance_keywords
    )


def analyze_job_requirements(
    job_description: str,
    custom_keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Analyze job requirements from the description.

    Args:
        job_description: Job description text
        custom_keywords: Optional list of custom keywords to look for

    Returns:
        Dict[str, Any]: Analysis results containing:
            - requires_clearance: bool
            - experience_level: str
            - key_skills: List[str]
            - education_requirements: List[str]
            - matched_keywords: List[str]
    """
    if not job_description:
        return {
            "requires_clearance": False,
            "experience_level": "Unknown",
            "key_skills": [],
            "education_requirements": [],
            "matched_keywords": [],
        }

    # Check for clearance requirement
    requires_clearance = check_clearance_requirement(job_description)

    # Extract experience level
    experience_level = _extract_experience_level(job_description)

    # Extract key skills
    key_skills = _extract_key_skills(job_description)

    # Extract education requirements
    education_requirements = _extract_education_requirements(job_description)

    # Check for custom keywords
    matched_keywords = []
    if custom_keywords:
        matched_keywords = [
            keyword
            for keyword in custom_keywords
            if keyword.lower() in job_description.lower()
        ]

    return {
        "requires_clearance": requires_clearance,
        "experience_level": experience_level,
        "key_skills": key_skills,
        "education_requirements": education_requirements,
        "matched_keywords": matched_keywords,
    }


def _extract_experience_level(job_description: str) -> str:
    """Extract experience level from job description."""
    # TODO: Implement experience level extraction
    return "Unknown"


def _extract_key_skills(job_description: str) -> List[str]:
    """Extract key skills from job description."""
    # TODO: Implement key skills extraction
    return []


def _extract_education_requirements(job_description: str) -> List[str]:
    """Extract education requirements from job description."""
    # TODO: Implement education requirements extraction
    return []
