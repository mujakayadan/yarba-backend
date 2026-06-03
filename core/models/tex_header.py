"""TexHeader model for storing reusable LaTeX headers or snippets."""

from datetime import UTC, datetime

from beanie import Document
from pydantic import Field

from core.models.document_config import BSON_DATETIME_ENCODERS, DOCUMENT_MODEL_CONFIG


class TexHeader(Document):
    """TexHeader model for storing reusable LaTeX headers or snippets.
    This model holds LaTeX code snippets that can be inserted into specific
    sections of a LaTeX document, like resume sections (e.g., skills, projects).
    """

    name: str = Field(description="Name of the header for easy identification.")
    content: str = Field(description="LaTeX code for the header snippet.")
    category: str = Field(
        default="resume_section",
        description="Category of the header (e.g., resume_section, cover_letter_section).",
    )
    is_default: bool = Field(
        default=False, description="Indicates if this is a default header."
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp.",
    )

    model_config = DOCUMENT_MODEL_CONFIG

    class Settings:
        """Beanie document settings."""

        name = "tex_headers"
        use_state_management = True
        indexes = ["category"]
        bson_encoders = BSON_DATETIME_ENCODERS
