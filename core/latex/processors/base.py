"""Base section processor for LaTeX content generation."""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from config.logging_config import get_logger


class SectionProcessor(ABC):
    """
    Base class for section processors.

    This abstract class defines the interface for processing resume sections
    into LaTeX content. It focuses solely on content generation without
    including preambles or formatting that should come from the database.

    IMPORTANT: Processors should NOT include section environment tags like
    \\resumeSubHeadingListStart and \\resumeSubHeadingListEnd as these are
    already included in the tex_headers templates in the database.
    """

    def __init__(self):
        """Initialize the processor."""
        self.logger = get_logger(self.__class__.__name__)

    def parse_content(self, content: Any) -> Any:
        """
        Parse JSON content safely, handling various input formats.

        Args:
            content: The section content to parse

        Returns:
            Parsed content in a normalized format
        """
        # Handle None case
        if content is None:
            return None

        # If content is already a dict or list, return as is
        if isinstance(content, (dict, list)):
            return content

        # If content is a string, try to parse as JSON
        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If not valid JSON, return as is
                return content

        # If content has a method like model_dump, use it
        if hasattr(content, "model_dump"):
            # Pydantic v2
            return content.model_dump()
        elif hasattr(content, "dict") and callable(getattr(content, "dict")):
            # Pydantic v1 or similar
            return content.dict()

        # Return string representation for other types
        return str(content)

    def convert_nested_arrays_to_dict(self, nested_arrays: List[List]) -> List[Dict]:
        """
        Convert nested arrays with key-value pairs to list of dictionaries.
        This is useful for awards and publications sections which may come in this format.

        Args:
            nested_arrays: A list of lists where each inner list contains key-value pairs

        Returns:
            A list of dictionaries with the key-value pairs properly organized
        """
        result = []
        for item_data in nested_arrays:
            if not isinstance(item_data, list):
                continue

            # Check if it's a list of key-value pairs
            if all(isinstance(pair, list) and len(pair) == 2 for pair in item_data):
                # Convert to dict format
                item_dict = {}
                for key, value in item_data:
                    item_dict[key] = value
                result.append(item_dict)
            elif isinstance(item_data, dict):
                # Already a dict
                result.append(item_data)

        return result

    @abstractmethod
    def process(self, content: Any) -> str:
        """
        Process section content into LaTeX format.

        Args:
            content: The section content to process

        Returns:
            LaTeX formatted content - should be just the content without
            section headers or formatting as those come from tex_headers.
            DO NOT include section environment tags like \\resumeSubHeadingListStart
            as these are already in the tex_headers templates.
        """
        pass

    def generate_content(self, content: Any) -> str:
        """
        Generate content for a section without adding section markup.
        This provides the raw content to be used with section headers from tex_headers.

        Args:
            content: The section content to process

        Returns:
            Processed content without section markup
        """
        return self.process(content)
