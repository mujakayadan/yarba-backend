from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JobDetails(BaseModel):
    """Pydantic model for storing extracted job details."""

    description: str | None = Field(
        default=None,
        description="The HTML content of the job description, potentially including title and company.",
    )
    extraction_time: str | None = Field(
        default=None, description="Time taken for the extraction process."
    )
    extraction_metadata: dict[str, Any] | None = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)
