"""Base UI implementation."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel

from config.logging_config import get_logger
from config.settings import Settings

logger = get_logger(__name__)
settings = Settings()


class UIConfig(BaseModel):
    """Configuration for UI implementations.

    This class holds configuration options for UI implementations,
    including theming, layout, and behavior settings.
    """

    title: str = settings.ui.title
    description: str = settings.ui.description
    theme: Dict[str, Any] = settings.ui.theme
    layout: Dict[str, Any] = settings.ui.layout
    debug_mode: bool = settings.debug


class BaseUI(ABC):
    """Abstract base class for UI implementations.

    This class provides the base functionality for different UI
    implementations (Streamlit, FastAPI, etc.). It handles configuration,
    routing, and shared UI logic.
    """

    def __init__(self, config: Optional[UIConfig] = None):
        """Initialize the UI.

        Args:
            config: Optional UI configuration
        """
        self.config = config or UIConfig()

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the UI application.

        This method should handle any necessary setup before
        starting the UI application.
        """
        pass

    @abstractmethod
    async def render_page(self, page_name: str, **kwargs) -> None:
        """Render a specific page.

        Args:
            page_name: Name of the page to render
            **kwargs: Additional page-specific parameters
        """
        pass

    @abstractmethod
    async def handle_input(self, input_type: str, data: Any) -> None:
        """Handle user input.

        Args:
            input_type: Type of input to handle
            data: Input data
        """
        pass

    @abstractmethod
    async def display_output(self, output_type: str, data: Any) -> None:
        """Display output to the user.

        Args:
            output_type: Type of output to display
            data: Output data
        """
        pass

    @abstractmethod
    async def handle_error(self, error: Exception) -> None:
        """Handle and display errors.

        Args:
            error: The error to handle
        """
        pass

    async def _setup_theme(self) -> None:
        """Set up UI theming.

        This method should be called during initialization to
        apply the configured theme.
        """
        pass

    async def _setup_layout(self) -> None:
        """Set up UI layout.

        This method should be called during initialization to
        apply the configured layout.
        """
        pass
