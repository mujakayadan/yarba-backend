"""Base prompt template."""

from typing import Dict, Optional


class BasePrompt:
    """Base class for all prompts."""

    def __init__(self, template: str):
        """Initialize the prompt template.

        Args:
            template: The prompt template string
        """
        self._template = template.strip()

    def format(self, **kwargs: Dict[str, str]) -> str:
        """Format the prompt template with the given arguments.

        Args:
            **kwargs: Keyword arguments to format the template with

        Returns:
            The formatted prompt string
        """
        return self._template.format(**kwargs)

    def __str__(self) -> str:
        """Return the prompt template as a string."""
        return self._template

    def __repr__(self) -> str:
        """Return a string representation of the prompt."""
        return f"{self.__class__.__name__}({self._template})"
