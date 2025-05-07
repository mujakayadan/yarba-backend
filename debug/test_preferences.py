#!/usr/bin/env python
"""Test script for preference handling in resume generation.

This script tests the preference handling in the Resume Generation Service
using real services and real data with the test user ID.
"""

import asyncio
import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Suppress noisy third-party debug logs
for noisy_logger in [
    "pymongo",
    "beanie",
    "httpcore",
    "httpx",
    "motor",
    "bson",
    "asyncio",
    "uvicorn",
    "starlette",
    "litellm",
]:
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from beanie import PydanticObjectId

from config.logging_config import configure_logging, get_logger
from config.settings import settings
from core.database.init import init_db
from core.models.resume import Resume
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.services.job_service import JobService
from core.services.latex_service import LatexService
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService
from core.services.resume_generation_service import ResumeGenerationService
from core.utils.preference_utils import get_prompt_preferences
from utils.text import sanitize_mongodb_uri

# Configure logging
configure_logging()
logger = get_logger(__name__)


async def setup_database():
    """Set up MongoDB connection and initialize Beanie."""
    # Log database connection info from settings
    logger.info(f"Database settings loaded from config:")
    sanitized_uri = sanitize_mongodb_uri(settings.database.url)
    logger.info(f"MongoDB URI: {sanitized_uri}")
    logger.info(f"Database name: {settings.database.name}")

    # Initialize database using the project's init_db function
    logger.info("Initializing database connection...")
    client = await init_db()
    if not client:
        raise RuntimeError("Failed to initialize database connection")

    logger.info("Database connection established successfully")
    return client


async def test_preferences():
    """Test preference handling using real services with test user ID."""
    logger.info("Testing preference handling with services")

    # Get repositories
    profile_repo = ProfileRepository()

    # Get profile using test user ID
    profile = await profile_repo.get_by_user_id(settings.test_user_id)

    if profile:
        logger.info(f"Found profile for test user: {settings.test_user_id}")

        # Get preferences from profile
        preferences = get_prompt_preferences(profile)

        # Log preferences
        formatted = json.dumps(preferences, indent=2)
        logger.info(f"Preferences for test user:\n{formatted}")

        # Check for key sections
        required_sections = [
            "career_summary",
            "skills",
            "work_experience",
            "education",
            "project",
        ]
        for section in required_sections:
            if section not in preferences:
                logger.error(f"Missing required section in preferences: {section}")
            else:
                logger.info(
                    f"Section {section} exists with {len(preferences[section])} settings"
                )

        # Test prompt service
        prompt_service = PromptService(user_id=settings.test_user_id)
        logger.info("Testing prompt service...")

        # Get available prompts
        available_prompts = await prompt_service.get_available_prompts()
        logger.info(f"Available prompts: {available_prompts}")

        # Get system prompt
        system_prompt = await prompt_service.get_system_prompt()
        logger.info(f"System prompt length: {len(system_prompt)} characters")

        # Get resume prompt
        resume_prompt = await prompt_service.get_resume_prompt()
        logger.info(f"Resume prompt length: {len(resume_prompt)} characters")

        return preferences
    else:
        logger.error(f"No profile found for test user ID: {settings.test_user_id}")
        logger.info("Using default preferences from settings")
        default_preferences = settings.preferences.get_prompt_variables()
        return default_preferences


