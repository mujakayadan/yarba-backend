"""Model selector component."""

import streamlit as st

from config.logging_config import get_logger
from config.settings import Settings
from core.database.factory import get_unit_of_work

logger = get_logger(__name__)
settings = Settings()


class ModelSelector:
    def __init__(self):
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
        # Load saved preferences
        self._load_saved_preferences()

    def _load_saved_preferences(self):
        """Load saved preferences from database"""
        try:
            # Default values from settings
            st.session_state["model_type"] = "Claude"
            st.session_state["model_name"] = settings.llm.default_model
            st.session_state["temperature"] = settings.llm.temperature
            logger.debug("Using default model preferences")
        except Exception as e:
            logger.error(f"Error loading model preferences: {e}")

    def get_model_settings(self):
        """Get model settings, preferring saved preferences"""
        # Use saved preferences if available
        if "model_type" in st.session_state:
            model_type = st.session_state["model_type"]
            model_name = st.session_state["model_name"]
            temperature = st.session_state["temperature"]
        else:
            # Default values from settings
            model_type = "Claude"
            model_name = settings.llm.default_model
            temperature = settings.llm.temperature

        return model_type, model_name, temperature

    def set_model_settings(self, model_type: str, model_name: str, temperature: float):
        """Set model settings in session state.

        Args:
            model_type: The type of model (e.g., "Claude", "OpenAI")
            model_name: The specific model name
            temperature: The temperature setting for the model
        """
        st.session_state["model_type"] = model_type
        st.session_state["model_name"] = model_name
        st.session_state["temperature"] = temperature
        logger.debug(f"Set model settings: {model_type}, {model_name}, {temperature}")
