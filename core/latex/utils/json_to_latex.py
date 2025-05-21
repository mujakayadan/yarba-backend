"""Utility for converting JSON schema data to LaTeX format."""

import json
from typing import Any, Dict

from config.logging_config import get_logger

from .safety import sanitize_latex

logger = get_logger(__name__)


def parse_json_content(content: Any) -> Any:
    """
    Parse JSON content safely, handling various input formats.

    This function handles:
    1. JSON strings
    2. Already parsed dictionaries/lists
    3. Objects with attributes that need conversion

    Args:
        content: The content to parse, could be a string, dict, or other object

    Returns:
        Parsed content in a format suitable for LaTeX conversion
    """
    # Handle None case
    if content is None:
        return {}

    # If content is already a dict or list, return as is
    if isinstance(content, (dict, list)):
        return content

    # If content is a string, try to parse as JSON
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # If not valid JSON, return as is - will be sanitized later
            return content

    # If content has a method like model_dump or dict, use it
    if hasattr(content, "model_dump"):
        # Pydantic v2
        return content.model_dump()
    elif hasattr(content, "dict") and callable(content.dict):
        # Pydantic v1 or similar
        return content.model_dump()

    # Return string representation for other types
    return str(content)


def process_personal_information(content: Any) -> Dict[str, str]:
    """
    Process personal information from JSON schema format.

    Args:
        content: Personal information in JSON schema format

    Returns:
        Dict with personal information fields
    """
    data = parse_json_content(content)

    if not isinstance(data, dict):
        logger.warning(f"Personal information is not a dict: {type(data)}")
        return {}

    # Extract fields from the schema
    return {
        "full_name": sanitize_latex(data.get("full_name", "")),
        "email": sanitize_latex(data.get("email", "")),
        "phone": sanitize_latex(data.get("phone", "")),
        "address": sanitize_latex(data.get("address", "")),
        "linkedin": sanitize_latex(data.get("linkedin", "")),
        "github": sanitize_latex(data.get("github", "")),
        "website": sanitize_latex(data.get("website", "")),
    }


def process_awards(content: Any) -> str:
    """
    Process awards from JSON schema format to LaTeX format.

    Args:
        content: Awards in JSON schema format

    Returns:
        LaTeX formatted awards content
    """
    logger.debug(
        f"Processing awards content: {content} (type: {type(content).__name__})"
    )

    data = parse_json_content(content)
    logger.debug(f"Parsed awards data: {data} (type: {type(data).__name__})")

    if isinstance(data, str):
        # If it's still a string after parsing attempt, return as is
        logger.warning(f"Awards data is still a string after parsing: {data}")
        return sanitize_latex(data)

    result = []
    # Add the wrapper for the list of awards
    result.append("\\resumeSubHeadingListStart")

    # Handle both direct list of awards and dict with "awards" key
    awards_list = []
    if isinstance(data, dict) and "awards" in data and isinstance(data["awards"], list):
        awards_list = data["awards"]
        logger.debug(f"Found awards list in dictionary with {len(awards_list)} items")
    elif isinstance(data, list):
        awards_list = data
        logger.debug(f"Using direct awards list with {len(awards_list)} items")

    # Process each award
    for i, award in enumerate(awards_list):
        logger.debug(f"Processing award {i}: {award} (type: {type(award).__name__})")
        if isinstance(award, dict):
            name = sanitize_latex(award.get("name", ""))
            explanation = sanitize_latex(award.get("explanation", ""))

            if name and explanation:
                logger.debug(f"Adding award: {name} - {explanation}")
                result.append(f"\\resumeAwardHeading{{{name}}}{{{explanation}}}")
            else:
                logger.warning(f"Award {i} is missing name or explanation: {award}")
        elif isinstance(award, list) and len(award) >= 2:
            # Try to handle array format [name, explanation]
            name = sanitize_latex(str(award[0]))
            explanation = sanitize_latex(str(award[1]))
            logger.debug(f"Adding award from array: {name} - {explanation}")
            result.append(f"\\resumeAwardHeading{{{name}}}{{{explanation}}}")
        else:
            logger.warning(f"Unrecognized award format: {award}")

    # End the list
    result.append("\\resumeSubHeadingListEnd")

    latex_result = "\n".join(result)
    logger.debug(f"Final awards LaTeX result: {latex_result}")
    return latex_result


def process_skills(content: Any) -> str:
    """
    Process skills from JSON schema format to LaTeX format.

    Args:
        content: Skills in JSON schema format

    Returns:
        LaTeX formatted skills content
    """
    data = parse_json_content(content)

    if isinstance(data, str):
        # If it's still a string after parsing attempt, return as is
        return sanitize_latex(data)

    result = []

    if isinstance(data, dict) and "skills" in data and isinstance(data["skills"], list):
        result.append("\\resumeSubHeadingListStart")

        for category in data["skills"]:
            if isinstance(category, dict):
                category_name = sanitize_latex(category.get("category", ""))
                skills_list = category.get("skills", [])

                if isinstance(skills_list, list) and skills_list:
                    skills_str = ", ".join(
                        sanitize_latex(skill) for skill in skills_list
                    )
                    result.append(
                        f"\\resumeSkillHeading{{{category_name}}}{{{skills_str}}}"
                    )

        result.append("\\resumeSubHeadingListEnd")

    return "\n".join(result)


