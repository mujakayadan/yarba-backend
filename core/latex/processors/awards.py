"""Awards section processor."""

from typing import Any

from ..utils.safety import sanitize_latex
from .base import SectionProcessor


class AwardsProcessor(SectionProcessor):
    """Processor for awards section."""

    def process(self, content: Any) -> str:
        """Process awards data into LaTeX content.

        Args:
            content: Awards data

        Returns:
            LaTeX content for awards
        """
        # Parse the content
        data = self.parse_content(content)

        # Handle empty case
        if not data:
            return ""

        result = []

        # Handle nested array format (special case from our API response)
        # Format: [[["name", "Award Name"], ["explanation", "Award Explanation"]], [...]]
        if isinstance(data, list) and all(isinstance(item, list) for item in data):
            # Convert nested arrays to list of dictionaries
            awards_dicts = self.convert_nested_arrays_to_dict(data)

            for award_dict in awards_dicts:
                name = sanitize_latex(award_dict.get("name", ""))
                explanation = sanitize_latex(award_dict.get("explanation", ""))

                if name:
                    award_content = f"\\resumeAwardHeading{{{name}}}{{{explanation}}}"
                    result.append(award_content)

        # Process list of award objects (standard format)
        elif isinstance(data, list) and all(
            isinstance(item, dict) for item in data if isinstance(item, dict)
        ):
            for award in data:
                if not isinstance(award, dict):
                    continue

                # Extract award details with defaults
                name = sanitize_latex(award.get("name", ""))
                explanation = sanitize_latex(award.get("explanation", ""))

                # Skip if name is missing
                if not name:
                    continue

                # Format the award using the award_item template format
                award_content = f"\\resumeAwardHeading{{{name}}}{{{explanation}}}"
                result.append(award_content)

        # Handle dictionary format (single award or nested)
        elif isinstance(data, dict):
            # Check if it's a dictionary with nested awards
            if "awards" in data and isinstance(data["awards"], list):
                for award in data["awards"]:
                    if not isinstance(award, dict):
                        continue

                    name = sanitize_latex(award.get("name", ""))
                    explanation = sanitize_latex(award.get("explanation", ""))

                    if not name:
                        continue

                    award_content = f"\\resumeAwardHeading{{{name}}}{{{explanation}}}"
                    result.append(award_content)
            else:
                # It's a single award
                name = sanitize_latex(data.get("name", ""))
                explanation = sanitize_latex(data.get("explanation", ""))

                if name:
                    award_content = f"\\resumeAwardHeading{{{name}}}{{{explanation}}}"
                    result.append(award_content)

        # If no awards were processed but we had data, add a placeholder
        if not result and data:
            result.append(
                "\\resumeAwardHeading{Achievement}{Notable achievement or award}"
            )

        # Check if there are any results to display
        if not result:
            return ""

        # Return the fully formatted awards section
        return f"% Awards \\& Achievements\n\\section{{Awards \\& Achievements}}\n\\resumeSubHeadingListStart\n{'\n'.join(result)}\n\\resumeSubHeadingListEnd\n\n"
