import logging
import re

from bs4 import BeautifulSoup
from markdownify import markdownify as md

logger = logging.getLogger(__name__)


def html_to_markdown(html_content: str) -> str:
    """
    Converts HTML content to Markdown and cleans it up.

    Args:
        html_content: The HTML string to convert.

    Returns:
        The cleaned Markdown representation of the HTML.
    """
    if not html_content:
        return ""

    text_content: str
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        text_content = md(str(soup))
    except Exception as e:
        logger.error(f"Error converting HTML to Markdown: {e}")
        # Fallback to stripping tags if Markdown conversion fails
        text_content = strip_html_tags(html_content)

    text_content = re.sub(r"show more", "", text_content, flags=re.IGNORECASE)
    text_content = re.sub(r"show less", "", text_content, flags=re.IGNORECASE)

    text_content = text_content.strip()
    text_content = re.sub(r"\n\s*\n", "\n", text_content)

    return text_content


def strip_html_tags(html_content: str) -> str:
    """
    Removes all HTML tags from a string, leaving only the text content.

    Args:
        html_content: The HTML string.

    Returns:
        The text content without HTML tags.
    """
    if not html_content:
        return ""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return text
    except Exception as e:
        logger.error(f"Error stripping HTML tags: {e}")
        # Return basic stripped text as a last resort or empty
        return ""
