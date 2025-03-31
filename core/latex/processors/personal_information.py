"""Personal information section processor."""

from typing import Any, Dict

from ..utils.sanitizer import sanitize_latex
from .base import SectionProcessor


class PersonalInformationProcessor(SectionProcessor):
    """Processor for personal information section."""

    def process(self, content: Any) -> str:
        """
        Process personal information into LaTeX content.

        Args:
            content: Personal information data

        Returns:
            LaTeX content for personal information
        """
        # Parse the content
        data = self.parse_content(content)

        if not isinstance(data, dict):
            self.logger.warning(f"Personal information is not a dict: {type(data)}")
            return ""

        # Extract the fields with defaults
        full_name = sanitize_latex(data.get("full_name", ""))
        email = sanitize_latex(data.get("email", ""))
        phone = sanitize_latex(data.get("phone", ""))
        address = sanitize_latex(data.get("address", ""))
        linkedin = sanitize_latex(data.get("linkedin", ""))
        github = sanitize_latex(data.get("github", ""))
        website = sanitize_latex(data.get("website", ""))

        # Return formatted for personalInformation command (note the capital 'I')
        # The personalInformation command expects parameters in this order:
        # \personalInformation{full_name}{phone}{email}{linkedin}{github}{website}{address}
        return f"\\personalInformation{{{full_name}}}{{{phone}}}{{{email}}}{{{linkedin}}}{{{github}}}{{{website}}}{{{address}}}"
