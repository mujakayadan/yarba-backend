"""Certifications section processor."""

from typing import Any, Dict, List

from ..utils.sanitizer import sanitize_latex
from .base import SectionProcessor


class CertificationsProcessor(SectionProcessor):
    """Processor for certifications section."""

    def process(self, content: Any) -> str:
        """
        Process certifications data into LaTeX content.

        Args:
            content: Certifications data

        Returns:
            LaTeX content for certifications
        """
        # Parse the content
        data = self.parse_content(content)

        # Handle empty case
        if not data:
            return ""

        result = []

        # Process list of certifications
        if isinstance(data, list):
            for cert in data:
                if not isinstance(cert, dict):
                    continue

                # Extract certification details with defaults
                name = sanitize_latex(cert.get("name", ""))
                issuer = sanitize_latex(cert.get("issuer", ""))
                date = sanitize_latex(cert.get("date", ""))

                # Skip if name is missing
                if not name:
                    continue

                # Format the certification using a project-like format since no specific template exists
                cert_content = f"\\resumeProjectHeading\n{{{name}}}{{{date}}}\n\\resumeItem{{{issuer}}}"
                result.append(cert_content)

        # Handle dictionary format (single certification or nested)
        elif isinstance(data, dict):
            # Check if it's a dictionary with nested certifications
            if "certifications" in data and isinstance(data["certifications"], list):
                for cert in data["certifications"]:
                    if not isinstance(cert, dict):
                        continue

                    name = sanitize_latex(cert.get("name", ""))
                    issuer = sanitize_latex(cert.get("issuer", ""))
                    date = sanitize_latex(cert.get("date", ""))

                    if not name:
                        continue

                    cert_content = f"\\resumeProjectHeading\n{{{name}}}{{{date}}}\n\\resumeItem{{{issuer}}}"
                    result.append(cert_content)
            else:
                # It's a single certification
                name = sanitize_latex(data.get("name", ""))
                issuer = sanitize_latex(data.get("issuer", ""))
                date = sanitize_latex(data.get("date", ""))

                if name:
                    cert_content = f"\\resumeProjectHeading\n{{{name}}}{{{date}}}\n\\resumeItem{{{issuer}}}"
                    result.append(cert_content)

        # Check if there are any results to display
        if not result:
            return ""

        # Return the fully formatted certifications section
        return f"% Certifications\n\\section{{Certifications}}\n\\resumeSubHeadingListStart\n{'\n'.join(result)}\n\\resumeSubHeadingListEnd\n\n"
