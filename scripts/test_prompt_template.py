#!/usr/bin/env python
"""
Test script for verifying template variable substitution using string.Template.

This script demonstrates how variable substitution should work with underscore notation
which is compatible with Python's string.Template class.
"""

import asyncio
import re
import sys
from pathlib import Path
from string import Template

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.logging_config import configure_logging, get_logger

# Set up logging
configure_logging()
logger = get_logger(__name__)


def test_template_substitution():
    """Test template substitution with underscore notation."""

    # Sample test template using underscore notation (compatible with string.Template)
    test_template = """
    Career Summary:
    Create a concise career summary of ${career_summary_details_min_words} to
    ${career_summary_details_max_words} words.

    Work Experience:
    Choose the top ${work_experience_details_max_jobs} positions.
    For each position, include ${work_experience_details_bullet_points_per_job} bullet points.

    Skills:
    Choose exactly ${skills_details_max_categories} skill categories.
    Include ${skills_details_min_skills_per_category} to ${skills_details_max_skills_per_category} skills per category.

    Projects:
    Choose ${project_details_max_projects} projects most relevant to the target position.
    For each project, include ${project_details_bullet_points_per_project} key bullet points.

    Publications:
    Choose up to ${publications_details_max_publications} publications.

    Awards:
    Choose up to ${awards_details_max_awards} awards.
    """

    # Create mock preferences in flat structure
    mock_variables = {
        "career_summary_details_min_words": 10,
        "career_summary_details_max_words": 15,
        "work_experience_details_max_jobs": 4,
        "work_experience_details_bullet_points_per_job": 3,
        "skills_details_max_categories": 5,
        "skills_details_min_skills_per_category": 8,
        "skills_details_max_skills_per_category": 10,
        "project_details_max_projects": 5,
        "project_details_bullet_points_per_project": 3,
        "education_details_max_entries": 3,
        "education_details_max_courses": 4,
        "publications_details_max_publications": 3,
        "awards_details_max_awards": 4,
    }

    # Print variables for debugging
    logger.info(f"Template variables: {mock_variables}")

    # Apply template substitution using string.Template
    template = Template(test_template)
    formatted_text = template.substitute(mock_variables)

    # Print the result
    logger.info("Formatted template:")
    print(formatted_text)

    # Check for any remaining variables
    unresolved_vars = re.findall(r"\${([a-zA-Z_]+)}", formatted_text)
    if unresolved_vars:
        logger.warning(f"Unresolved variables: {unresolved_vars}")
    else:
        logger.info("All variables successfully substituted")

    return formatted_text


def test_nested_to_flat_conversion():
    """Test converting nested preferences to flat variables with underscore notation."""

    # Create mock preferences (simulating MongoDB document structure)
    mock_preferences = {
        "project_details": {"max_projects": 5, "bullet_points_per_project": 3},
        "work_experience_details": {"max_jobs": 4, "bullet_points_per_job": 3},
        "skills_details": {
            "max_categories": 5,
            "min_skills_per_category": 8,
            "max_skills_per_category": 10,
        },
        "career_summary_details": {"min_words": 10, "max_words": 15},
        "education_details": {"max_entries": 3, "max_courses": 4},
        "publications_details": {"max_publications": 3},
        "awards_details": {"max_awards": 4},
    }

    # Convert nested structure to flat variables with underscore notation
    flat_variables = {}
    for section, section_data in mock_preferences.items():
        if isinstance(section_data, dict):
            for key, value in section_data.items():
                var_name = f"{section}_{key}"
                flat_variables[var_name] = str(value)

    # Print the conversion result
    logger.info("Nested preferences converted to flat variables:")
    for var_name, value in flat_variables.items():
        logger.info(f"  {var_name} = {value}")

    # Simple template for testing
    test_template = "Projects: ${project_details_max_projects}, Skills: ${skills_details_max_categories}"

    # Apply template substitution
    template = Template(test_template)
    result = template.substitute(flat_variables)

    logger.info(f"Template substitution result: {result}")
    return flat_variables


def main():
    """Run the tests."""
    logger.info("Starting template substitution tests")

    # Test direct template substitution with underscore notation
    logger.info("Test 1: Direct template substitution with underscore notation")
    test_template_substitution()

    # Test converting nested preferences to flat variables
    logger.info("\nTest 2: Converting nested preferences to flat variables")
    test_nested_to_flat_conversion()

    logger.info("Template substitution tests completed")


if __name__ == "__main__":
    main()
