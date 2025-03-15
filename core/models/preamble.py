"""Preamble model for storing LaTeX preamble content."""

from datetime import datetime
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field


class Preamble(Document):
    """
    Preamble model for storing LaTeX preamble content.
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
        default_factory=datetime.utcnow, description="Creation timestamp."
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp."
    )

    @classmethod
    async def get_default(cls, preamble_type: str) -> Optional["Preamble"]:
        """
        Get the default preamble for a specific type.

        Args:
            preamble_type: Type of preamble to get the default for

        Returns:
            The default preamble for the specified type, or None if not found
        """
        return await cls.find_one({"type": preamble_type, "is_default": True})

    model_config = {
        "validate_assignment": True,
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "collection": "preambles",
    }

    class Settings:
        """Beanie document settings."""

        name = "preambles"
        use_state_management = True
        bson_encoders = {
            datetime: lambda x: x,
        }
