from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class JobDetails(BaseModel):
    """Pydantic model for storing extracted job details."""

    description: Optional[str] = Field(
        default=None,
        description="The HTML content of the job description, potentially including title and company.",
    )
    extraction_time: Optional[str] = Field(
        default=None, description="Time taken for the extraction process."
    )
    extraction_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        """Allows the model to be created from arbitrary class instances (ORM mode)"""

        from_attributes = True