def process_work_experience(content: Any) -> str:
    """
    Process work experience from JSON schema format to LaTeX format.

    Args:
        content: Work experience in JSON schema format

    Returns:
        LaTeX formatted work experience content
    """
    data = parse_json_content(content)

    if isinstance(data, str):
        # If it's still a string after parsing attempt, return as is
        return sanitize_latex(data)

    result = []

    if (
        isinstance(data, dict)
        and "work_experience" in data
        and isinstance(data["work_experience"], list)
    ):
        result.append("\\resumeSubHeadingListStart")

        for job in data["work_experience"]:
            if isinstance(job, dict):
                job_title = sanitize_latex(job.get("job_title", ""))
                company = sanitize_latex(job.get("company", ""))
                location = sanitize_latex(job.get("location", ""))
                time = sanitize_latex(job.get("time", ""))
                responsibilities = job.get("responsibilities", [])

                # Add the subheading
                result.append(
                    f"\\resumeSubheading{{{job_title}}}{{{time}}}{{{company}}}{{{location}}}"
                )

                # Add the responsibilities as bullet points
                if isinstance(responsibilities, list) and responsibilities:
                    result.append("\\resumeItemListStart")

                    for responsibility in responsibilities:
                        result.append(
                            f"\\resumeItem{{{sanitize_latex(responsibility)}}}"
                        )

                    result.append("\\resumeItemListEnd")

        result.append("\\resumeSubHeadingListEnd")

    return "\n".join(result)


def process_education(content: Any) -> str:
    """
    Process education from JSON schema format to LaTeX format.

    Args:
        content: Education in JSON schema format

    Returns:
        LaTeX formatted education content
    """
    data = parse_json_content(content)

    if isinstance(data, str):
        # If it's still a string after parsing attempt, return as is
        return sanitize_latex(data)

    result = []

    if (
        isinstance(data, dict)
        and "education" in data
        and isinstance(data["education"], list)
    ):
        result.append("\\resumeSubHeadingListStart")

        for edu in data["education"]:
            if isinstance(edu, dict):
                university_name = sanitize_latex(edu.get("university_name", ""))
                location = sanitize_latex(edu.get("location", ""))
                degree_type = sanitize_latex(edu.get("degree_type", ""))
                degree = sanitize_latex(edu.get("degree", ""))
                time = sanitize_latex(edu.get("time", ""))
                gpa = sanitize_latex(edu.get("GPA", ""))
                transcript = edu.get("transcript", [])

                # Combine degree type and degree
                full_degree = f"{degree_type} in {degree}" if degree else degree_type

                # Add GPA if available
                full_degree = f"{full_degree}, GPA: {gpa}" if gpa else full_degree

                # Format transcript as a string
                if isinstance(transcript, list) and transcript:
                    transcript_str = "Key Courses: " + ", ".join(
                        sanitize_latex(course) for course in transcript
                    )
                else:
                    transcript_str = ""

                # Add the education entry
                result.append(
                    f"\\resumeEducationHeading{{{university_name}}}{{{location}}}{{{full_degree}}}{{{time}}}{{{transcript_str}}}"
                )

        result.append("\\resumeSubHeadingListEnd")

    return "\n".join(result)


def process_projects(content: Any) -> str:
    """
    Process projects from JSON schema format to LaTeX format.

    Args:
        content: Projects in JSON schema format

    Returns:
        LaTeX formatted projects content
    """
    data = parse_json_content(content)

    if isinstance(data, str):
        # If it's still a string after parsing attempt, return as is
        return sanitize_latex(data)

    result = []

    if (
        isinstance(data, dict)
        and "projects" in data
        and isinstance(data["projects"], list)
    ):
        result.append("\\resumeSubHeadingListStart")

        for project in data["projects"]:
            if isinstance(project, dict):
                name = sanitize_latex(project.get("name", ""))
                date = sanitize_latex(project.get("date", ""))
                bullet_points = project.get("bullet_points", [])

                # Add the project heading
                result.append(f"\\resumeProjectHeading{{{name}}}{{{date}}}")

                # Add the bullet points
                if isinstance(bullet_points, list) and bullet_points:
                    result.append("\\resumeItemListStart")

                    for point in bullet_points:
                        result.append(f"\\resumeItem{{{sanitize_latex(point)}}}")

                    result.append("\\resumeItemListEnd")

        result.append("\\resumeSubHeadingListEnd")

    return "\n".join(result)


