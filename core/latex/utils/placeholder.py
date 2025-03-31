"""LaTeX placeholder management utilities."""

import re
from typing import Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger(__name__)


class PlaceholderMixin:
    """Mixin class for objects that provide placeholder values."""

    def get_placeholders(self) -> Dict[str, str]:
        """
        Get a dictionary of non-callable attributes as placeholders.

        Returns:
            Dict[str, str]: Dictionary of attribute names and values
        """
        return {
            key: str(value)
            for key, value in self.__dict__.items()
            if not key.startswith("_") and not callable(value)
        }


class PlaceholderManager:
    """Manager for handling placeholders in LaTeX templates."""

    def __init__(self, start_delimiter: str = "{{", end_delimiter: str = "}}"):
        """
        Initialize the placeholder manager.

        Args:
            start_delimiter: Start delimiter for placeholders
            end_delimiter: End delimiter for placeholders
        """
        self.start_delimiter = re.escape(start_delimiter)
        self.end_delimiter = re.escape(end_delimiter)
        self.placeholder_pattern = re.compile(
            f"{self.start_delimiter}(.*?){self.end_delimiter}"
        )

        # Also support single-brace placeholders for LaTeX commands
        self.single_brace_pattern = re.compile(r"\{([A-Za-z0-9_]+)\}")

    def replace_placeholders(
        self,
        template: str,
        values: Dict[str, str],
        raise_on_missing: bool = True,
        default_value: str = "",
        single_braces: bool = False,
    ) -> str:
        """
        Replace placeholders in a template with their values.

        Args:
            template: Template string containing placeholders
            values: Dictionary of placeholder values
            raise_on_missing: Whether to raise an error for missing placeholders
            default_value: Default value for missing placeholders
            single_braces: Whether to use single-brace pattern matching (for LaTeX commands)

        Returns:
            str: Template with placeholders replaced

        Raises:
            ValueError: If a placeholder is missing and raise_on_missing is True
        """

        def replace_match(match: re.Match) -> str:
            key = match.group(1).strip()
            if key not in values:
                if raise_on_missing:
                    raise ValueError(f"Missing placeholder value for '{key}'")
                logger.warning(f"Missing placeholder value for '{key}', using default")
                return default_value
            return str(values[key])

        # Use the appropriate pattern based on the single_braces flag
        pattern = (
            self.single_brace_pattern if single_braces else self.placeholder_pattern
        )
        return pattern.sub(replace_match, template)

    def replace_all_placeholders(
        self,
        template: str,
        values: Dict[str, str],
        raise_on_missing: bool = False,
        default_value: str = "",
    ) -> str:
        """
        Replace both double-brace and single-brace placeholders.

        Args:
            template: Template string containing placeholders
            values: Dictionary of placeholder values
            raise_on_missing: Whether to raise an error for missing placeholders
            default_value: Default value for missing placeholders

        Returns:
            str: Template with all placeholders replaced
        """
        # First replace standard double-brace placeholders
        result = self.replace_placeholders(
            template, values, raise_on_missing, default_value, single_braces=False
        )

        # Then replace single-brace placeholders
        result = self.replace_placeholders(
            result, values, raise_on_missing, default_value, single_braces=True
        )

        return result

    def extract_placeholders(self, template: str) -> List[str]:
        """
        Extract all unique placeholder keys from a template.

        Args:
            template: Template string containing placeholders

        Returns:
            List[str]: List of unique placeholder keys
        """
        matches = self.placeholder_pattern.finditer(template)
        return sorted(set(match.group(1).strip() for match in matches))

    def validate_placeholders(
        self,
        template: str,
        values: Dict[str, str],
        raise_on_missing: bool = True,
    ) -> bool:
        """
        Check if all required placeholders are provided.

        Args:
            template: Template string containing placeholders
            values: Dictionary of placeholder values
            raise_on_missing: Whether to raise an error for missing placeholders

        Returns:
            bool: True if all placeholders are provided

        Raises:
            ValueError: If placeholders are missing and raise_on_missing is True
        """
        required = set(self.extract_placeholders(template))
        provided = set(values.keys())
        missing = required - provided

        if missing:
            message = f"Missing placeholder values: {', '.join(sorted(missing))}"
            if raise_on_missing:
                raise ValueError(message)
            logger.warning(message)
            return False

        return True
