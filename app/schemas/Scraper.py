from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from app.schemas.PyObjectId import PyObjectId
from bson import ObjectId


class ScraperSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    sourceName: str = Field(..., alias="sourceName")
    url: str
    description: Optional[str] = None
    userId: str = Field(..., alias="user_id")
    opportunities: list = Field(default_factory=list)
    status: str = Field(default="PENDING_SCRAPING")
    error: Optional[str] = None
    maxDepth: Optional[int] = None
    maxUrls: Optional[int] = None
    scrapedUrlCount: Optional[int] = None
    scrapedName: Optional[str] = None
    scrapedDescription: Optional[str] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        extra = "ignore"


class ScraperCreateSchema(BaseModel):
    sourceName: str = Field(..., alias="sourceName")
    url: str
    description: Optional[str] = None
    opportunities: list = Field(default_factory=list)

    class Config:
        populate_by_name = True


class CrawlForOpportunitiesRequest(BaseModel):
    """Request body for scrape-and-extract-speaking-opportunities API. Uses RapidAPI scraper (single URL)."""
    url: str


class ScraperUpdateSchema(BaseModel):
    sourceName: Optional[str] = Field(None, alias="sourceName")
    url: Optional[str] = None
    description: Optional[str] = None
    opportunities: Optional[list] = None
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
