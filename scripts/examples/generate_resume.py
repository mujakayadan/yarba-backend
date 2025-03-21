"""Example script demonstrating resume and cover letter generation."""

import asyncio
import sys
from pathlib import Path

# Make sure we can import from the project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.logging_config import get_logger
from core.models.resume import Resume
from core.repositories.portfolio import PortfolioRepository
from core.repositories.profile import ProfileRepository
from core.repositories.resume import ResumeRepository
from core.repositories.tex_template import TexHeaderRepository, TexTemplateRepository
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService
from core.services.resume_generation_service import ResumeGenerationService
from core.services.tex_service import TexService

# Set up logger
logger = get_logger(__name__)


async def generate_resume(user_id: str, resume_id: str):
    """Generate a resume and cover letter for a user.

    Args:
        user_id: The ID of the user to generate the resume for.
        resume_id: The ID of the resume to generate.

    Returns:
        tuple: A tuple containing the resume LaTeX and cover letter LaTeX.
    """
    # Initialize repositories
    portfolio_repository = PortfolioRepository()
    profile_repository = ProfileRepository()
    resume_repository = ResumeRepository()
    tex_template_repository = TexTemplateRepository()
    tex_header_repository = TexHeaderRepository()

    # Initialize services
    prompt_service = PromptService()
    llm_service = LLMService(
        profile_repository=profile_repository, prompt_service=prompt_service
    )
    tex_service = TexService(
        tex_template_repository=tex_template_repository,
        tex_header_repository=tex_header_repository,
    )

    # Initialize resume generation service
    resume_service = ResumeGenerationService(
        resume_repository=resume_repository,
        portfolio_repository=portfolio_repository,
        profile_repository=profile_repository,
        llm_service=llm_service,
        tex_service=tex_service,
    )

    # Configure services for the user
    await prompt_service.set_user_id(user_id)
    await llm_service.configure_for_user(user_id)
    await resume_service.configure_for_user(user_id)

    # Generate resume content
    logger.info(f"Generating resume content for resume {resume_id}")
    resume_content = await resume_service.generate_resume_content(resume_id)

    # Generate resume LaTeX
    logger.info("Generating resume LaTeX")
    resume_latex = await resume_service.generate_latex(
        resume_id=resume_id, content=resume_content, is_cover_letter=False
    )

    # Generate cover letter
    logger.info("Generating cover letter")
    cover_letter = await resume_service.generate_cover_letter(
        resume_id=resume_id, resume_content=resume_content
    )

    # Generate cover letter LaTeX
    logger.info("Generating cover letter LaTeX")
    cover_letter_latex = await resume_service.generate_latex(
        resume_id=resume_id, content=cover_letter, is_cover_letter=True
    )

    return resume_latex, cover_letter_latex


async def save_output(resume_latex: str, cover_letter_latex: str, output_dir: str):
    """Save the generated LaTeX files.

    Args:
        resume_latex: The LaTeX content for the resume.
        cover_letter_latex: The LaTeX content for the cover letter.
        output_dir: The directory to save the files to.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save resume
    with open(output_path / "resume.tex", "w") as f:
        f.write(resume_latex)

    # Save cover letter
    with open(output_path / "cover_letter.tex", "w") as f:
        f.write(cover_letter_latex)

    logger.info(f"Output saved to {output_path}")


async def main():
    """Run the example script."""
    # Configuration
    user_id = "your_user_id"  # Replace with actual user ID
    resume_id = "your_resume_id"  # Replace with actual resume ID
    output_dir = "my_data/output"

    try:
        # Generate resume and cover letter
        resume_latex, cover_letter_latex = await generate_resume(user_id, resume_id)

        # Save output
        await save_output(resume_latex, cover_letter_latex, output_dir)

        logger.info("Resume generation completed successfully")
    except Exception as e:
        logger.error(f"Error generating resume: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
