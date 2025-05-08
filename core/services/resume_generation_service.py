"""Service for resume generation using LLM."""

import copy
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId
from bson import json_util
from pydantic import BaseModel

from config.logging_config import get_logger
from core.exceptions.base import NotFoundException
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.schemas.resume_schemas import ResumeOutputSchema
from core.services.latex_service import LatexService, get_latex_service
from core.services.llm_service import LLMService
from core.services.portfolio_service import PortfolioService
from core.services.profile_service import ProfileService
from core.services.prompt_service import PromptService
from core.utils.json_helper import convert_to_serializable
from core.utils.schema_mapping import map_resume_output_to_models

logger = get_logger(__name__)


class ResumeGenerationService:
    """Service for generating resume content using LLM and creating LaTeX documents."""

    def __init__(
        self,
        resume_repository: ResumeRepository,
        portfolio_repository: PortfolioRepository,
        profile_repository: ProfileRepository,
        prompt_service: PromptService,
        profile_service: ProfileService,
        portfolio_service: PortfolioService,
        llm_service: LLMService,
        latex_service: LatexService,
    ):
        """
        Initialize the resume generation service.

        Args:
            resume_repository: Repository for accessing resume data
            portfolio_repository: Repository for accessing portfolio data
            profile_repository: Repository for accessing profile data
            prompt_service: Service for loading and formatting prompts
            profile_service: Service for profile operations
            portfolio_service: Service for portfolio operations
            llm_service: Service for LLM operations
            latex_service: Service for LaTeX document generation
        """
        self.resume_repository = resume_repository
        self.portfolio_repository = portfolio_repository
        self.profile_repository = profile_repository
        self.prompt_service = prompt_service
        self.profile_service = profile_service
        self.portfolio_service = portfolio_service
        self.llm_service = llm_service
        self.latex_service = latex_service

        self.logger = get_logger(self.__class__.__name__)

    def _generate_proper_title(self, company_name: str, job_title: str) -> str:
        """
        Generate a properly formatted title from company_name and job_title.

        Args:
            company_name: Company name with lowercase and underscores
            job_title: Job title with lowercase and underscores

        Returns:
            Properly formatted title
        """
        if not company_name and not job_title:
            return "My Resume"

        # Convert underscores to spaces and capitalize words
        formatted_company = (
            " ".join(word.capitalize() for word in company_name.split("_"))
            if company_name
            else ""
        )
        formatted_job = (
            " ".join(word.capitalize() for word in job_title.split("_"))
            if job_title
            else ""
        )

        # Combine them with a space if both exist
        if formatted_company and formatted_job:
            return f"{formatted_company} {formatted_job}"
        elif formatted_company:
            return formatted_company
        else:
            return formatted_job

    async def configure_for_user(self, user_id: PydanticObjectId) -> None:
        """
        Configure the service for a specific user.

        Args:
            user_id: User ID to configure for
        """
        await self.llm_service.configure_for_user(user_id)
        self.logger.debug(f"Resume generation service configured for user {user_id}")

    async def get_resume_data(
        self, resume_id: PydanticObjectId
    ) -> Tuple[Resume, Profile, Portfolio]:
        """
        Get the resume, profile, and portfolio data for a resume.

        Args:
            resume_id: Resume ID

        Returns:
            Tuple of Resume, Profile, and Portfolio

        Raises:
            ValueError: If any required data is missing
        """
        # Get resume
        resume = await self.resume_repository.get_by_id(resume_id)
        if not resume:
            raise ValueError(f"Resume with ID {resume_id} not found")

        # Get profile
        profile = await self.profile_repository.get_by_id(resume.profile_id)
        if not profile:
            raise ValueError(f"Profile with ID {resume.profile_id} not found")

        # Get portfolio using portfolio service
        try:
            portfolio = await self.portfolio_service.get_portfolio_by_id(
                resume.portfolio_id
            )
            self.logger.debug(f"Retrieved portfolio with ID: {resume.portfolio_id}")
        except Exception as e:
            self.logger.error(f"Error retrieving portfolio: {e}")
            raise ValueError(
                f"Portfolio with ID {resume.portfolio_id} not found or could not be retrieved"
            )

        return resume, profile, portfolio

    async def generate_latex(
        self,
        resume: Resume,  # Accept Resume object
        profile: Profile,  # Accept Profile object
    ) -> str:
        """
        Generate LaTeX for a resume using the provided data.

        Args:
            resume: The Resume object
            profile: The Profile object associated with the resume

        Returns:
            str: LaTeX content

        Raises:
            ValueError: If LaTeX generation fails or content is missing.
        """
        # Ensure content exists
        if not resume.content:
            # If content is missing, we need the resume_id to generate it.
            # This indicates a potential issue in the calling logic - content should
            # ideally be generated *before* calling generate_latex/compile_pdf.
            # However, for now, we fetch the ID and generate.
            if not resume.id:
                # This case should not happen if resume object is passed correctly
                raise ValueError("Resume object missing ID and content is empty.")
            self.logger.warning(
                f"Resume content missing for {resume.id}, generating it now."
            )
            await self.generate_resume_textual_content(resume.id)
            # We need to update the resume object in memory after generation
            updated_resume = await self.resume_repository.get_by_id(resume.id)
            if not updated_resume:
                raise ValueError(
                    f"Failed to fetch updated resume {resume.id} after content generation."
                )
            resume = updated_resume  # Use the updated resume object

        # Generate LaTeX for resume using LaTeX service, passing objects directly
        try:
            resume_latex = await self.latex_service.generate_resume_latex(
                resume=resume, profile=profile  # Pass objects
            )
            return resume_latex
        except Exception as e:
            self.logger.error(
                f"Error generating LaTeX via LatexService for resume {resume.id}: {e}"
            )
            # Re-raise as ValueError to be consistent with previous behavior
            raise ValueError(f"Failed to generate LaTeX: {str(e)}")

    async def compile_pdf(
        self,
        resume: Resume,  # Accept Resume object
        profile: Profile,  # Accept Profile object
    ) -> bytes:
        """
        Compile LaTeX to PDF for a resume using provided data.

        Args:
            resume: The Resume object
            profile: The Profile object

        Returns:
            bytes: PDF content

        Raises:
            ValueError: If compilation fails.
        """
        # Note: We assume content generation happened *before* calling this method
        # if necessary. The generate_latex call might handle it, but it's cleaner
        # if the caller ensures content exists.
        if not resume.content:
            self.logger.warning(
                f"compile_pdf called for resume {resume.id} with empty content. Generation might fail or be triggered by generate_latex."
            )

        # Generate and compile resume
        try:
            # Generate resume LaTeX using the objects
            resume_latex = await self.generate_latex(resume, profile)

            # Compile to PDF
            pdf_bytes = await self.latex_service.compile_latex_to_pdf(
                resume_latex,
                is_cover_letter=False,
                company_name=resume.company_name,
                job_title=resume.job_title,
            )

            # Verify PDF was generated successfully
            if not pdf_bytes or len(pdf_bytes) == 0:
                self.logger.error(
                    f"PDF compilation returned empty bytes for resume {resume.id}"
                )
                raise ValueError("PDF compilation failed - empty result")

            # Log success
            self.logger.info(
                f"Successfully compiled PDF for resume {resume.id}, size: {len(pdf_bytes)} bytes"
            )

            # Return the PDF bytes directly
            return pdf_bytes

        except (
            ValueError
        ) as ve:  # Catch specific ValueErrors from generate_latex or latex_service
            self.logger.error(
                f"ValueError during PDF compilation for {resume.id}: {ve}"
            )
            raise  # Re-raise the specific error
        except Exception as e:
            self.logger.error(f"Error compiling PDF for {resume.id}: {e}")
            # Wrap other exceptions in a ValueError for consistency upstream
            raise ValueError(f"Failed to compile PDF: {str(e)}")

    async def generate_resume_textual_content(
        self,
        resume_id: PydanticObjectId,
    ) -> Dict[str, Any]:
        """
        Generate complete resume textual content using a structured LLM call.

        Args:
            resume_id: Resume ID

        Returns:
            Generated resume content as a dictionary (as stored in the Resume model)

        Raises:
            ValueError: If resume, profile, job_description, or prompt is missing or generation fails.
        """
        # Get resume data (includes resume, profile)
        resume, profile, _ = await self.get_resume_data(resume_id)

        # Check job description
        if not resume.job_description:
            self.logger.error(f"Job description missing for resume_id: {resume_id}")
            raise ValueError("Job description is required for resume generation")

        # Make sure the LLM service is configured for the current user
        await self.llm_service.configure_for_user(resume.user_id)

        # Ensure prompt service is configured for the user
        self.prompt_service.set_user_id(resume.user_id)

        # Prepare portfolio data for the prompt
        portfolio_data_dict = await self._prepare_portfolio_data(resume.user_id)
        if not portfolio_data_dict:
            self.logger.warning(f"No portfolio data found for user {resume.user_id}")
            # Continue, but generation quality might be affected

        try:
            # --- 1. Prepare Prompt ---
            self.logger.info("Preparing prompt for structured resume generation.")
            system_prompt = await self.prompt_service.get_system_prompt()
            base_variables = await self.prompt_service._get_prompt_variables()

            # Sanitize portfolio data before adding to variables
            clean_portfolio_data = convert_to_serializable(portfolio_data_dict)

            variables = {
                **base_variables,
                "job_description": resume.job_description,
                "portfolio_data": clean_portfolio_data,
            }

            # Format the main resume prompt
            resume_prompt_text = await self.prompt_service.format_prompt(
                "resume", variables
            )
            if not resume_prompt_text:
                self.logger.error("Failed to format resume prompt.")
                raise ValueError("Could not format the resume prompt.")

            # --- 2. Call LLM for Structured Output ---
            self.logger.info(
                f"Calling LLM service for structured resume content for resume_id: {resume_id}"
            )
            tags = ["operation:generate_resume", f"resume_id:{str(resume_id)}"]

            # Call the generic structured completion method
            resume_output: ResumeOutputSchema = (
                await self.llm_service.get_structured_completion(
                    prompt=resume_prompt_text,
                    schema_model=ResumeOutputSchema,
                    system_prompt=system_prompt,
                    user_id=str(resume.user_id),
                    tags=tags,
                    fallback_to_text=False,  # Ensure we get the Pydantic model or an error
                )
            )
            self.logger.info(
                f"Successfully received structured resume content from LLM for resume_id: {resume_id}"
            )

            # --- 3. Post-process and Update Resume ---
            # Add years_of_experience from portfolio to the generated summary
            # (The schema mapping logic expects it later if converting back to model)
            if resume_output.career_summary:
                portfolio = await self.portfolio_repository.get_by_user_id(
                    resume.user_id
                )
                if (
                    portfolio
                    and portfolio.career_summary
                    and portfolio.career_summary.years_of_experience
                ):
                    # We don't add years_of_experience to the schema itself as per the prompt instructions
                    # This value is primarily used during LaTeX generation or if mapping back to models
                    self.logger.info(
                        f"Years of experience from portfolio: {portfolio.career_summary.years_of_experience}"
                    )
                else:
                    self.logger.warning(
                        f"Years_of_experience not found in portfolio for user {resume.user_id}"
                    )

            # Convert the Pydantic model back to a dictionary for storage in resume.content
            # This assumes resume.content stores a dictionary, not the Pydantic model itself.
            generated_content_dict = resume_output.model_dump(
                mode="json"
            )  # Use mode='json' for BSON compatibility

            # --- 4. Save Content ---
            if not resume.content or not isinstance(resume.content, dict):
                resume.content = {}
            resume.content.update(generated_content_dict)
            resume.updated_at = datetime.now(timezone.utc)

            # Save updated resume
            await self.resume_repository.update(resume.id, resume)
            self.logger.info(f"Saved resume {resume.id} with generated content")

            # --- 5. Debug Output (Optional) ---
            from pathlib import Path

            debug_dir = Path("debug/output")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = f"{timestamp}_{resume.id}"
            test_output_dir = debug_dir / folder_name
            test_output_dir.mkdir(parents=True, exist_ok=True)

            # Save the generated content dict
            with open(
                test_output_dir / "generated_content.json", "w", encoding="utf-8"
            ) as f:
                json.dump(
                    generated_content_dict, f, indent=2, default=str
                )  # Use default=str for potential complex types

            # Return the content dictionary as stored in the resume
            return resume.content

        except Exception as e:
            self.logger.error(
                f"Error in generate_resume_textual_content for resume_id {resume_id}: {e}"
            )
            # Log the type of exception
            self.logger.exception("Detailed traceback:")
            raise ValueError(f"Failed to generate resume content: {str(e)}")

    async def _prepare_portfolio_data(
        self, user_id: PydanticObjectId
    ) -> Dict[str, Any]:
        """
        Prepare portfolio data suitable for the resume generation prompt.

        Fetches relevant sections from the user's profile and portfolio.

        Args:
            user_id: User ID

        Returns:
            Dictionary with portfolio data structured for the prompt.
        """
        result = {}
        portfolio = None  # Initialize portfolio

        # Get personal information from Profile
        try:
            profile = await self.profile_repository.get_by_user_id(user_id)
            if profile and profile.personal_information:
                # Use model_dump to get a dictionary representation
                result["personal_information"] = (
                    profile.personal_information.model_dump()
                )
            else:
                self.logger.warning(
                    f"Personal information not found for user {user_id}"
                )
        except Exception as e:
            self.logger.error(
                f"Error getting personal information for user {user_id}: {e}"
            )

        # Get portfolio data
        try:
            portfolio = await self.portfolio_repository.get_by_user_id(user_id)
        except Exception as e:
            self.logger.error(f"Error fetching portfolio for user {user_id}: {e}")
            # Return whatever we have so far (potentially just personal info)
            return result

        if not portfolio:
            self.logger.warning(f"Portfolio not found for user {user_id}")
            return result

        # Map portfolio fields to dictionary using model_dump for serialization consistency
        portfolio_fields = [
            "career_summary",
            "skills",
            "work_experience",
            "education",
            "projects",
            "awards",
            "publications",
            "certifications",
            "custom_sections",
        ]
        for field in portfolio_fields:
            if hasattr(portfolio, field):
                data = getattr(portfolio, field)
                if data:  # Only include non-empty sections
                    try:
                        # Use model_dump if it's a Pydantic model or list of models
                        if isinstance(data, BaseModel):
                            result[field] = data.model_dump()
                        elif (
                            isinstance(data, list)
                            and data
                            and isinstance(data[0], BaseModel)
                        ):
                            result[field] = [item.model_dump() for item in data]
                        else:
                            # Otherwise, assume it's already serializable (like dict or basic list)
                            result[field] = data
                    except Exception as dump_error:
                        self.logger.warning(
                            f"Could not dump field {field}: {dump_error}. Storing raw."
                        )
                        result[field] = data  # Store raw data on error

        # Handle enabled custom sections specifically if custom_sections wasn't directly mapped
        if (
            portfolio.custom_sections
            and portfolio.custom_sections.enabled
            and "custom_sections" not in result
        ):
            enabled_sections_data = {}
            for section_name in portfolio.custom_sections.enabled:
                if hasattr(portfolio, section_name):
                    data = getattr(portfolio, section_name)
                    if data:
                        try:
                            if isinstance(data, BaseModel):
                                enabled_sections_data[section_name] = data.model_dump()
                            elif (
                                isinstance(data, list)
                                and data
                                and isinstance(data[0], BaseModel)
                            ):
                                enabled_sections_data[section_name] = [
                                    item.model_dump() for item in data
                                ]
                            else:
                                enabled_sections_data[section_name] = data
                        except Exception as dump_error:
                            self.logger.warning(
                                f"Could not dump custom section {section_name}: {dump_error}. Storing raw."
                            )
                            enabled_sections_data[section_name] = data
            if enabled_sections_data:
                result["custom_sections"] = (
                    enabled_sections_data  # Store under a 'custom_sections' key
                )

        # Final serialization check/cleanup might be needed depending on how models are structured
        # Using convert_to_serializable one last time before sending to LLMService might be safest
        # This is done within generate_resume_textual_content before formatting the prompt

        return result
