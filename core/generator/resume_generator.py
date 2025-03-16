"""Resume generator implementation."""

import json
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from core.latex.compilers import ResumeCompiler
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume

from .base import BaseGenerator
from .utils.prompt_builder import build_resume_prompt

logger = get_logger(__name__)


class ResumeGenerator(BaseGenerator):
    """Resume generator implementation."""

    async def generate(self, **kwargs) -> Dict[str, Any]:
        """Generate resume content.

        Args:
            **kwargs: Additional arguments for generation

        Returns:
            Dict[str, Any]: Generated resume content
        """
        if not self.profile or not self.resume:
            raise ValueError("Profile and Resume are required for generation")

        # Preprocess data
        data = await self.preprocess(**kwargs)

        # Get section preferences
        section_preferences = self.profile.preferences.section_preferences

        # Initialize content dictionary
        content = {}

        # Process each section based on preferences
        for section, preference in section_preferences.items():
            if preference == "Process":
                # Generate content using LLM
                section_content = await self._generate_section(section, data)
                content[section] = section_content
            elif preference == "Hardcode":
                # Use hardcoded content from portfolio
                content[section] = await self._get_hardcoded_section(section)

        # Postprocess content
        processed_content = await self.postprocess(content, **kwargs)

        # Update resume content
        self.resume.content = processed_content

        # Generate PDF if requested
        if kwargs.get("generate_pdf", False):
            await self._generate_pdf()

        return processed_content

    async def _generate_section(self, section_name: str, data: Dict[str, Any]) -> Any:
        """Generate content for a specific section using LLM.

        Args:
            section_name: Name of the section
            data: Data for generation

        Returns:
            Any: Generated section content
        """
        # Get model settings
        model_settings = self.get_model_settings()

        # Build prompt for the section
        prompt = build_resume_prompt(
            section_name=section_name,
            profile=self.profile,
            portfolio=self.portfolio,
            resume=self.resume,
            job_description=self.resume.job_description,
            job_title=self.resume.job_title,
            company_name=self.resume.company_name,
        )

        # TODO: Implement LLM client call
        # For now, return placeholder content
        self.logger.info(f"Generating content for section: {section_name}")

        # Placeholder implementation
        if section_name == "personal_information":
            return {
                "full_name": self.profile.full_name,
                "email": self.profile.email,
                "phone": self.profile.phone,
                "address": self.profile.address,
                "linkedin": self.profile.linkedin,
                "github": self.profile.github,
                "website": self.profile.website,
            }
        elif section_name == "career_summary":
            return "Experienced professional with a track record of success."
        elif section_name == "skills":
            return {"Technical Skills": ["Python", "JavaScript", "MongoDB"]}
        elif section_name == "work_experience":
            return []
        elif section_name == "education":
            return []
        elif section_name == "projects":
            return []

        return None

    async def _get_hardcoded_section(self, section_name: str) -> Any:
        """Get hardcoded content for a section from the portfolio.

        Args:
            section_name: Name of the section

        Returns:
            Any: Hardcoded section content
        """
        if not self.portfolio:
            return None

        if section_name == "personal_information":
            # Get profile from portfolio
            profile = await self.portfolio.get_profile()
            if profile:
                return {
                    "full_name": profile.full_name,
                    "email": profile.email,
                    "phone": profile.phone,
                    "address": profile.address,
                    "linkedin": profile.linkedin,
                    "github": profile.github,
                    "website": profile.website,
                }
        elif section_name == "career_summary":
            return self.portfolio.get_career_summary(self.resume.job_description)
        elif section_name == "skills":
            skill_categories = {}
            for skill_category in self.portfolio.skills:
                for category, skills in skill_category.items():
                    skill_categories[category] = skills
            return skill_categories
        elif section_name == "work_experience":
            return [exp.dict() for exp in self.portfolio.work_experience]
        elif section_name == "education":
            return [edu.dict() for edu in self.portfolio.education]
        elif section_name == "projects":
            return [proj.dict() for proj in self.portfolio.projects]
        elif section_name == "awards":
            return [award.dict() for award in self.portfolio.awards]
        elif section_name == "publications":
            return [pub.dict() for pub in self.portfolio.publications]

        return None

    async def _generate_pdf(self) -> Optional[bytes]:
        """Generate PDF from resume content.

        Returns:
            Optional[bytes]: Generated PDF content
        """
        try:
            compiler = ResumeCompiler()
            pdf_content = await compiler.generate_pdf(self.resume)
            if pdf_content:
                self.resume.resume_pdf = pdf_content
                return pdf_content
        except Exception as e:
            self.logger.error(f"Error generating PDF: {str(e)}")

        return None
