from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Any


class OpportunitySchema(BaseModel):
    """Schema for extracted speaking opportunities from LLM."""

    link: str = ""
    event_name: str = ""
    location: str = ""
    topics: List[str] = Field(default_factory=list, alias="topics")
    date: Optional[str] = None  # Event date - when event is to happen
    speaking_format: str = "Not available"  # Workshop, Panel discussion, etc.
    delivery_mode: str = ""  # Virtual or in person
    target_audiences: List[str] = Field(default_factory=list)  # General Audience, managers, etc.
    metadata: dict = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class UrlScrapeCreateSchema(BaseModel):
    """Schema for creating a URL scrape job."""

    url: str
    topics: Optional[List[str]] = None  # Optional; allowed values from speaker_profile_chatbot.TOPICS
