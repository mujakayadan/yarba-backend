"""Publications section processor."""

from typing import Any

from ..utils.safety import sanitize_latex
from .base import SectionProcessor


class PublicationsProcessor(SectionProcessor):
    """Processor for publications section."""

    def process(self, content: Any) -> str:
        """Process publications data into LaTeX content.

        Args:
            content: Publications data

        Returns:
            LaTeX content for publications
        """
        # Parse the content
        data = self.parse_content(content)

        # Handle empty case
        if not data:
            return ""

        result = []

        # Handle nested array format (special case from our API response)
        # Format: [[["name", "Paper Title"], ["publisher", "Journal Name"], ["link", "URL"], ["time", "Date"]], [...]]
        if isinstance(data, list) and all(isinstance(item, list) for item in data):
            # Convert nested arrays to list of dictionaries
            pub_dicts = self.convert_nested_arrays_to_dict(data)

            for pub_dict in pub_dicts:
                name = sanitize_latex(pub_dict.get("name", ""))
                publisher = sanitize_latex(pub_dict.get("publisher", ""))
                time = sanitize_latex(pub_dict.get("time", ""))
                link = sanitize_latex(pub_dict.get("link", ""))

                if name:
                    if not link:
                        link = "#"

                    publication_content = f"\\resumeProjectHeading\n{{\\textbf{{{name}}}}}{{{time}}}\n\\resumeItem{{\\href{{{link}}}{{\\color{{blue}}{publisher}}}}}"
                    result.append(publication_content)

        # Process list of publication objects (standard format)
        elif isinstance(data, list) and all(
            isinstance(item, dict) for item in data if isinstance(item, dict)
        ):
            for pub in data:
                if not isinstance(pub, dict):
                    continue

                # Extract publication details with defaults
                name = sanitize_latex(pub.get("name", ""))
                publisher = sanitize_latex(pub.get("publisher", ""))
                time = sanitize_latex(pub.get("time", ""))
                link = sanitize_latex(pub.get("link", ""))

                # Skip if name is missing
                if not name:
                    continue

                # If link is empty, use # to keep the link structure
                if not link:
                    link = "#"

                # Format the publication using the publication_item template format
                publication_content = f"\\resumeProjectHeading\n{{\\textbf{{{name}}}}}{{{time}}}\n\\resumeItem{{\\href{{{link}}}{{\\color{{blue}}{publisher}}}}}"
                result.append(publication_content)

        # Handle dictionary format (single publication or nested)
        elif isinstance(data, dict):
            # Check if it's a dictionary with nested publications
            if "publications" in data and isinstance(data["publications"], list):
                for pub in data["publications"]:
                    if not isinstance(pub, dict):
                        continue

                    name = sanitize_latex(pub.get("name", ""))
                    publisher = sanitize_latex(pub.get("publisher", ""))
                    time = sanitize_latex(pub.get("time", ""))
                    link = sanitize_latex(pub.get("link", ""))

                    if not name:
                        continue

                    if not link:
                        link = "#"

                    publication_content = f"\\resumeProjectHeading\n{{\\textbf{{{name}}}}}{{{time}}}\n\\resumeItem{{\\href{{{link}}}{{\\color{{blue}}{publisher}}}}}"
                    result.append(publication_content)
            else:
                # It's a single publication
                name = sanitize_latex(data.get("name", ""))
                publisher = sanitize_latex(data.get("publisher", ""))
                time = sanitize_latex(data.get("time", ""))
                link = sanitize_latex(data.get("link", ""))

                if name:
                    if not link:
                        link = "#"

                    publication_content = f"\\resumeProjectHeading\n{{\\textbf{{{name}}}}}{{{time}}}\n\\resumeItem{{\\href{{{link}}}{{\\color{{blue}}{publisher}}}}}"
                    result.append(publication_content)

        # If no publications were processed but we had data, add a placeholder
        if not result and data:
            result.append(
                "\\resumeProjectHeading\n{\\textbf{Publication Title}}{YYYY-MM}\n\\resumeItem{\\href{#}{\\color{blue}Journal or Conference}}"
            )

        # Check if there are any results to display
        if not result:
            return ""

        # Return the fully formatted publications section
        return f"% Publications\n\\section{{Publications}}\n\\vspace{{3pt}}\n\\resumeSubHeadingListStart\n{'\n'.join(result)}\n\\resumeSubHeadingListEnd\n\n"
