"""Model selector component."""

import streamlit as st

from config.logging_config import get_logger
from config.settings import Settings

logger = get_logger(__name__)
settings = Settings()


class ModelSelector:
    """Component for selecting AI models and their parameters."""

    def __init__(self):
        """Initialize the model selector with available model options."""
        logger.debug("Initializing ModelSelector")
        self.model_types = ["OpenAI", "Claude", "Ollama", "Gemini"]
        self.model_options = {
            "OpenAI": [
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4o-2024-08-06",
                "o1-mini",
                "gpt-4o-2024-05-13",
            ],
            "Claude": [
                "claude-3-5-sonnet-latest",
                "claude-3-opus-latest",
                "claude-3-5-sonnet-20241022",
                "claude-3-5-sonnet-20240620",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
            ],
            "Ollama": [
                "llama3.1",
                "llama2",
                "llama2-uncensored",
                "mistral",
                "mixtral",
                "codellama",
                "neural-chat",
            ],
            "Gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.5-pro-exp-0801"],
        }

    def render(
        self, current_model_type: str = None, current_model_name: str = None
    ) -> tuple:
        """
        Render the model selector component.

        Args:
            current_model_type: Currently selected model type
            current_model_name: Currently selected model name

        Returns:
            tuple: Selected model type and name
        """
        # Default values if not provided
        if not current_model_type:
            current_model_type = "Claude"
        if not current_model_name:
            current_model_name = "claude-3-5-sonnet-20240620"

        # Ensure current_model_type is valid
        if current_model_type not in self.model_types:
            current_model_type = "Claude"

        # Model type selection
        model_type = st.selectbox(
            "Model Type",
            self.model_types,
            index=self.model_types.index(current_model_type),
        )

        # Ensure current_model_name is valid for the selected model type
        if current_model_name not in self.model_options[model_type]:
            current_model_name = self.model_options[model_type][0]

        # Model name selection
        model_name = st.selectbox(
            "Model Name",
            self.model_options[model_type],
            index=(
                self.model_options[model_type].index(current_model_name)
                if current_model_name in self.model_options[model_type]
                else 0
            ),
        )

        return model_type, model_name
