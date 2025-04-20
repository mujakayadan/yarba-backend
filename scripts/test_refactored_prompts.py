#!/usr/bin/env python
"""
Test the refactored PromptLoader and PromptService classes.

This script verifies that our refactored approach with separate concerns works correctly:
- PromptLoader: Only responsible for loading raw prompt templates
- PromptService: Responsible for formatting prompts with user preferences
- Using a single 'data' object instead of separate portfolio and profile objects
- Using Jinja2 templates with {{ var }} syntax instead of ${var} syntax
"""

import asyncio
import datetime
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env files
load_dotenv(Path(__file__).parent.parent / ".env.local")
load_dotenv(Path(__file__).parent.parent / ".env")

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from beanie import PydanticObjectId

from config.logging_config import configure_logging, get_logger
from config.settings import settings
from core.database.init import init_db
from core.loaders.prompt_loader import PromptLoader
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.user_repository import UserRepository
from core.services.portfolio_service import PortfolioService
from core.services.profile_service import ProfileService
from core.services.prompt_service import PromptService
from core.utils.json_helper import convert_to_serializable, dumps, loads

# Set up logging
configure_logging()
logger = get_logger(__name__)


def count_variables(prompt: str) -> int:
    """Count unresolved variables in a prompt."""
    # Jinja2 variable pattern
    var_pattern = r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}"
    matches = re.findall(var_pattern, prompt)
    return len(matches)


async def test_prompt_loader():
    """Test PromptLoader's responsibility of loading raw prompts."""

    logger.info("Testing PromptLoader (raw template loading)")

    # Initialize PromptLoader
    prompt_loader = PromptLoader()

    # Get the raw prompt names
    prompt_names = prompt_loader.get_all_prompt_names()
    logger.info(f"Available prompts: {prompt_names}")

    # Get a raw resume prompt
    raw_prompt = prompt_loader.get_prompt("resume")
    variable_count = count_variables(raw_prompt)
    logger.info(f"Raw resume prompt contains {variable_count} variables")

    # Verify the loader doesn't do any variable substitution
    assert variable_count > 0, "Raw prompt should contain variables"

    # Check that the prompt contains expected sections
    assert "SKILLS SECTION" in raw_prompt, "Raw prompt missing SKILLS SECTION"
    assert (
        "WORK EXPERIENCE SECTION" in raw_prompt
    ), "Raw prompt missing WORK EXPERIENCE SECTION"

    logger.info("PromptLoader test passed!")
    return raw_prompt


def clean_metadata(data):
    """Remove metadata fields from dictionaries or lists of dictionaries."""
    metadata_fields = [
        "_id",
        "id",
        "user_id",
        "profile_id",
        "portfolio_id",
        "created_at",
        "updated_at",
    ]

    if isinstance(data, dict):
        return {
            k: clean_metadata(v) for k, v in data.items() if k not in metadata_fields
        }
    elif isinstance(data, list):
        return [clean_metadata(item) for item in data]
    else:
        return data


