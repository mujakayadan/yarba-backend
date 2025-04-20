"""Personal information section processor."""

from typing import Any, Dict
from urllib.parse import urlparse

from config.settings import settings

from ..utils.safety import sanitize_latex
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

        # Return formatted for personalInformation command (capital 'I')
        # The personalInformation command expects parameters in this order:
        # \personalInformation{full_name}{phone}{email}{linkedin}{github}{website}{address}
        personalinfo_cmd = f"\\personalInformation{{{full_name}}}{{{phone}}}{{{email}}}{{{linkedin}}}{{{github}}}{{{website}}}{{{address}}}"
        self.logger.debug(
            f"Generated personal info command: {personalinfo_cmd[:40]}..."
        )

        # Return the fully formatted personal information section
        return f"% Personal Information\n{personalinfo_cmd}\n\n"
