"""Base generator class for all generators."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from config.logging_config import get_logger
from config.settings import Settings
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume

logger = get_logger(__name__)


class BaseGenerator(ABC):
    """Base class for all generators."""

    def __init__(
        self,
        profile: Optional[Profile] = None,
        portfolio: Optional[Portfolio] = None,
        resume: Optional[Resume] = None,
        settings: Optional[Settings] = None,
    ):
        """Initialize the generator.

        Args:
            profile: User profile
            portfolio: User portfolio
            resume: Resume to generate
            settings: Application settings
        """
        self.profile = profile
        self.portfolio = portfolio
        self.resume = resume
        self.settings = settings or Settings()
        self.logger = logger

    @abstractmethod
    async def generate(self, **kwargs) -> Dict[str, Any]:
        """Generate content.

        Args:
            **kwargs: Additional arguments for generation

        Returns:
            Dict[str, Any]: Generated content
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
