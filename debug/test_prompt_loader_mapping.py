"""Test the PromptLoader with profile preferences mapping."""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.logging_config import configure_logging, get_logger
from core.loaders.prompt_loader import PromptLoader


# Mock profile data structure - this simulates what we fetch from MongoDB
class MockPromptPreferences:
    """Mock prompt preferences."""

    def __init__(self, preferences_dict):
        """Initialize with dictionary."""
        self.__dict__.update(preferences_dict)

    def model_dump(self):
        """Return a dictionary of preferences."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class MockProfile:
    """Mock profile to test PromptLoader."""

    def __init__(self, prompt_preferences_dict=None):
        """Initialize mock profile."""
        self.prompt_preferences = (
            MockPromptPreferences(prompt_preferences_dict)
            if prompt_preferences_dict
            else None
        )
        self.life_story = "Born and raised in a tech-savvy family, I developed a passion for programming early on."


# Mock profile repository
class MockProfileRepository:
    """Mock repository for testing."""

    def __init__(self, mock_profile=None):
        """Initialize with mock profile."""
        self.mock_profile = mock_profile

    async def get_by_user_id(self, user_id):
        """Mock get_by_user_id method."""
        return self.mock_profile


# Mock profile preferences
def get_mock_profile_preferences():
    """Get mock profile preferences for testing."""
    return {
        "project": {"max_projects": 4, "bullet_points_per_project": 3},
        "work_experience": {"max_jobs": 4, "bullet_points_per_job": 3},
        "skills": {"max_categories": 5, "min_per_category": 3, "max_per_category": 7},
        "career_summary": {"min_words": 15, "max_words": 25, "tone": "professional"},
        "education": {"max_entries": 3, "max_courses": 4},
        "cover_letter": {"paragraphs": 5, "target_age": 25},
        "awards": {"max_awards": 4},
        "publications": {"max_publications": 3},
    }


async def mock_get_profile(self):
    """Mock the _get_profile method for testing."""
    return self._profile


def check_for_unprocessed_variables(text):
    """Check for any unprocessed Jinja2 variables or data references in text."""
    unprocessed = []

    # Check for Jinja2 variables
    for i, line in enumerate(text.split("\n")):
        if "{{" in line or "}}" in line:
            unprocessed.append((i + 1, "Jinja2", line))

    # Check for data references in JSON format at the end of template
    portfolio_data_section = text.split("Portfolio Data:")
    if len(portfolio_data_section) > 1:
        data_section = portfolio_data_section[1].strip()
        # Check if it's a raw dict/object instead of a string representation
        if data_section.startswith("{") and ("}" in data_section):
            unprocessed.append(
                (
                    text.count("\n") - data_section.count("\n"),
                    "JSON Object",
                    data_section,
                )
            )

    return unprocessed


async def test_prompt_loader_mapping():
    """Test PromptLoader with profile preferences mapping."""
    configure_logging()
    logger = get_logger("test_prompt_loader_mapping")

    # Create mock profile
    prompt_preferences = get_mock_profile_preferences()
    mock_profile = MockProfile(prompt_preferences)

    # Create a PromptLoader with mock data
    loader = PromptLoader(user_id="mock_user_id")
    loader._profile = mock_profile

    # Mock the _get_profile method
    loader._get_profile = lambda: asyncio.create_task(mock_get_profile(loader))

    # Test the preference variables
    variables = await loader._get_preference_variables()

    # Add required template data
    variables["portfolio_data"] = {"career_summary": {"years_of_experience": 5}}
    variables[
        "job_description"
    ] = """
We are looking for a Python developer with FastAPI experience.
The ideal candidate will have a strong understanding of Python and FastAPI.
They will also have experience with Docker and Kubernetes.
About the job
Role: Senior 3D Computer Vision Engineer

location: Newark, CA



Job Description:

Extensive knowledge and applied experience in 3D computer vision, multi-view geometry, SfM/SLAM
Strong skills in camera calibration, linear algebra, numerical optimization, factor graph representations and statistical estimation theory. Familiarity with OpenCV and image processing.
A solid foundation in math and robotics to propose creative solutions for autonomous systems
    """

    # Print the mapped variables
    print("\n=== Mapped Template Variables ===")
    if "preferences" in variables:
        print(json.dumps(variables["preferences"], indent=2))
    else:
        print("No preferences mapped!")

    # Test the format_prompt_with_variables method directly
    cover_letter_prompt = await loader.format_prompt_with_variables(
        "cover_letter", variables
    )
    resume_prompt = await loader.format_prompt_with_variables("resume", variables)

    # Save processed templates for inspection
    with open("debug/processed_resume.txt", "w") as f:
        f.write(resume_prompt)

    # Check for unprocessed variables
    print("\n=== Checking for Unprocessed Variables ===")
    unprocessed_cl = check_for_unprocessed_variables(cover_letter_prompt)
    unprocessed_resume = check_for_unprocessed_variables(resume_prompt)

    if unprocessed_cl:
        print("Unprocessed variables in cover letter prompt:")
        for line_num, var_type, line in unprocessed_cl:
            print(f"  Line {line_num} ({var_type}): {line}")
    else:
        print("✓ No unprocessed variables in cover letter prompt")

    if unprocessed_resume:
        print("Unprocessed variables in resume prompt:")
        for line_num, var_type, line in unprocessed_resume:
            print(f"  Line {line_num} ({var_type}): {line}")
    else:
        print("✓ No unprocessed variables in resume prompt")

    # Check cover letter prompt variable substitution
    print("\n=== Cover Letter Template - Variable Substitution ===")
    for line in cover_letter_prompt.split("\n"):
        if "paragraphs" in line.lower() and "create" in line.lower():
            print(f"Paragraphs: {line}")
        if "year old" in line.lower():
            print(f"Grade level: {line}")

    # Check work experience section
    print("\n=== Resume Template - Work Experience Section ===")
    in_work_section = False
    for line in resume_prompt.split("\n"):
        if "# WORK EXPERIENCE SECTION" in line:
            in_work_section = True
            print("Found Work Experience Section:")
        elif in_work_section and line.startswith("#"):
            in_work_section = False
        elif in_work_section and "Focus on" in line:
            print(f"  {line}")

    print("\nTest completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_prompt_loader_mapping())