async def get_real_user_data(user_id=None):
    """Get real user data from the database."""

    # Use test user ID from settings if none provided
    if user_id is None:
        user_id_str = settings.test_user_id
        user_id = PydanticObjectId(user_id_str) if user_id_str else None

    if not user_id:
        # Default test user ID if none configured
        user_id = PydanticObjectId("000000000000000000000000")

    logger.info(f"Getting real user data for user ID: {user_id}")

    # Initialize repositories
    user_repo = UserRepository()
    profile_repo = ProfileRepository()
    portfolio_repo = PortfolioRepository()

    # Initialize services
    portfolio_service = PortfolioService(
        user_repository=user_repo, portfolio_repository=portfolio_repo
    )
    profile_service = ProfileService(
        user_repository=user_repo, profile_repository=profile_repo
    )

    # Get portfolio and profile
    portfolio = await portfolio_service.get_portfolio_by_user_id(user_id)
    profile = await profile_service.get_profile_by_user_id(user_id)

    if not portfolio:
        logger.error(f"No portfolio found for user {user_id}")
        raise ValueError(f"No portfolio found for user {user_id}")

    if not profile:
        logger.error(f"No profile found for user {user_id}")
        raise ValueError(f"No profile found for user {user_id}")

    logger.info(f"Successfully retrieved portfolio and profile for user {user_id}")

    # Convert to dictionaries for easier manipulation
    portfolio_dict = convert_to_serializable(portfolio.model_dump())
    profile_dict = convert_to_serializable(profile.model_dump())

    # Prepare the combined data structure (merging portfolio data)
    combined_data = {**clean_metadata(portfolio_dict)}

    # Add personal information from profile
    if "personal_information" in profile_dict:
        combined_data["personal_information"] = clean_metadata(
            profile_dict["personal_information"]
        )
        logger.info("Added personal information from profile")

    # Get user preferences
    # For testing purposes, we'll load preferences directly rather than relying on PromptService
    # This is to verify that PromptService correctly handles preferences later
    preferences = await profile_service.get_preferences(user_id)
    preferences_dict = None

    # Check if profile has preferences
    if preferences:
        preferences_dict = clean_metadata(preferences.model_dump())
        logger.info("Using preferences from user profile")
        # Log some key preference values
        for key in [
            "career_summary_details",
            "work_experience_details",
            "skills_details",
        ]:
            if key in preferences_dict and preferences_dict[key]:
                logger.info(f"  Profile preference: {key} = {preferences_dict[key]}")
    else:
        logger.info("No preferences in profile, falling back to global settings")
        # Get preference settings from global settings
        preferences_dict = settings.preferences.get_prompt_variables()
        # Log some key preference values
        for key in [
            "career_summary_details_min_words",
            "work_experience_details_max_jobs",
            "skills_details_max_categories",
        ]:
            if key in preferences_dict:
                logger.info(f"  Default preference: {key} = {preferences_dict[key]}")

    return combined_data, preferences_dict, user_id, user_repo


