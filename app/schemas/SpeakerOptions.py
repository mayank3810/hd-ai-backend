from typing import Optional

from pydantic import BaseModel, Field


class SpeakerOptionCreateSchema(BaseModel):
    """Body for POST catalog rows (topics, audiences, delivery modes, speaking formats)."""
    name: str = Field(..., min_length=1)
    slug: Optional[str] = Field(
        default=None,
        description="Optional; generated from name when omitted.",
    )
    type: str = Field(
        default="custom",
        description="e.g. system | custom",
    )
