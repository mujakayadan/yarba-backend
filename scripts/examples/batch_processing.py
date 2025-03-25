"""Example script demonstrating batch processing of multiple resumes."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Make sure we can import from the project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.logging_config import get_logger
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.repositories.tex_header_repository import TexHeaderRepository
from core.repositories.tex_template_repository import TexTemplateRepository
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService
from core.services.resume_generation_service import ResumeGenerationService
from core.services.tex_service import TexService

# Set up logger
logger = get_logger(__name__)


class BatchProcessor:
    """Batch processor for generating multiple resumes."""

    def __init__(self):
        """Initialize the batch processor."""
        # Initialize repositories
        self.portfolio_repository = PortfolioRepository()
        self.profile_repository = ProfileRepository()
        self.resume_repository = ResumeRepository()
        self.tex_template_repository = TexTemplateRepository()
        self.tex_header_repository = TexHeaderRepository()

        # Initialize services
        self.prompt_service = PromptService()
        self.llm_service = LLMService(
            profile_repository=self.profile_repository,
            prompt_service=self.prompt_service,
        )
        self.tex_service = TexService(
            tex_template_repository=self.tex_template_repository,
            tex_header_repository=self.tex_header_repository,
        )

        # Initialize resume generation service
        self.resume_service = ResumeGenerationService(
            resume_repository=self.resume_repository,
            portfolio_repository=self.portfolio_repository,
            profile_repository=self.profile_repository,
            llm_service=self.llm_service,
            tex_service=self.tex_service,
        )

    async def process_user_resumes(self, user_id: str) -> Dict[str, Dict]:
        """Process all resumes for a specific user.

        Args:
            user_id: The ID of the user to process resumes for.

        Returns:
            Dict[str, Dict]: A dictionary mapping resume IDs to their processed data.
        """
        logger.info(f"Processing resumes for user {user_id}")

        # Configure services for the user
        await self.prompt_service.set_user_id(user_id)
        await self.llm_service.configure_for_user(user_id)
        await self.resume_service.configure_for_user(user_id)

        # Get all resumes for the user
        resumes = await self.resume_repository.get_by_user_id(user_id)

        if not resumes:
            logger.warning(f"No resumes found for user {user_id}")
            return {}

        logger.info(f"Found {len(resumes)} resumes for user {user_id}")

        # Process each resume in parallel
        tasks = [self.process_resume(resume.id) for resume in resumes]
        results = await asyncio.gather(*tasks)

        # Create a dictionary of resume ID to result
        processed_data = {
            str(resume.id): result for resume, result in zip(resumes, results)
        }

        logger.info(
            f"Completed processing {len(processed_data)} resumes for user {user_id}"
        )
        return processed_data

    async def process_resume(self, resume_id: str) -> Dict:
        """Process a single resume.

        Args:
            resume_id: The ID of the resume to process.

        Returns:
            Dict: The processed resume data.
        """
        logger.info(f"Processing resume {resume_id}")

        try:
            # Get resume data
            resume = await self.resume_repository.get_by_id(resume_id)

            if not resume:
                logger.error(f"Resume {resume_id} not found")
                return {"error": "Resume not found"}

            # Generate resume content
            resume_content = await self.resume_service.generate_resume_content(
                resume_id
            )

            # Generate cover letter
            cover_letter = await self.resume_service.generate_cover_letter(
                resume_id=resume_id, resume_content=resume_content
            )

            # Generate LaTeX
            resume_latex = await self.resume_service.generate_latex(
                resume_id=resume_id, content=resume_content, is_cover_letter=False
            )

            cover_letter_latex = await self.resume_service.generate_latex(
                resume_id=resume_id, content=cover_letter, is_cover_letter=True
            )

            # Return processed data
            return {
                "resume": resume.model_dump(),
                "resume_content": resume_content,
                "cover_letter": cover_letter,
                "resume_latex": resume_latex,
                "cover_letter_latex": cover_letter_latex,
            }
        except Exception as e:
            logger.error(f"Error processing resume {resume_id}: {e}")
            return {"error": str(e)}

    async def process_multiple_users(self, user_ids: List[str]) -> Dict[str, Dict]:
        """Process resumes for multiple users.

        Args:
            user_ids: List of user IDs to process.

        Returns:
            Dict[str, Dict]: A dictionary mapping user IDs to their processed resume data.
        """
        # Process each user sequentially to avoid resource contention
        results = {}
        for user_id in user_ids:
            results[user_id] = await self.process_user_resumes(user_id)

        return results

    async def save_results(self, results: Dict[str, Dict], output_dir: str) -> None:
        """Save the processed results to disk.

        Args:
            results: The processed results, organized by user ID and resume ID.
            output_dir: The directory to save the results to.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for user_id, user_data in results.items():
            # Create a directory for the user
            user_dir = output_path / user_id
            user_dir.mkdir(exist_ok=True)

            # Create a summary file with metadata
            with open(user_dir / "summary.json", "w") as f:
                summary = {
                    "user_id": user_id,
                    "resume_count": len(user_data),
                    "resume_ids": list(user_data.keys()),
                }
                json.dump(summary, f, indent=2)

            # Save each resume's data
            for resume_id, resume_data in user_data.items():
                if "error" in resume_data:
                    # Skip resumes with errors
                    logger.warning(
                        f"Skipping resume {resume_id} due to error: {resume_data['error']}"
                    )
                    continue

                # Create a directory for the resume
                resume_dir = user_dir / resume_id
                resume_dir.mkdir(exist_ok=True)

                # Save resume metadata
                with open(resume_dir / "metadata.json", "w") as f:
                    json.dump(resume_data["resume"], f, indent=2)

                # Save resume content
                with open(resume_dir / "content.json", "w") as f:
                    json.dump(resume_data["resume_content"], f, indent=2)

                # Save cover letter
                with open(resume_dir / "cover_letter.txt", "w") as f:
                    f.write(resume_data["cover_letter"])

                # Save LaTeX files
                with open(resume_dir / "resume.tex", "w") as f:
                    f.write(resume_data["resume_latex"])

                with open(resume_dir / "cover_letter.tex", "w") as f:
                    f.write(resume_data["cover_letter_latex"])

        logger.info(f"Results saved to {output_path}")


async def main():
    """Run the batch processing example."""
    # Configuration
    user_ids = [
        "user_1",  # Replace with actual user IDs
        "user_2",
    ]
    output_dir = "my_data/batch_output"

    try:
        # Initialize batch processor
        processor = BatchProcessor()

        # Process all resumes for the specified users
        results = await processor.process_multiple_users(user_ids)

        # Save the results
        await processor.save_results(results, output_dir)

        logger.info("Batch processing completed successfully")
    except Exception as e:
        logger.error(f"Error during batch processing: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
