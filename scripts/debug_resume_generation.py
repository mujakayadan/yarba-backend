"""
Debug script for resume generation.

This script diagnoses issues with job description and portfolio data being passed to the LLM.
It uses the actual service classes with real LLM calls while logging all data flow.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path so imports work BEFORE other project imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from beanie import PydanticObjectId
from dotenv import load_dotenv

from config.logging_config import configure_logging
from config.settings import settings
from core.database.init import init_db
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.repositories.user_repository import UserRepository
from core.services.llm_service import LLMService
from core.services.portfolio_service import PortfolioService
from core.services.profile_service import ProfileService
from core.services.prompt_service import PromptService
from core.utils.json_helper import dumps

# Load environment variables from .env files
load_dotenv(Path(__file__).parent.parent / ".env.local")
load_dotenv(Path(__file__).parent.parent / ".env")

# Check if ANTHROPIC_API_KEY is loaded
if not os.environ.get("ANTHROPIC_API_KEY"):
    print("WARNING: ANTHROPIC_API_KEY environment variable is not set!")

# Set up logging (basicConfig should be called early)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("resume_debug")

# Configure project-specific logging (if it adds handlers or changes levels)
# If configure_logging also calls basicConfig, the above basicConfig might be redundant
# or could conflict. Assuming configure_logging is additive or idempotent here.
configure_logging()

# Sample job description to use if none is provided in resume
SAMPLE_JOB_DESCRIPTION = """
Software Engineer

Company: Meriti Inc.
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

Nice to Have:
- Experience with CI/CD pipelines
- Knowledge of containerization (Docker, Kubernetes)
- Experience with cloud platforms (AWS, GCP, Azure)

