"""Base section processor for LaTeX document generation."""

import json
from typing import Any, Dict, List

from config.logging_config import get_logger

from ..utils.safety import sanitize_latex


class SectionProcessor:
    """Base class for section processors.

    This class defines the interface for section processors and provides
    common functionality for parsing and processing section data.
    """

    def __init__(self):
        """Initialize the processor."""
        self.logger = get_logger(self.__class__.__name__)

    def process(self, content: Any) -> str:
        """
        Process content into LaTeX format.

        This is the main method that should be implemented by subclasses.

        Args:
            content: Section content to process

        Returns:
            Processed LaTeX content
        """
        # Default implementation just returns sanitized content
        if isinstance(content, str):
            return sanitize_latex(content)
        return ""

    def parse_content(self, content: Any) -> Any:
        """
        Parse section content into a usable format.

        Args:
            content: Raw section content

        Returns:
            Parsed content in a usable format
        """
        # If content is None or empty, return None
        if content is None or (isinstance(content, (str, list, dict)) and not content):
            return None

        # If content is already a string, dict, or list, return it as is
        if isinstance(content, (dict, list)):
            return content

        # If content is a string, try to parse it as JSON
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
                if parsed:
                    return parsed
            except (json.JSONDecodeError, TypeError, ValueError):
                # If not valid JSON, return the string as is
                return content

        # For any other type, convert to string and return
        return str(content)

    def extract_section_data(
        self, resume_data: Dict[str, Any], section_name: str
    ) -> Any:
        """
        Extract section data from resume data.

        Args:
            resume_data: Complete resume data
            section_name: Name of the section to extract

        Returns:
            Section data or None if not found
        """
        # If section_name is in resume_data, return its value
        if section_name in resume_data:
            return resume_data[section_name]

        # If resume_data has a 'content' field, check there
        if "content" in resume_data and isinstance(resume_data["content"], dict):
            content = resume_data["content"]
            if section_name in content:
                return content[section_name]

        # If not found, return None
        return None

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
