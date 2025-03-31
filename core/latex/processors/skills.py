"""Skills section processor."""

from typing import Any, Dict, List

from ..utils.sanitizer import sanitize_latex
from .base import SectionProcessor


class SkillsProcessor(SectionProcessor):
    """Processor for skills section."""

    def process(self, content: Any) -> str:
        """
        Process skills into LaTeX content (not formatting).

        Args:
            content: Skills data

        Returns:
            LaTeX content for skills without section formatting
        """
        # Parse the content
        data = self.parse_content(content)

        if isinstance(data, str):
            # If it's still a string after parsing attempt, just return it sanitized
            return sanitize_latex(data)

        result = []

        # Process different data structures
        if isinstance(data, dict):
            # Handle dictionary format with "skills" key
            if "skills" in data and isinstance(data["skills"], list):
                for category in data["skills"]:
                    if isinstance(category, dict):
                        category_name = sanitize_latex(category.get("category", ""))
                        skills_list = category.get("skills", [])

                        if category_name and skills_list:
                            # Add skill item with proper format for template
                            result.append(
                                f"\\resumeSkillHeading{{{category_name}}}{{{sanitize_latex(', '.join(skills_list))}}}"
                            )

            # Handle dictionary with category keys directly
            elif any(isinstance(data.get(key), list) for key in data):
                for category, skills in data.items():
                    if isinstance(skills, list) and skills:
                        result.append(
                            f"\\resumeSkillHeading{{{sanitize_latex(category)}}}{{{sanitize_latex(', '.join(skills))}}}"
                        )

        # Handle list of dictionaries with category/skills structure
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "category" in item and "skills" in item:
                    category = sanitize_latex(item["category"])
                    skills = item["skills"]
                    if isinstance(skills, list) and skills:
                        result.append(
                            f"\\resumeSkillHeading{{{category}}}{{{sanitize_latex(', '.join(skills))}}}"
                        )

        # If no skills were processed but we had data, add a placeholder
        if not result and data:
            # Add placeholder if no skills were found
            result.append("\\resumeSkillHeading{Technical Skills}{Placeholder skills}")

        return "\n".join(result)