def process_publications(content: Any) -> str:
    """
    Process publications from JSON schema format to LaTeX format.

    Args:
        content: Publications in JSON schema format

    Returns:
        LaTeX formatted publications content
    """
    data = parse_json_content(content)

    if isinstance(data, str):
        # If it's still a string after parsing attempt, return as is
        return sanitize_latex(data)

    result = []

    if (
        isinstance(data, dict)
        and "publications" in data
        and isinstance(data["publications"], list)
    ):
        result.append("\\resumeSubHeadingListStart")

        for pub in data["publications"]:
            if isinstance(pub, dict):
                name = sanitize_latex(pub.get("name", ""))
                publisher = sanitize_latex(pub.get("publisher", ""))
                time = sanitize_latex(pub.get("time", ""))
                link = pub.get("link", "")

                # Add the publication heading
                result.append(f"\\resumeProjectHeading{{{name}}}{{{time}}}")

                # Start item list for publication details
                result.append("\\resumeItemListStart")

                # Add the publication details as an item
                if link:
                    # Avoid nested f-strings by using string concatenation
                    safe_link = sanitize_latex(link)
                    safe_publisher = sanitize_latex(publisher)
                    result.append(
                        f"\\resumeItem{{\\href{{{safe_link}}}{{\\color{{blue}}{safe_publisher}}}}}"
                    )
                else:
                    result.append(f"\\resumeItem{{{sanitize_latex(publisher)}}}")

                # End item list
                result.append("\\resumeItemListEnd")

        result.append("\\resumeSubHeadingListEnd")

    return "\n".join(result)


def process_career_summary(content: Any) -> str:
    """
    Process career summary from JSON schema format to LaTeX format.

    Args:
        content: Career summary in JSON schema format

    Returns:
        LaTeX formatted career summary content
    """
    data = parse_json_content(content)

    if isinstance(data, str):
        # If it's still a string after parsing attempt, return as is
        return sanitize_latex(data)

    if isinstance(data, dict):
        # Get the primary job title - prioritize job_title field
        primary_title = ""
        if "job_title" in data:
            primary_title = sanitize_latex(data["job_title"])
        elif "default_job_title" in data and data["default_job_title"]:
            primary_title = sanitize_latex(data["default_job_title"])
        elif "job_titles" in data:
            job_titles = data.get("job_titles", [])
            if isinstance(job_titles, list) and job_titles:
                primary_title = sanitize_latex(job_titles[0])
            elif isinstance(job_titles, str):
                primary_title = sanitize_latex(job_titles)

        # Get years of experience and default summary
        years_of_experience = data.get("years_of_experience", "")
        default_summary = data.get("default_summary", "")

        # Format the career summary using the careerSummary command
        if primary_title and years_of_experience and default_summary:
            return f"\\careerSummary{{{primary_title}}}{{{sanitize_latex(years_of_experience)}}}{{{sanitize_latex(default_summary)}}}"

    # Return empty string if we can't parse the career summary
    return ""


def process_content_by_section(section_name: str, content: Any) -> str:
    """
    Process content by section type, extracting structured content.

    Note: This function now focuses on extracting structured content for use with templates
    rather than directly including LaTeX formatting commands.

    Args:
        section_name: The name of the section to process
        content: The content to process, can be a string (JSON or plain text) or already parsed JSON

    Returns:
        LaTeX formatted content
    """
    logger.debug(f"Processing content for section {section_name}")

    # Try to parse content if it's a string
    parsed_content = parse_json_content(content)
    logger.debug(f"Parsed content type: {type(parsed_content).__name__}")

    # Select appropriate processor based on section name
    if section_name == "personal_information":
        # Just extract the values, LaTeX formatting handled by template
        return process_personal_information(parsed_content)
    elif section_name == "career_summary":
        return process_career_summary(parsed_content)
    elif section_name == "skills":
        return process_skills(parsed_content)
    elif section_name == "work_experience":
        return process_work_experience(parsed_content)
    elif section_name == "education":
        return process_education(parsed_content)
    elif section_name == "projects":
        return process_projects(parsed_content)
    elif section_name == "awards":
        return process_awards(parsed_content)
    elif section_name == "publications":
        return process_publications(parsed_content)
    elif section_name == "certifications":
        # Handle certifications similar to awards
        return process_awards(parsed_content)
    else:
        # For unknown sections, just sanitize and return as is
        if isinstance(parsed_content, str):
            return sanitize_latex(parsed_content)
        elif isinstance(parsed_content, dict):
            # Try to extract a text field if available
            if "content" in parsed_content:
                return sanitize_latex(str(parsed_content["content"]))
            else:
                return sanitize_latex(str(parsed_content))
        elif isinstance(parsed_content, list):
            # For lists, create a simple itemized list
            result = ["\\begin{itemize}"]
            for item in parsed_content:
                if isinstance(item, dict) and "text" in item:
                    result.append(f"\\item {sanitize_latex(item['text'])}")
                else:
                    result.append(f"\\item {sanitize_latex(str(item))}")
            result.append("\\end{itemize}")
            return "\n".join(result)
        else:
            return sanitize_latex(str(parsed_content))
