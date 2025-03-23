"""TexTemplate model for storing LaTeX document templates."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from beanie import Document
from pydantic import Field


class TexTemplate(Document):
    """
    TexTemplate model for storing LaTeX document templates.
    This model holds complete LaTeX document templates that can be used
    to generate resumes, cover letters, and other documents.
    """

    name: str = Field(description="Name of the template for easy identification.")
    content: str = Field(description="LaTeX code for the document template.")
    type: str = Field(
        default="resume",
        description="Type of template (e.g., resume, cover_letter).",
    )
    is_default: bool = Field(
        default=False, description="Indicates if this is a default template."
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp.",
    )

    model_config = {
        "validate_assignment": True,
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "collection": "tex_templates",
    }

    class Settings:
        """Beanie document settings."""

        name = "tex_templates"
        use_state_management = True
        indexes = ["type"]
        bson_encoders = {
            datetime: lambda x: x,
        }

    def to_latex(self, **kwargs: Any) -> str:
        """
        Format the template content with the provided parameters.

        Args:
            **kwargs: Key-value pairs to use for template formatting

        Returns:
            str: Formatted LaTeX content

        Raises:
            ValueError: If formatting fails
            KeyError: If a required template parameter is missing
        """
        try:
            return self.content.format(**kwargs)
        except KeyError as e:
            raise KeyError(f"Missing required template parameter: {e}")
        except Exception as e:
            raise ValueError(f"Error formatting template: {e}")
