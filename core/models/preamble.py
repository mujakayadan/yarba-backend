"""Preamble model for storing LaTeX preamble content."""

from datetime import UTC, datetime

from beanie import Document
from pydantic import Field


class Preamble(Document):
    """Preamble model for storing LaTeX preamble content.
    This model holds the LaTeX code that defines the document's overall structure,
    including package imports, page settings, and custom commands.
    """

    name: str = Field(description="Name of the preamble for easy identification.")
    type: str = Field(
        default="resume_preamble",
        description="Type of preamble (e.g., resume_preamble, cover_letter_preamble).",
    )
    content: str = Field(description="LaTeX code for the preamble.")
    is_default: bool = Field(
        default=False, description="Indicates if this is a default preamble."
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp.",
    )

    model_config = {
        "validate_assignment": True,
        "json_encoders": {datetime: lambda v: v.isoformat()},
    }

    class Settings:
        """Beanie document settings."""

        name = "preambles"
        use_state_management = True
        bson_encoders = {
            datetime: lambda dt: (dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt),
        }
