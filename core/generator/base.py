"""Base generator class for document generation."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from config.logging_config import get_logger
from config.settings import Settings
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.preamble_repository import PreambleRepository
from core.repositories.tex_header_repository import TexHeaderRepository
from core.repositories.tex_template_repository import TexTemplateRepository
from core.services.llm_service import LLMService

logger = get_logger(__name__)


class BaseGenerator(ABC):
    """Base abstract class for document generators.

    This class provides common functionality for document generators,
    including access to user data, repositories, and services.
    """

    def __init__(
        self,
        profile: Profile,
        resume: Resume,
        portfolio: Optional[Portfolio] = None,
        llm_service: Optional[LLMService] = None,
        preamble_repository: Optional[PreambleRepository] = None,
        tex_header_repository: Optional[TexHeaderRepository] = None,
        tex_template_repository: Optional[TexTemplateRepository] = None,
    ):
        """Initialize the base generator.

        Args:
            profile: User profile
            resume: Resume to generate content for
            portfolio: Optional portfolio data
            llm_service: LLM service for content generation
            preamble_repository: Repository for LaTeX preambles
            tex_header_repository: Repository for LaTeX headers
            tex_template_repository: Repository for LaTeX templates
        """
        self.profile = profile
        self.resume = resume
        self.portfolio = portfolio
        self.llm_service = llm_service
        self.preamble_repository = preamble_repository
        self.tex_header_repository = tex_header_repository
        self.tex_template_repository = tex_template_repository
        self.logger = logger

    @abstractmethod
    async def generate(self, **kwargs) -> Dict[str, Any]:
        """Generate document content.

        This abstract method must be implemented by subclasses to
        generate the specific document content.

        Args:
            **kwargs: Additional arguments for generation

        Returns:
            Dict[str, Any]: Generated document content
        """
        pass

    async def preprocess(self, **kwargs) -> Dict[str, Any]:
        """Preprocess data before generation.

        Args:
            **kwargs: Additional arguments for preprocessing

        Returns:
            Dict[str, Any]: Preprocessed data
        """
        return kwargs

    async def postprocess(self, content: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Postprocess generated content.

        Args:
            content: Generated content
            **kwargs: Additional arguments for postprocessing

        Returns:
            Dict[str, Any]: Postprocessed content
        """
        return content

    def get_model_settings(self) -> Dict[str, Any]:
        """Get LLM model settings.

        Returns:
            Dict[str, Any]: Model settings
        """
        if self.resume and self.resume.llm_settings:
            # Use resume-specific settings if available
            model_settings = {
                "model_type": self.resume.llm_settings.model_type
                or self.settings.llm.default_model.split("-")[0],
                "model_name": self.resume.llm_settings.model_name
                or self.settings.llm.default_model,
                "temperature": self.resume.llm_settings.temperature
                or self.settings.llm.temperature,
                "max_tokens": self.resume.llm_settings.max_tokens
                or self.settings.llm.max_tokens,
            }
        elif (
            self.profile
            and self.profile.preferences
            and self.profile.preferences.llm_preferences
        ):
            # Use profile preferences if available
            llm_prefs = self.profile.preferences.llm_preferences
            model_settings = {
                "model_type": llm_prefs.get(
                    "model_type", self.settings.llm.default_model.split("-")[0]
                ),
                "model_name": llm_prefs.get(
                    "model_name", self.settings.llm.default_model
                ),
                "temperature": llm_prefs.get(
                    "temperature", self.settings.llm.temperature
                ),
                "max_tokens": self.settings.llm.max_tokens,
            }
        else:
            # Use default settings
            model_settings = {
                "model_type": self.settings.llm.default_model.split("-")[0],
                "model_name": self.settings.llm.default_model,
                "temperature": self.settings.llm.temperature,
                "max_tokens": self.settings.llm.max_tokens,
            }

        return model_settings

    async def _get_section_processing_preference(self, section_name: str) -> str:
        """Get processing preference for a section.

        Args:
            section_name: Name of the section

        Returns:
            str: Processing preference ('Process' or 'Hardcode')
        """
        # Default to processing
        section_preference = "Process"

        # Check profile preferences if available
        if (
            self.profile
            and self.profile.preferences
            and self.profile.preferences.section_preferences
        ):
            section_preference = self.profile.preferences.section_preferences.get(
                section_name, "Process"
            )

        return section_preference

    async def _get_preamble(self, preamble_name: str) -> Optional[str]:
        """Get a LaTeX preamble.

        Args:
            preamble_name: Name of the preamble to retrieve

        Returns:
            Optional[str]: Preamble content if found, None otherwise
        """
        if not self.preamble_repository:
            self.logger.warning("Preamble repository not available")
            return None

        try:
            preamble = await self.preamble_repository.get_by_name(preamble_name)
            if preamble:
                return preamble.content
        except Exception as e:
            self.logger.error(f"Error retrieving preamble '{preamble_name}': {e}")

        return None

    async def _get_tex_header(self, header_name: str) -> Optional[str]:
        """Get a LaTeX header.

        Args:
            header_name: Name of the header to retrieve

        Returns:
            Optional[str]: Header content if found, None otherwise
        """
        if not self.tex_header_repository:
            self.logger.warning("TeX header repository not available")
            return None

        try:
            header = await self.tex_header_repository.get_by_name(header_name)
            if header:
                return header.content
        except Exception as e:
            self.logger.error(f"Error retrieving TeX header '{header_name}': {e}")

        return None

    async def _get_tex_template(self, template_name: str) -> Optional[str]:
        """Get a LaTeX template.

        Args:
            template_name: Name of the template to retrieve

        Returns:
            Optional[str]: Template content if found, None otherwise
        """
        if not self.tex_template_repository:
            self.logger.warning("TeX template repository not available")
            return None

        try:
            template = await self.tex_template_repository.get_by_name(template_name)
            if template:
                return template.content
        except Exception as e:
            self.logger.error(f"Error retrieving TeX template '{template_name}': {e}")

        return None