async def test_prompt_service():
    """Test PromptService's responsibility of formatting prompts with variables."""

    logger.info("Testing PromptService (template formatting)")

    # Get real user data and preferences
    combined_data, preferences_dict, user_id, user_repo = await get_real_user_data()

    # Initialize PromptService with UserRepository
    prompt_service = PromptService(user_repository=user_repo)

    # Get a raw prompt for comparison
    raw_prompt = await prompt_service.get_prompt("resume")
    raw_variable_count = count_variables(raw_prompt)
    logger.info(f"Raw resume prompt contains {raw_variable_count} variables")

    # Test job description
    job_description = """
    Software Engineer

    Company: Tech Innovations
    Location: Remote, US

    Job Description:
    We are looking for a Software Engineer to join our growing team. You will be responsible for developing and maintaining web applications, implementing new features, and ensuring high performance and reliability of our systems.

    Requirements:
    - 3+ years of experience in software development
    - Proficiency in Python and JavaScript
    - Experience with web frameworks such as FastAPI, Django, or Flask
    - Familiarity with front-end technologies (React, Vue.js, or Angular)
    - Experience with databases (PostgreSQL, MongoDB)
    - Strong problem-solving skills
    - Excellent communication and teamwork abilities
    """

    # Log data structure summary
    logger.info("Combined data structure summary:")
    for key, value in combined_data.items():
        if isinstance(value, dict):
            logger.info(f"  {key}: dict with {len(value)} keys")
        elif isinstance(value, list):
            logger.info(f"  {key}: list with {len(value)} items")
        else:
            logger.info(f"  {key}: {type(value).__name__}")

    # Use the recommended approach with a single data object
    variables = {"job_description": job_description, "data": combined_data}

    # Format the prompt, passing the user_id
    formatted_prompt = await prompt_service.get_resume_prompt(
        variables, user_id=user_id
    )
    formatted_variable_count = count_variables(formatted_prompt)

    logger.info(
        f"Formatted prompt contains {formatted_variable_count} unresolved variables"
    )
    logger.info(f"Formatted prompt length: {len(formatted_prompt)} characters")

    # Verify variable substitution happened
    assert (
        formatted_variable_count < raw_variable_count
    ), "Variables should be substituted"
    assert len(formatted_prompt) > 1000, "Formatted prompt seems too short"

    # Check if required sections are present
    required_sections = [
        "SKILLS SECTION",
        "WORK EXPERIENCE SECTION",
        "EDUCATION SECTION",
    ]
    missing_sections = [
        section for section in required_sections if section not in formatted_prompt
    ]
    if missing_sections:
        logger.warning(
            f"Missing required sections in formatted prompt: {missing_sections}"
        )
    else:
        logger.info("All required sections are present in formatted prompt")

    # Verify that preferences are reflected in the formatted prompt
    # For example, if preferences.career_summary or preferences.career_summary_details_max_words is used
    if "preferences" in preferences_dict:
        career_summary = preferences_dict["preferences"].get("career_summary", {})
        if "max_words" in career_summary:
            max_words = career_summary["max_words"]
            logger.info(
                f"Checking for preference career_summary.max_words ({max_words})"
            )

            career_section = formatted_prompt.find("CAREER SUMMARY SECTION")
            if career_section > 0:
                career_text = formatted_prompt[career_section : career_section + 500]
                if str(max_words) in career_text:
                    logger.info(
                        f"Preference career_summary.max_words ({max_words}) is correctly reflected"
                    )
                else:
                    logger.warning(
                        f"Preference career_summary.max_words may not be correctly applied"
                    )
    elif "career_summary_details_max_words" in preferences_dict:
        max_words = preferences_dict["career_summary_details_max_words"]
        logger.info(
            f"Checking for preference career_summary_details_max_words ({max_words})"
        )

        career_section = formatted_prompt.find("CAREER SUMMARY SECTION")
        if career_section > 0:
            career_text = formatted_prompt[career_section : career_section + 500]
            if str(max_words) in career_text:
                logger.info(
                    f"Preference career_summary_details_max_words ({max_words}) is correctly reflected"
                )
            else:
                logger.warning(
                    f"Preference career_summary_details_max_words may not be correctly applied"
                )

    # Validate the prompt using the service's validation method
    validation = prompt_service.validate_prompt(formatted_prompt)
    if validation["is_valid"]:
        logger.info("Prompt validation passed: No unsubstituted variables found")
    else:
        logger.warning(
            f"Prompt contains unsubstituted variables: {validation['unsubstituted_vars']}"
        )
        if (
            "unsubstituted_expressions" in validation
            and validation["unsubstituted_expressions"]
        ):
            logger.warning(
                f"Prompt contains unsubstituted expressions: {validation['unsubstituted_expressions']}"
            )

    logger.info("PromptService test passed!")
    return formatted_prompt


async def show_formatting_difference(raw_prompt, formatted_prompt):
    """Show the difference between raw and formatted prompt sections."""

    # Find the skills section in both versions
    raw_start = raw_prompt.find("SKILLS SECTION")
    formatted_start = formatted_prompt.find("SKILLS SECTION")

    if raw_start > 0 and formatted_start > 0:
        # Extract a snippet of the skills section
        raw_end = raw_prompt.find("SECTION", raw_start + 15)
        if raw_end < 0:
            raw_end = raw_start + 300

        formatted_end = formatted_prompt.find("SECTION", formatted_start + 15)
        if formatted_end < 0:
            formatted_end = formatted_start + 300

        raw_section = raw_prompt[raw_start:raw_end]
        formatted_section = formatted_prompt[formatted_start:formatted_end]

        logger.info("\nRaw prompt SKILLS section:")
        print("---")
        print(raw_section[:200] + "...")  # Show first 200 chars
        print("---")

        logger.info("\nFormatted prompt SKILLS section:")
        print("---")
        print(formatted_section[:200] + "...")  # Show first 200 chars
        print("---")

        # Find variable placeholders in raw section (using Jinja2 syntax)
        variables = re.findall(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}", raw_section)
        if variables:
            logger.info(f"Variables in raw section: {variables}")

        # Check if these variables exist in formatted section
        for var in variables:
            placeholder = f"{{ {var} }}"  # Add spaces to make it easier to match
            if placeholder.replace(" ", "") in formatted_section:
                logger.info(f"Variable {var} was NOT substituted")
            else:
                logger.info(f"Variable {var} was successfully substituted")