Benefits:
- Competitive salary
- Flexible work hours
- Remote work options
- Health insurance
- 401(k) plan
- Professional development opportunities
"""


class LoggingLLMService(LLMService):
    """Extended LLM Service that logs all inputs and outputs but uses real LLM."""

    async def get_completion(self, prompt, system_prompt, **kwargs):
        """Override to log the prompt and system prompt before calling the real LLM."""
        logger.info(f"LLM Service received system prompt ({len(system_prompt)} chars):")
        logger.info("--- START SYSTEM PROMPT ---")
        logger.info(system_prompt)
        logger.info("--- END SYSTEM PROMPT ---")

        logger.info(f"LLM Service received prompt ({len(prompt)} chars):")
        logger.info("--- START PROMPT FIRST 500 CHARS ---")
        logger.info(prompt[:500])
        logger.info("--- END PROMPT FIRST 500 CHARS ---")

        # Validate prompt before sending to LLM
        prompt_service = PromptService()
        validation = prompt_service.validate_prompt(prompt)
        if not validation["is_valid"]:
            logger.warning(
                f"Prompt contains unsubstituted variables: {validation['unsubstituted_vars']}"
            )

        # Check for metadata fields that shouldn't be sent to LLM
        self._check_for_metadata_fields(prompt)

        # Call the actual LLM service
        start_time = datetime.now()
        try:
            response = await super().get_completion(prompt, system_prompt, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"LLM response received in {duration:.2f} seconds")

            # Log response summary
            logger.info(f"Response length: {len(response)}")
            logger.info("--- RESPONSE FIRST 200 CHARS ---")
            logger.info(response[:200])
            logger.info("--- END RESPONSE SNIPPET ---")

            return response
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            raise

    def _check_for_metadata_fields(self, prompt: str) -> None:
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

            # Log specific instances to help debugging (getting 50 chars around each occurrence)
            for field in found_fields:
                index = prompt.find(f'"{field}":')
                if index >= 0:
                    start = max(0, index - 25)
                    end = min(len(prompt), index + 25)
                    context = prompt[start:end].replace("\n", " ").strip()
                    logger.warning(f"Context around '{field}': ...{context}...")
        else:
            logger.info("No metadata fields found in prompt - good!")

        # Check for missing data fields
        if '"data":' not in prompt and '"portfolio":' not in prompt:
            logger.warning(
                "Neither 'data' nor 'portfolio' found in prompt, possible data structure issue"
            )

        if '"personal_information":' not in prompt:
            logger.warning(
                "No 'personal_information' found in prompt, might affect resume output"
            )


class LoggingPromptService(PromptService):
    """Extended Prompt Service that logs all operations."""

    async def get_resume_prompt(self, variables):
        """Override to log the variables and resulting prompt."""
        logger.info("PromptService.get_resume_prompt called with variables:")

        # Log keys and some basic info
        if variables:
            for key, value in variables.items():
                if isinstance(value, dict):
                    logger.info(
                        f"  {key}: dict with {len(value)} keys: {list(value.keys())}"
                    )

                    # For portfolio, log second level keys too
                    if key == "portfolio":
                        for k2, v2 in value.items():
                            if isinstance(v2, (dict, list)):
                                logger.info(
                                    f"    {k2}: {type(v2).__name__} with {len(v2)} items"
                                )
                            else:
                                logger.info(f"    {k2}: {type(v2).__name__}")
                elif isinstance(value, (list, tuple)):
                    logger.info(
                        f"  {key}: {type(value).__name__} with {len(value)} items"
                    )
                elif isinstance(value, str) and len(value) > 100:
                    logger.info(
                        f"  {key}: string of length {len(value)}, starts with: {value[:50]}..."
                    )
                else:
                    logger.info(f"  {key}: {value}")
        else:
            logger.warning("  No variables provided!")

        # Call original method
        result = await super().get_resume_prompt(variables)

        logger.info(f"Formatted resume prompt length: {len(result)}")
        logger.info(f"First 200 chars: {result[:200]}")

        return result

    def _format_template(self, template_str, variables):
        """Override to log the template formatting process."""
        logger.info(f"Formatting template with {len(variables)} variables")

        # Log which keys will be formatted
        import re

        template_vars = set(re.findall(r"\${([a-zA-Z_]+)}", template_str))
        logger.info(f"Template contains variables: {template_vars}")

        # Check for missing variables
        missing_vars = template_vars - set(variables.keys())
        if missing_vars:
            logger.warning(f"Missing variables in template: {missing_vars}")

            # For debugging purposes, make a copy to avoid modifying the original
            debug_variables = variables.copy()

            # Create placeholder data for missing variables to prevent template errors
            for var in missing_vars:
                if var == "job_description":
                    debug_variables[var] = variables.get(
                        "job_description", SAMPLE_JOB_DESCRIPTION
                    )
                elif var == "portfolio":
                    debug_variables[var] = variables.get(
                        "portfolio", {"placeholder": "Data for debugging"}
                    )
                else:
                    debug_variables[var] = f"[Missing: {var}]"

            # Use the debug variables for formatting
            variables = debug_variables

        # Log variable types and detect potential serialization issues
        for key, value in variables.items():
            if isinstance(value, (dict, list)):
                try:
                    # Use the custom dumps function that handles special types
                    dumps(value)
                except Exception as e:
                    logger.error(f"Cannot serialize {key}: {e}")

            if key in ("portfolio", "job_description") and not value:
                logger.warning(f"Variable {key} is empty or None!")

        # Format the template string - convert ${var} to Python string interpolation format {var}
        # This ensures complex objects like dictionaries and lists are properly passed
        python_template = template_str

        # Replace ${var} with {var} for string interpolation
        python_template = re.sub(r"\${([a-zA-Z_]+)}", r"{\1}", python_template)

        # For variables that should be JSON strings, convert them
        for key, value in variables.items():
            if isinstance(value, (dict, list)):
                if key == "portfolio" or key == "job_description":
                    # These need to be JSON strings in the template
                    # Use our custom dumps function that handles datetime, ObjectId, etc.
                    variables[key] = dumps(value)

        # Try to format the template using the new approach
        try:
            result = python_template.format(**variables)

            # Check for any remaining template variables
            unsubstituted = re.findall(r"\${([a-zA-Z_]+)}", result)
            if unsubstituted:
                logger.error(
                    f"Template still has unsubstituted variables after formatting: {unsubstituted}"
                )

            return result
        except Exception as e:
            logger.error(f"Error formatting template: {e}")
            logger.error(f"Variables: {list(variables.keys())}")
            logger.error(f"Template first 100 chars: {python_template[:100]}")

            # Fall back to the original implementation
            return super()._format_template(template_str, variables)


# Add ProfileService override with get_api_keys method
class DebugProfileService(ProfileService):
    """Extended Profile Service that provides a get_api_keys method."""

    async def get_api_keys(self, user_id):
        """Get API keys for a user."""
        logger.info(f"Getting API keys for user: {user_id}")

        try:
            # Get the profile to check if it has API keys
            await self.get_profile_by_user_id(user_id)

            # Get API keys from environment
            api_keys = {}
            if "OPENAI_API_KEY" in os.environ:
                api_keys["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]
            if "ANTHROPIC_API_KEY" in os.environ:
                api_keys["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]
            if "GEMINI_API_KEY" in os.environ:
                api_keys["GEMINI_API_KEY"] = os.environ["GEMINI_API_KEY"]

            logger.info(f"Found {len(api_keys)} API keys in environment")
            return api_keys

        except Exception as e:
            logger.error(f"Error getting API keys: {e}")
            return {}


async def test_direct_llm_call(resume_service, resume_id, llm_service=None):
    """Test calling the LLM directly using the same methods as the resume service.

    This function uses the same data preparation logic as the main resume service
    but allows direct inspection of the prompt and LLM output.
    """
    logger.info(f"Testing direct LLM call for resume {resume_id}")

    try:
        # Get the resume data using the service's method
        resume, profile, portfolio = await resume_service.get_resume_data(resume_id)
        logger.info(f"Retrieved resume data for resume {resume_id}")

        # Use the resume service's internal method to prepare generation data
        # This ensures we're using exactly the same data preparation logic
        generation_data = await resume_service._prepare_generation_data(
            user_id=resume.user_id,
            portfolio_id=resume.portfolio_id,
            job_description=resume.job_description,
        )
        logger.info(
            f"Prepared generation data with keys: {list(generation_data.keys())}"
        )

        # Get the LLM service from the resume service if not provided
        if not llm_service:
            llm_service = resume_service.llm_service

        # Get the prompt service from the LLM service
        prompt_service = llm_service.prompt_service

        # Format the resume prompt using the same method as the service
        system_prompt = await prompt_service.get_system_prompt()
        logger.info("Retrieved system prompt")

        # Format the resume prompt using the same method as the service
        formatted_prompt = await prompt_service.get_resume_prompt(generation_data)
        logger.info(f"Formatted resume prompt (length: {len(formatted_prompt)})")

        # Call the LLM directly - this is the only part that's "direct"
        logger.info("Sending request to LLM service directly")
        response = await llm_service.get_completion(
            prompt=formatted_prompt, system_prompt=system_prompt
        )

        # Parse the response using the same method as the service
        resume_content = resume_service._parse_llm_response(response, str(resume_id))
        logger.info("Parsed LLM response into structured content")

        return resume_content
    except Exception as e:
        logger.error(f"Error in direct LLM call: {e}")
        return None


async def get_or_create_test_resume(
    resume_repo: ResumeRepository,
    portfolio_service: PortfolioService,
    profile_service: ProfileService,
    user_id: str,
) -> PydanticObjectId:
    """Get an existing resume or create a new one for testing."""
    logger.info(f"Finding or creating a test resume for user {user_id}")

    # Convert string ID to PydanticObjectId if needed
    if isinstance(user_id, str):
        user_id = PydanticObjectId(user_id)

    # Check for existing resumes
    user_resumes = await resume_repo.get_by_user_id(user_id)

    if user_resumes and len(user_resumes) > 0:
        test_resume = user_resumes[0]
        logger.info(f"Using existing resume: {test_resume.id}")

        # Update the job description if it's empty
        if not test_resume.job_description:
            test_resume.job_description = SAMPLE_JOB_DESCRIPTION
            await resume_repo.update(test_resume.id, test_resume)
            logger.info("Updated empty job description in existing resume")

        return test_resume.id

    # No existing resume, create a new one
    # Get user profile
    profile = await profile_service.get_profile_by_user_id(user_id)
    if not profile:
        logger.error(f"No profile found for user {user_id}")
        raise ValueError(f"No profile found for user {user_id}")

    # Get portfolio
    portfolio = await portfolio_service.get_portfolio_by_user_id(user_id)
    if not portfolio:
        logger.error(f"No portfolio found for user {user_id}")
        raise ValueError(f"No portfolio found for user {user_id}")

    # Create new test resume
    from core.models.resume import Resume

    new_resume = Resume(
        user_id=user_id,
        profile_id=profile.id,
        portfolio_id=portfolio.id,
        title="Debug Test Resume",
        job_description=SAMPLE_JOB_DESCRIPTION,
        company_name="meriti_inc",
        job_title="software_engineer",
    )

    created_resume = await resume_repo.create(new_resume)
    logger.info(f"Created new test resume: {created_resume.id}")
    return created_resume.id


async def main():
    """Main function for testing resume generation."""
    try:
        logger.info("Starting resume generation debug script")

        # Get test user ID from settings
        test_user_id = settings.test_user_id
        logger.info(f"Using test user ID: {test_user_id}")

        # Initialize database
        logger.info("Initializing database connection")
        await init_db()

        # Initialize repositories
        logger.info("Initializing repositories")
        ResumeRepository()
        portfolio_repo = PortfolioRepository()
        profile_repo = ProfileRepository()
        user_repo = UserRepository()

        # Initialize services
        logger.info("Initializing services")
        PortfolioService(user_repository=user_repo, portfolio_repository=portfolio_repo)
        profile_service = DebugProfileService(
            user_repository=user_repo, profile_repository=profile_repo
        )
        prompt_service = LoggingPromptService()

        # Initialize LLM service with required profile_service
        llm_service = LoggingLLMService(
            profile_service=profile_service, prompt_service=prompt_service
        )

        # Get API keys for user
        logger.info(f"Getting API keys for user: {test_user_id}")
        api_keys = await profile_service.get_api_keys(test_user_id)
        logger.info(f"Found {len(api_keys)} API keys in environment")

        # Define sample job description
        job_description = """
        Data Scientist

        We are looking for a Data Scientist with strong Python and machine learning skills.
        Must have experience with deep learning frameworks like TensorFlow or PyTorch.
        3+ years of experience preferred.
        """

        # Define sample user portfolio and profile data
        portfolio_data = {
            "skills": {
                "Programming Languages": [
                    "Python",
                    "R",
                    "SQL",
                    "Java",
                    "JavaScript",
                    "C++",
                    "TypeScript",
                    "HTML/CSS",
                ],
                "Machine Learning": [
                    "TensorFlow",
                    "PyTorch",
                    "Scikit-learn",
                    "XGBoost",
                    "Neural Networks",
                    "Deep Learning",
                    "NLP",
                    "Computer Vision",
                ],
                "Data Engineering": [
                    "Apache Spark",
                    "Hadoop",
                    "AWS",
                    "GCP",
                    "Azure",
                    "Docker",
                    "Kubernetes",
                    "Airflow",
                ],
                "Databases": [
                    "PostgreSQL",
                    "MongoDB",
                    "Redis",
                    "Elasticsearch",
                    "Cassandra",
                    "DynamoDB",
                    "MySQL",
                    "SQLite",
                ],
                "Tools & Platforms": [
                    "Git",
                    "GitHub",
                    "Jupyter",
                    "VS Code",
                    "PyCharm",
                    "DataBricks",
                    "Tableau",
                    "Power BI",
                ],
            },
            "work_experience": [
                {
                    "company": "Tech AI Corp",
                    "job_title": "Senior Data Scientist",
                    "location": "San Francisco, CA",
                    "start_date": "2020-01",
                    "end_date": "Present",
                    "responsibilities": [
                        "Led a team of 5 data scientists on computer vision projects",
                        "Developed ML models for image classification with 95% accuracy",
                        "Implemented CI/CD pipelines for ML model deployment",
                    ],
                },
                {
                    "company": "DataTech Solutions",
                    "job_title": "Data Scientist",
                    "location": "Boston, MA",
                    "start_date": "2018-04",
                    "end_date": "2019-12",
                    "responsibilities": [
                        "Built recommendation engines with collaborative filtering",
                        "Created NLP models for sentiment analysis on customer reviews",
                        "Reduced infrastructure costs by 30% through optimization",
                    ],
                },
            ],
            "education": [
                {
                    "institution": "MIT",
                    "degree": "MS in Computer Science",
                    "location": "Cambridge, MA",
                    "start_date": "2016-09",
                    "end_date": "2018-05",
                    "gpa": "3.9",
                    "courses": [
                        "Machine Learning",
                        "Deep Learning",
                        "Data Mining",
                        "Algorithms",
                    ],
                },
                {
                    "institution": "Boston University",
                    "degree": "BS in Mathematics",
                    "location": "Boston, MA",
                    "start_date": "2012-09",
                    "end_date": "2016-05",
                    "gpa": "3.8",
                    "courses": [
                        "Linear Algebra",
                        "Statistics",
                        "Probability",
                        "Calculus",
                    ],
                },
            ],
        }

        profile_data = {
            "personal_information": {
                "full_name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1 (555) 123-4567",
                "location": "San Francisco, CA",
                "linkedin": "linkedin.com/in/johndoe",
                "github": "github.com/johndoe",
            }
        }

        # Helper function to clean metadata from data structures
        def clean_metadata(data):
            """Remove metadata fields from dictionaries or lists of dictionaries."""
            metadata_fields = [
                "id",
                "_id",
                "user_id",
                "profile_id",
                "portfolio_id",
                "created_at",
                "updated_at",
            ]

            if isinstance(data, dict):
                return {
                    k: clean_metadata(v)
                    for k, v in data.items()
                    if k not in metadata_fields
                }
            elif isinstance(data, list):
                return [clean_metadata(item) for item in data]
            else:
                return data

        # OPTION 1: Using the old approach (separate portfolio and profile)
        logger.info("=== OPTION 1: Using separated portfolio and profile ===")
        old_variables = {
            "job_description": job_description,
            "portfolio": portfolio_data,
            "profile": profile_data,
        }
        prompt_old = await prompt_service.get_resume_prompt(old_variables)
        logger.info(f"Generated prompt with old approach: {len(prompt_old)} chars")

        # OPTION 2: Using the new approach (combined data)
        logger.info("=== OPTION 2: Using combined data object ===")

        # Combine portfolio and personal information into a single data object
        combined_data = {**portfolio_data}
        combined_data["personal_information"] = profile_data["personal_information"]

        new_variables = {"job_description": job_description, "data": combined_data}
        prompt_new = await prompt_service.get_resume_prompt(new_variables)
        logger.info(f"Generated prompt with new approach: {len(prompt_new)} chars")

        # OPTION 3: Using the new approach with explicit metadata cleaning
        logger.info(
            "=== OPTION 3: Using combined data with explicit metadata cleaning ==="
        )

        # Clean metadata from both portfolio and profile data
        clean_portfolio = clean_metadata(portfolio_data)
        clean_profile = clean_metadata(profile_data)

        # Combine into a clean data structure
        clean_data = {**clean_portfolio}
        clean_data["personal_information"] = clean_profile["personal_information"]

        clean_variables = {"job_description": job_description, "data": clean_data}
        prompt_clean = await prompt_service.get_resume_prompt(clean_variables)
        logger.info(f"Generated prompt with clean approach: {len(prompt_clean)} chars")

        # Check for metadata fields
        for option_num, prompt in [
            ("1", prompt_old),
            ("2", prompt_new),
            ("3", prompt_clean),
        ]:
            metadata_fields = [
                '_id":',
                'user_id":',
                'profile_id":',
                '"id":',
                'created_at":',
                'updated_at":',
            ]
            found = False
            for field in metadata_fields:
                if field in prompt:
                    logger.warning(
                        f"Option {option_num} contains metadata field: {field}"
                    )
                    found = True
            if not found:
                logger.info(f"Option {option_num} is clean - no metadata fields found")

        # Verify the prompts are equivalent in content (ignoring metadata)
        logger.info(
            f"All approaches produce prompts with similar length: {len(prompt_old)} vs {len(prompt_new)} vs {len(prompt_clean)}"
        )

        # Send the prompt to the LLM
        logger.info("=== Sending prompt to LLM ===")
        system_prompt = (
            "You are an AI assistant that helps create professional resumes."
        )
        response = await llm_service.get_completion(prompt_clean, system_prompt)

        # Try to parse the response as JSON
        try:
            json_response = json.loads(response)
            logger.info("Successfully parsed response as JSON")
            logger.info(f"Response contains {len(json_response)} top-level fields")

            # Verify key sections exist
            expected_sections = [
                "personal_information",
                "career_summary",
                "skills",
                "work_experience",
                "education",
            ]

            missing_sections = [
                section for section in expected_sections if section not in json_response
            ]
            if missing_sections:
                logger.warning(
                    f"Response is missing expected sections: {missing_sections}"
                )
            else:
                logger.info("All expected sections are present in the response")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response as JSON: {e}")

    except Exception as e:
        logger.error(f"Error in resume generation test: {e}", exc_info=True)


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
