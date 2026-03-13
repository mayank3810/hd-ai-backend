from pydantic import BaseModel


class GoogleQueryCreateSchema(BaseModel):
    """Schema for submitting a Google search query to be processed in background."""

    query: str

