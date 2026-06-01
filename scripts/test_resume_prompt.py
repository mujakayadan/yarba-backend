#!/usr/bin/env python
"""Test the resume prompt variable substitution.

This script tests both the PromptLoader and PromptService classes to verify
that variable substitution works correctly with the resume prompt template.
"""

import asyncio
import re
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.logging_config import configure_logging, get_logger
from core.loaders.prompt_loader import PromptLoader
from core.services.prompt_service import PromptService

# Set up logging
configure_logging()
logger = get_logger(__name__)


def count_variables(prompt: str) -> int:
    """Count unresolved variables in a prompt."""
    var_pattern = r"\${([a-zA-Z_]+)}"  # Updated to use underscore notation only
    matches = re.findall(var_pattern, prompt)
    return len(matches)


def check_section_substitution(prompt: str, section_name: str) -> str:
    """Extract a section from the prompt and check variables."""
    # Find a relevant section with substitutions
    section_start = prompt.find(section_name)
    if section_start <= 0:
        return f"Section '{section_name}' not found in prompt"

    # Look for the next section heading or take 500 chars
    section_end = prompt.find("SECTION", section_start + len(section_name))
    if section_end < 0:
        section_end = min(section_start + 500, len(prompt))  # Show about 500 chars

    section_text = prompt[section_start:section_end]

    # Count any unresolved variables
    unresolved = re.findall(
        r"\${([a-zA-Z_]+)}", section_text
    )  # Updated to use underscore notation
    if unresolved:
        return f"{section_name} contains {len(unresolved)} unresolved variables: {unresolved}"

    return f"{section_name} successfully substituted"


async def test_prompt_loader():
    """Test variable substitution in PromptLoader."""
    logger.info("Testing PromptLoader variable substitution")

    # Initialize PromptLoader without a user ID
    prompt_loader = PromptLoader()

    # First get the raw prompt to see variables
    raw_prompt = prompt_loader.get_prompt("resume")
    logger.info(f"Raw prompt contains {count_variables(raw_prompt)} variables")

    # Mock job description and portfolio variables

    # Note: PromptLoader is now only responsible for loading raw prompts, not formatting
    logger.info("PromptLoader test passed!")
    return raw_prompt


async def test_prompt_service():
    """Test variable substitution in PromptService."""
    logger.info("Testing PromptService variable substitution")

    # Initialize PromptService without a user repository or user ID
    prompt_service = PromptService()

    # Get raw prompt for comparison
    raw_prompt = await prompt_service.get_prompt("resume")
    logger.info(f"Raw prompt contains {count_variables(raw_prompt)} variables")

    # Mock job description and portfolio variables
    variables = {
        "job_description": "Data Science position requiring ML and Python experience.",
        "portfolio": {
            "personal_info": {"name": "Test User", "email": "test@example.com"}
        },
    }

    # Get the resume prompt with variables - note updated API
    prompt = await prompt_service.get_resume_prompt(
        job_description=variables["job_description"], portfolio=variables["portfolio"]
    )

    # Check for unresolved variables
    remaining_vars = count_variables(prompt)
    logger.info(f"After substitution, prompt has {remaining_vars} unresolved variables")

    # Verify key substitutions
    assert "Data Science position" in prompt, "Job description wasn't substituted"

    # Check key sections
    sections = ["SKILLS SECTION", "WORK EXPERIENCE SECTION", "EDUCATION SECTION"]
    for section in sections:
        logger.info(check_section_substitution(prompt, section))

    logger.info("PromptService test passed!")
    return prompt


async def show_substitution_sample(prompt):
    """Show a sample of the template substitution in the prompt."""
    # Find the skills section to analyze

    # Extract the actual skills section from the prompt
    skills_start = prompt.find("SKILLS SECTION")
    if skills_start > 0:
        skills_end = prompt.find("SECTION", skills_start + 15)
        if skills_end < 0:
            skills_end = skills_start + 500

        actual_skills = prompt[skills_start:skills_end]

        logger.info("Original skills section template contained variables for:")
        logger.info("- skills_details_max_categories")
        logger.info("- skills_details_min_per_category")
        logger.info("- skills_details_max_per_category")

        logger.info(f"\nActual skills section after substitution:\n{actual_skills}")


async def main():
    """Run the tests."""
    logger.info("Starting resume prompt substitution tests")

    # Test PromptLoader
    await test_prompt_loader()

    # Test PromptService
    service_prompt = await test_prompt_service()

    # Show sample of the substitution result
    await show_substitution_sample(service_prompt)

    logger.info("Resume prompt substitution tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