async def check_for_metadata_fields(prompt):
    """Check if metadata fields are present in the prompt."""
    metadata_fields = [
        '_id":',
        'user_id":',
        'profile_id":',
        '"id":',
        'created_at":',
        'updated_at":',
    ]

    found_fields = []
    for field in metadata_fields:
        if field in prompt:
            found_fields.append(field.replace('":', ""))

    if found_fields:
        logger.warning(
            f"Found metadata fields in prompt that should be filtered: {found_fields}"
        )
    else:
        logger.info("No metadata fields found in prompt - good!")


async def test_llm_response_parsing():
    """Test LLM generation and response parsing, saving debug files for inspection."""

    logger.info("Testing LLM response generation and parsing")

    # Get real user data and preferences
    combined_data, preferences_dict, user_id, user_repo = await get_real_user_data()

    # Initialize services
    prompt_service = PromptService(user_repository=user_repo)
    profile_service = ProfileService(
        user_repository=user_repo, profile_repository=ProfileRepository()
    )

    # Create LLM service
    from core.services.llm_service import LLMService

    llm_service = LLMService(
        profile_service=profile_service,
        prompt_service=prompt_service,
        model="gpt-4.1-mini-2025-04-14",  # Use a model that can handle the full response
        temperature=0.1,
        enable_json_validation=True,
    )
    await llm_service.configure_for_user(user_id)

    # Create resume generation service with a mock LaTeX service to avoid initialization errors
    from core.repositories.resume_repository import ResumeRepository
    from core.services.resume_generation_service import ResumeGenerationService

    # Create a mock LaTeX service
    class MockLatexService:
        async def generate_resume_latex(self, resume_id):
            return "Mock LaTeX content"

        async def compile_latex_to_pdf(self, latex_content, is_cover_letter=False):
            return b"Mock PDF content"

    resume_service = ResumeGenerationService(
        resume_repository=ResumeRepository(),
        portfolio_repository=PortfolioRepository(),
        profile_repository=ProfileRepository(),
        profile_service=profile_service,
        llm_service=llm_service,
        prompt_service=prompt_service,
        latex_service=MockLatexService(),  # Use mock LaTeX service
    )

    # Test job description
    job_description = """
    Software Engineer

    Company: Tech Innovations
    Location: Remote, US

    Job Description:
    We are looking for a Software Engineer to join our growing team. You will be responsible for developing and maintaining web applications, implementing new features, and ensuring high performance and reliability of our systems.

    Requirements:
    - 3+ years of experience in software development
    - Proficiency in Python and JavaScript
    - Experience with web frameworks such as FastAPI, Django, or Flask
    - Familiarity with front-end technologies (React, Vue.js, or Angular)
    - Experience with databases (PostgreSQL, MongoDB)
    - Strong problem-solving skills
    - Excellent communication and teamwork abilities
    """

    # Add job description to the combined data
    combined_data["job_description"] = job_description

    # Add user_id to personal information
    if "personal_information" not in combined_data:
        combined_data["personal_information"] = {}
    combined_data["personal_information"]["user_id"] = str(user_id)

    # Unique trace ID for this test
    trace_id = "test_llm_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Get formatted prompt with user data
    logger.info("Generating formatted prompt")
    formatted_prompt = await prompt_service.get_resume_prompt(
        combined_data, user_id=user_id
    )
    system_prompt = await prompt_service.get_system_prompt(user_id=user_id)

    # Save the formatted prompt to a file for debugging
    debug_dir = Path(__file__).parent.parent / "debug"
    debug_dir.mkdir(exist_ok=True)

    with open(
        debug_dir / f"formatted_prompt_{trace_id}.txt", "w", encoding="utf-8"
    ) as f:
        f.write(formatted_prompt)

    with open(debug_dir / f"system_prompt_{trace_id}.txt", "w", encoding="utf-8") as f:
        f.write(system_prompt)

    # Call the LLM service to get a response
    logger.info("Calling LLM service for completion")
    try:
        response = await llm_service.get_completion(
            prompt=formatted_prompt,
            system_prompt=system_prompt,
            user_id=str(user_id),
            tags=["test", "resume_generation", f"trace:{trace_id}"],
        )

        # Save the raw response to a file
        with open(
            debug_dir / f"llm_raw_response_{trace_id}.txt", "w", encoding="utf-8"
        ) as f:
            f.write(response)

        # Parse the response with the resume service's method
        logger.info("Parsing LLM response")

        # Check if response is a complete JSON structure
        json_start = response.find("{")
        json_end = response.rfind("}")

        if json_start == -1 or json_end == -1 or json_start > json_end:
            logger.error("LLM response does not contain valid JSON structure")
            logger.error(f"Response excerpt: {response[:100]}...")

            # Save the error to a file
            with open(
                debug_dir / f"llm_error_{trace_id}.txt", "w", encoding="utf-8"
            ) as f:
                f.write(f"Error: Invalid JSON structure in LLM response\n\n")
                f.write(f"Response:\n{response}")

            # Try to fix the response by prepending the missing part
            if json_end != -1 and json_start == -1:
                logger.info("Attempting to fix truncated JSON response")
                fixed_response = (
                    '{"personal_information":{"full_name":"","title":"","phone":"","email":"","location":"","linkedin":"","github":""},"career_summary":{"job_title":"","years_of_experience":"0","default_summary":""'
                    + response
                )

                # Save the fixed response
                with open(
                    debug_dir / f"llm_fixed_response_{trace_id}.txt",
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(fixed_response)

                response = fixed_response

        parsed_content = resume_service._parse_llm_response(response, trace_id)

        # Save the parsed content to a file
        with open(
            debug_dir / f"parsed_content_{trace_id}.json", "w", encoding="utf-8"
        ) as f:
            json.dump(parsed_content, f, indent=2)

        # Check if parsed content has required sections
        required_sections = [
            "personal_information",
            "career_summary",
            "skills",
            "work_experience",
        ]
        missing_sections = [
            section for section in required_sections if section not in parsed_content
        ]

        if missing_sections:
            logger.error(
                f"Missing required sections in parsed content: {missing_sections}"
            )
        else:
            logger.info("All required sections are present in parsed content")

        # Log the structure of the parsed content
        logger.info("Parsed content structure:")
        for key, value in parsed_content.items():
            if isinstance(value, dict):
                logger.info(f"  {key}: dict with {len(value)} keys")
            elif isinstance(value, list):
                logger.info(f"  {key}: list with {len(value)} items")
            else:
                logger.info(f"  {key}: {type(value).__name__}")

        logger.info(f"LLM response testing completed. Debug files saved in {debug_dir}")
        return parsed_content

    except Exception as e:
        logger.error(f"Error in LLM response testing: {e}", exc_info=True)

        # Save the error to a file
        with open(debug_dir / f"llm_error_{trace_id}.txt", "w", encoding="utf-8") as f:
            f.write(f"Error: {str(e)}\n\n")
            import traceback

            f.write(traceback.format_exc())

        logger.info(f"Error details saved to {debug_dir}/llm_error_{trace_id}.txt")
        raise


async def main():
    """Run the tests."""
    logger.info("Starting refactored prompt tests")

    try:
        # Initialize the database
        logger.info("Initializing database connection")
        await init_db()

        # Test PromptLoader
        raw_prompt = await test_prompt_loader()

        # Test PromptService with real data
        formatted_prompt = await test_prompt_service()

        # Test LLM response parsing
        llm_content = await test_llm_response_parsing()

        # Check for metadata fields
        await check_for_metadata_fields(formatted_prompt)

        # Show the difference between raw and formatted
        await show_formatting_difference(raw_prompt, formatted_prompt)

        logger.info("Refactored prompt tests completed successfully!")
    except Exception as e:
        logger.error(f"Error in refactored prompt tests: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