async def test_resume_with_preferences():
    """Test resume generation with preferences."""
    logger.info("Testing resume generation with preferences")

    # Create repositories
    resume_repo = ResumeRepository()
    portfolio_repo = PortfolioRepository()
    profile_repo = ProfileRepository()

    # Get profile for test user
    profile = await profile_repo.get_by_user_id(settings.test_user_id)
    if not profile:
        logger.error(f"No profile found for test user ID: {settings.test_user_id}")
        return

    logger.info(f"Found profile for test user ID: {settings.test_user_id}")

    # Get or create portfolio
    portfolio = None
    try:
        portfolio = await portfolio_repo.get_by_user_id(settings.test_user_id)
        if portfolio:
            logger.info(f"Found portfolio for test user ID: {settings.test_user_id}")
        else:
            logger.warning(
                f"No portfolio found for test user ID: {settings.test_user_id}"
            )
    except Exception as e:
        logger.error(f"Error retrieving portfolio: {e}")

    # Create job description
    job_description = """
    Senior Python Developer

    Company: Tech Innovations Inc.
    Location: Remote

    Job Description:
    We are looking for a Senior Python Developer to join our growing engineering team. The ideal candidate will have extensive experience with Python, FastAPI, and MongoDB, and will be responsible for designing, implementing, and maintaining our backend services.

    Responsibilities:
    - Design, develop, and maintain high-quality Python applications
    - Write clean, maintainable, and efficient code
    - Lead code reviews and mentor junior developers
    - Work closely with other teams to integrate systems and solve complex problems
    - Implement security and data protection measures

    Requirements:
    - 5+ years of experience with Python development
    - Strong experience with FastAPI, Flask, or Django
    - Experience with MongoDB and other NoSQL databases
    - Solid understanding of RESTful APIs and microservices architecture
    - Experience with Docker and container orchestration
    - Excellent problem-solving skills and attention to detail
    """

    # Use JobService to extract job information
    # Initialize prompt service first
    prompt_service = PromptService(user_id=settings.test_user_id)

    # Then initialize LLM service with prompt_service
    llm_service = LLMService(
        profile_repository=profile_repo,
    )
    await llm_service.configure_for_user(settings.test_user_id)

    # Create JobService with the LLM service
    job_service = JobService(llm_service=llm_service, prompt_service=prompt_service)

    # Extract job information
    logger.info("Extracting job information using JobService...")
    try:
        # Using a more direct approach for testing
        job_info = await job_service.extract_job_info(job_description)
        if job_info and isinstance(job_info, dict):
            company_name = job_info.get("company_name", "Tech Innovations Inc.")
            job_title = job_info.get("job_title", "Senior Python Developer")
            logger.info(f"Extracted company name: {company_name}")
            logger.info(f"Extracted job title: {job_title}")
        else:
            # Fallback if job_info is not properly structured
            company_name = "Tech Innovations Inc."
            job_title = "Senior Python Developer"
            logger.info(
                f"Using default company name and job title from job description"
            )
    except Exception as e:
        logger.error(f"Error extracting job information: {e}")
        # Always have a fallback for testing
        company_name = "Tech Innovations Inc."
        job_title = "Senior Python Developer"
        logger.info(f"Using fallback company name: {company_name}")
        logger.info(f"Using fallback job title: {job_title}")

    # Create a new Resume
    from core.models.resume import Resume

    current_time = datetime.now(timezone.utc)

    new_resume = Resume(
        user_id=settings.test_user_id,
        profile_id=profile.id,
        portfolio_id=portfolio.id if portfolio else None,
        title="Test Resume for Preferences",
        job_description=job_description,
        content={},
        created_at=current_time,
        updated_at=current_time,
        version=1,
        template_id="default",
        company_name=company_name,
        job_title=job_title,
    )

    # Create and save the resume to database
    logger.info("\n--- STEP 1: Creating Resume ---")
    await new_resume.create()
    resume_id = new_resume.id
    logger.info(f"Created new resume with ID: {resume_id}")

    # Create output directory for results
    debug_dir = Path("debug/output")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{timestamp}_{resume_id}"
    output_dir = debug_dir / folder_name
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created output directory: {output_dir}")

    # Create ResumeGenerationService and generate content
    try:
        # Create the full service stack
        logger.info("\n--- STEP 2: Initializing Services ---")

        # Instantiate required services (previously missing)
        from core.repositories.user_repository import UserRepository
        from core.services.portfolio_service import PortfolioService
        from core.services.profile_service import ProfileService

        user_repo = UserRepository()  # Needed for Profile/Portfolio services

        profile_service = ProfileService(profile_repo, user_repo)
        portfolio_service = PortfolioService(portfolio_repo, user_repo)
        latex_service = LatexService(
            portfolio_service=portfolio_service
        )  # Pass the required argument

        # Instantiate ResumeGenerationService with all required dependencies
        resume_generation_service = ResumeGenerationService(
            resume_repository=resume_repo,
            portfolio_repository=portfolio_repo,
            profile_repository=profile_repo,
            prompt_service=prompt_service,  # Already instantiated
            profile_service=profile_service,  # Added
            portfolio_service=portfolio_service,  # Added
            llm_service=llm_service,  # Already instantiated
            latex_service=latex_service,  # Added
        )

        # Configure service for the test user
        logger.info(
            f"Configuring ResumeGenerationService for user: {settings.test_user_id}"
        )
        await resume_generation_service.configure_for_user(settings.test_user_id)

        # Log preferences from profile that will be used
        logger.info("\n--- STEP 3: Preparing Preferences ---")
        preferences = get_prompt_preferences(profile)
        preferences_file = output_dir / "profile_preferences.json"
        with open(preferences_file, "w", encoding="utf-8") as f:
            json.dump(preferences, f, indent=2)
        logger.info(f"Saved profile preferences to {preferences_file}")

        # Log LLM preferences from user's profile
        llm_preferences = None
        if hasattr(profile, "system_preferences") and profile.system_preferences:
            if (
                hasattr(profile.system_preferences, "llm")
                and profile.system_preferences.llm
            ):
                llm_preferences = profile.system_preferences.llm
                logger.info(
                    f"Using LLM preferences from user profile: {llm_preferences}"
                )

                # Save LLM preferences to file
                llm_prefs_file = output_dir / "llm_preferences.json"
                with open(llm_prefs_file, "w", encoding="utf-8") as f:
                    json.dump(llm_preferences, f, indent=2, default=str)
                logger.info(f"Saved LLM preferences to {llm_prefs_file}")
            else:
                logger.warning(
                    "No LLM preferences found in user profile system_preferences"
                )
        else:
            logger.warning("No system_preferences found in user profile")

        # Generate resume content
        logger.info("\n--- STEP 4: Generating Resume Content ---")
        # Note: LLM preferences (model, temperature, etc.) are now taken from the user's profile system_preferences.llm
        try:
            resume_content = await resume_generation_service.generate_complete_resume(
                resume_id
            )
            logger.info(
                f"Successfully generated resume content with {len(resume_content)} sections"
            )
        except Exception as content_err:
            logger.error(f"Error generating resume content: {content_err}")
            logger.error(traceback.format_exc())
            return  # Exit early if content generation fails

        # Save generated content
        content_file = output_dir / "resume_content.json"
        with open(content_file, "w", encoding="utf-8") as f:
            json.dump(resume_content, f, indent=2, default=str)
        logger.info(f"Saved generated resume content to {content_file}")

        # Generate LaTeX from the content
        logger.info("\n--- STEP 5: Generating LaTeX ---")
        # Fetch the updated resume object containing the generated content
        updated_resume = await resume_repo.get_by_id(resume_id)
        if not updated_resume:
            logger.error(
                f"Failed to fetch updated resume {resume_id} after content generation."
            )
            return
        # Pass the resume and profile objects to generate_latex
        latex_content = await resume_generation_service.generate_latex(
            updated_resume, profile
        )

        # Save LaTeX content
        latex_file = output_dir / "resume.tex"
        with open(latex_file, "w", encoding="utf-8") as f:
            f.write(latex_content)
        logger.info(f"Saved LaTeX to {latex_file}")

        # Compile to PDF
        logger.info("\n--- STEP 6: Compiling PDF ---")
        try:
            # Pass the resume and profile objects to compile_pdf
            pdf_content = await resume_generation_service.compile_pdf(
                updated_resume, profile
            )

            if pdf_content and len(pdf_content) > 0:
                pdf_file = output_dir / "resume.pdf"
                with open(pdf_file, "wb") as f:
                    f.write(pdf_content)
                logger.info(f"Successfully saved PDF to {pdf_file}")
            else:
                logger.error("PDF compilation returned empty content")
        except Exception as pdf_err:
            logger.error(f"Error compiling PDF: {pdf_err}")

        # Save the resume details
        logger.info("\n--- STEP 7: Saving Summary ---")
        resume_details = {
            "id": str(resume_id),
            "title": new_resume.title,
            "company_name": company_name,
            "job_title": job_title,
            "preferences": preferences,
        }

        details_file = output_dir / "resume_details.json"
        with open(details_file, "w", encoding="utf-8") as f:
            json.dump(resume_details, f, indent=2, default=str)
        logger.info(f"Saved resume details to {details_file}")

        # Print summary of the test
        logger.info("\n" + "=" * 60)
        logger.info("RESUME GENERATION TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Resume ID: {resume_id}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Generated files:")
        logger.info(f"  - Resume content: {content_file}")
        logger.info(f"  - LaTeX file: {latex_file}")
        logger.info(f"  - PDF file: {output_dir / 'resume.pdf'}")
        logger.info(f"  - Preferences: {preferences_file}")
        if (
            hasattr(profile, "system_preferences")
            and profile.system_preferences
            and hasattr(profile.system_preferences, "llm")
            and profile.system_preferences.llm
        ):
            logger.info(f"  - LLM preferences: {output_dir / 'llm_preferences.json'}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error in resume generation: {e}")
        logger.error(traceback.format_exc())


