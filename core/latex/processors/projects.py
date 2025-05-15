"""Projects section processor."""

from typing import Any, Dict, List

from config.settings import settings

from ..utils.safety import sanitize_latex
from .base import SectionProcessor


class ProjectsProcessor(SectionProcessor):
    """Processor for projects section."""

    def process(self, content: Any) -> str:
        """
        Process projects data into LaTeX content.

        Args:
            content: Projects data

        Returns:
            LaTeX content for projects
        """
        # Parse the content
        data = self.parse_content(content)

        # Handle empty case
        if not data:
            return "\\resumeProjectHeading\n{Project Name}\n{01/2023 - Present}\n\\resumeItemListStart\n\\resumeItem{Project description}\n\\resumeItemListEnd"

        result = []

        # Process list of projects
        if isinstance(data, list):
            for project in data:
                if not isinstance(project, dict):
                    continue

                # Extract project details with defaults
                name = sanitize_latex(project.get("name", ""))
                tech = sanitize_latex(project.get("technologies", ""))
                date = sanitize_latex(project.get("date", ""))
                link = project.get("link")  # Get the link

                # Use default values if missing
                name = name or "Project"
                date = date or "01/2023 - Present"

                # Combine name and technology if both are present
                name_display = name
                if tech:
                    name_display = f"{name} \\textit{{{tech}}}"

                # Add hyperlink if link is present
                if link:
                    # Sanitize the link URL itself for LaTeX
                    safe_link = sanitize_latex(str(link))
                    # Make the [link] text small, italic, and underlined
                    link_indicator = "\\textit{\\small \\underline{[link]}}"
                    name_heading = (
                        f"\\href{{{safe_link}}}{{{name_display} {link_indicator}}}"
                    )
                else:
                    name_heading = name_display

                # Extract and process bullet points
                bullet_points = project.get("bullet_points", [])
                points = []

                if isinstance(bullet_points, list) and bullet_points:
                    for point in bullet_points:
                        points.append(f"\\resumeItem{{{sanitize_latex(point)}}}")
                elif isinstance(bullet_points, str) and bullet_points:
                    points.append(f"\\resumeItem{{{sanitize_latex(bullet_points)}}}")
                else:
                    # Ensure we have at least one point
                    points.append("\\resumeItem{Project description}")

                # Format the project using the project_item template format
                bullet_points_text = "\n".join(points)
                project_content = f"\\resumeProjectHeading\n{{{name_heading}}}\n{{{date}}}\n\\resumeItemListStart\n{bullet_points_text}\n\\resumeItemListEnd"
                result.append(project_content)

        # Handle dictionary format (single project or nested)
        elif isinstance(data, dict):
            # Check if it's a dictionary with nested projects
            if "projects" in data and isinstance(data["projects"], list):
                for project in data["projects"]:
                    if not isinstance(project, dict):
                        continue

                    name = sanitize_latex(project.get("name", ""))
                    tech = sanitize_latex(project.get("technologies", ""))
                    date = sanitize_latex(project.get("date", ""))
                    link = project.get("link")  # Get the link

                    # Use default values if missing
                    name = name or "Project"
                    date = date or "01/2023 - Present"

                    # Combine name and technology if both are present
                    name_display = name
                    if tech:
                        name_display = f"{name} \\textit{{{tech}}}"

                    # Add hyperlink if link is present
                    if link:
                        safe_link = sanitize_latex(str(link))
                        link_indicator = "\\textit{\\small \\underline{[link]}}"
                        name_heading = (
                            f"\\href{{{safe_link}}}{{{name_display} {link_indicator}}}"
                        )
                    else:
                        name_heading = name_display

                    # Extract and process bullet points
                    bullet_points = project.get("bullet_points", [])
                    points = []

                    if isinstance(bullet_points, list) and bullet_points:
                        for point in bullet_points:
                            points.append(f"\\resumeItem{{{sanitize_latex(point)}}}")
                    elif isinstance(bullet_points, str) and bullet_points:
                        points.append(
                            f"\\resumeItem{{{sanitize_latex(bullet_points)}}}"
                        )
                    else:
                        # Ensure we have at least one point
                        points.append("\\resumeItem{Project description}")

                    bullet_points_text = "\n".join(points)
                    project_content = f"\\resumeProjectHeading\n{{{name_heading}}}\n{{{date}}}\n\\resumeItemListStart\n{bullet_points_text}\n\\resumeItemListEnd"
                    result.append(project_content)
            else:
                # It's a single project
                name = sanitize_latex(data.get("name", ""))
                tech = sanitize_latex(data.get("technologies", ""))
                date = sanitize_latex(data.get("date", ""))
                link = data.get("link")  # Get the link

                # Use default values if missing
                name = name or "Project"
                date = date or "01/2023 - Present"

                # Combine name and technology if both are present
                name_display = name
                if tech:
                    name_display = f"{name} \\textit{{{tech}}}"

                # Add hyperlink if link is present
                if link:
                    safe_link = sanitize_latex(str(link))
                    link_indicator = "\\textit{\\small \\underline{[link]}}"
                    name_heading = (
                        f"\\href{{{safe_link}}}{{{name_display} {link_indicator}}}"
                    )
                else:
                    name_heading = name_display

                # Extract and process bullet points
                bullet_points = data.get("bullet_points", [])
                points = []

                if isinstance(bullet_points, list) and bullet_points:
                    for point in bullet_points:
                        points.append(f"\\resumeItem{{{sanitize_latex(point)}}}")
                elif isinstance(bullet_points, str) and bullet_points:
                    points.append(f"\\resumeItem{{{sanitize_latex(bullet_points)}}}")
                else:
                    # Ensure we have at least one point
                    points.append("\\resumeItem{Project description}")

                bullet_points_text = "\n".join(points)
                project_content = f"\\resumeProjectHeading\n{{{name_heading}}}\n{{{date}}}\n\\resumeItemListStart\n{bullet_points_text}\n\\resumeItemListEnd"
                result.append(project_content)

        # Return projects content
        if result:
            formatted_projects = "\n".join(result)
        else:
            # Provide a placeholder
            formatted_projects = "\\resumeProjectHeading\n{Project Name}\n{01/2023 - Present}\n\\resumeItemListStart\n\\resumeItem{Project description}\n\\resumeItemListEnd"

        # Return the fully formatted projects section
        return f"% Projects\n\\section{{Projects}}\n\\resumeSubHeadingListStart\n{formatted_projects}\n\\resumeSubHeadingListEnd\n\n"
