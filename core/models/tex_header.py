"""TexHeader model for storing reusable LaTeX headers or snippets."""

from datetime import datetime
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field


class TexHeader(Document):
    """
    TexHeader model for storing reusable LaTeX headers or snippets.
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
        default_factory=datetime.utcnow, description="Creation timestamp."
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp."
    )

    @classmethod
    async def get_by_name(
        cls, name: str, category: str = "resume_section"
    ) -> Optional["TexHeader"]:
        """
        Get a TeX header by name and category.

        Args:
            name: Name of the TeX header to get
            category: Category of the TeX header

        Returns:
            The TeX header with the specified name and category, or None if not found
        """
        return await cls.find_one({"name": name, "category": category})

    @classmethod
    async def get_default(
        cls, name: str, category: str = "resume_section"
    ) -> Optional["TexHeader"]:
        """
        Get the default TeX header for a specific name and category.

        Args:
            name: Name of the TeX header to get the default for
            category: Category of the TeX header

        Returns:
            The default TeX header for the specified name and category, or None if not found
        """
        return await cls.find_one(
            {"name": name, "category": category, "is_default": True}
        )

    model_config = {
        "validate_assignment": True,
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "collection": "tex_headers",
    }

    class Settings:
        """Beanie document settings."""

        name = "tex_headers"
        use_state_management = True
        indexes = ["category"]
        bson_encoders = {
            datetime: lambda x: x,
        }