async def main():
    """Run the test functions."""
    client = None
    start_time = datetime.now()
    try:
        logger.info("=" * 80)
        logger.info("STARTING PREFERENCE TESTS WITH REAL SERVICES")
        logger.info("=" * 80)

        # Set up database connection
        logger.info("\n\n1. Setting up database connection...")
        client = await setup_database()

        # Test preferences
        logger.info("\n\n2. Testing preferences from user profile...")
        preferences = await test_preferences()
        if preferences:
            logger.info("✓ Successfully retrieved preferences")
        else:
            logger.warning("! Could not retrieve preferences")

        # Test resume with preferences
        logger.info("\n\n3. Testing resume generation with preferences...")
        await test_resume_with_preferences()

        end_time = datetime.now()
        duration = end_time - start_time

        logger.info("\n\n" + "=" * 80)
        logger.info("TESTS COMPLETED SUCCESSFULLY")
        logger.info(f"Total execution time: {duration}")
        logger.info("=" * 80)
    except Exception as e:
        end_time = datetime.now()
        duration = end_time - start_time

        logger.error("!" * 80)
        logger.error(f"TEST FAILED WITH ERROR: {e}")
        logger.error(traceback.format_exc())
        logger.error(f"Failed after running for: {duration}")
        logger.error("!" * 80)
    finally:
        # Clean up database connection
        if client is not None:
            try:
                client.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")


if __name__ == "__main__":
    asyncio.run(main())
