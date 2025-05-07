"""Test the prompt loader with actual user preferences from the database."""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.logging_config import configure_logging, get_logger
from config.settings import settings
from core.database.init import init_db
from core.services.prompt_service import PromptService
from prompts import COVER_LETTER_PROMPT, RESUME_PROMPT


async def test_prompt_service():
    """Test PromptService with actual user data."""
    # Configure logging
    configure_logging()
    logger = get_logger("test_prompt_service")
    logger.info("Testing PromptService with real user preferences")

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("debug/output") / f"{timestamp}_prompt_service_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created output directory: {output_dir}")

    # Initialize DB connection
    await init_db()

    # Create a PromptService instance with the test user ID
    test_user_id = settings.test_user_id
    logger.info(f"Using test user ID: {test_user_id}")
    prompt_service = PromptService(user_id=test_user_id)

    # Get all available prompts
    available_prompts = await prompt_service.get_available_prompts()
    logger.info(f"Available prompts: {available_prompts}")

    # Process and save each prompt
    prompts_to_test = ["system", "resume", "cover_letter", "folder_name"]

    for prompt_name in prompts_to_test:
        if prompt_name in available_prompts:
            logger.info(f"Processing '{prompt_name}' prompt...")

            # Get the original prompt text
            original_prompt = await prompt_service.get_prompt_text(prompt_name)

            # Save original prompt
            original_file = output_dir / f"{prompt_name}_original.txt"
            with open(original_file, "w", encoding="utf-8") as f:
                f.write(original_prompt)

            # Get formatted prompt
            try:
                formatted_prompt = await prompt_service.get_prompt(prompt_name)

                # Save formatted prompt
                formatted_file = output_dir / f"{prompt_name}_formatted.txt"
                with open(formatted_file, "w", encoding="utf-8") as f:
                    f.write(formatted_prompt)

                logger.info(f"Successfully formatted and saved '{prompt_name}' prompt")

                # Extract and save preferences used for this prompt
                variables = await prompt_service._get_prompt_variables()
                variables_file = output_dir / f"{prompt_name}_variables.json"
                with open(variables_file, "w", encoding="utf-8") as f:
                    json.dump(variables, f, default=str, indent=2)

            except Exception as e:
                logger.error(f"Error formatting '{prompt_name}' prompt: {e}")
                error_file = output_dir / f"{prompt_name}_error.txt"
                with open(error_file, "w", encoding="utf-8") as f:
                    f.write(f"Error: {str(e)}")

    # Check for template variable substitution
    if "resume" in available_prompts:
        formatted_resume = await prompt_service.get_prompt("resume")

        # Check a few key substitutions
        sample_lines = []
        for line in formatted_resume.split("\n"):
            if any(
                x in line.lower() for x in ["categories", "words", "bullet", "entries"]
            ):
                if any(
                    x in line.lower()
                    for x in [
                        "career_summary",
                        "skills",
                        "work_experience",
                        "education",
                        "projects",
                    ]
                ):
                    sample_lines.append(line)

        # Save sample substitutions to a separate file for review
        substitution_file = output_dir / "sample_substitutions.txt"
        with open(substitution_file, "w", encoding="utf-8") as f:
            f.write("Sample of template variable substitutions:\n\n")
            f.write("\n".join(sample_lines))

    # Create a README file in the output folder
    readme_file = output_dir / "README.txt"
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(f"Prompt Service Test Results - {timestamp}\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Test User ID: {test_user_id}\n")
        f.write(f"Tested prompts: {', '.join(prompts_to_test)}\n\n")
        f.write("Files:\n")
        for prompt_name in prompts_to_test:
            f.write(f"- {prompt_name}_original.txt: The original prompt template\n")
            f.write(
                f"- {prompt_name}_formatted.txt: The prompt after variable substitution\n"
            )
            f.write(
                f"- {prompt_name}_variables.json: Variables used for substitution\n"
            )
        f.write("\n- sample_substitutions.txt: Examples of substituted variables\n")

    logger.info(f"Testing completed. Output saved to: {output_dir}")
    logger.info(f"README created at: {readme_file}")

    return output_dir


if __name__ == "__main__":
    output_path = asyncio.run(test_prompt_service())
    print(f"\nPrompt Service testing completed!")
    print(f"Output saved to: {output_path}")
