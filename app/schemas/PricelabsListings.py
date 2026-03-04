from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId
from app.schemas.PyObjectId import PyObjectId
from datetime import datetime

class PricelabsListing(BaseModel):
    listingId:Optional[str]=None
    latitude:Optional[float]=None
    longitude:Optional[float]=None
    name:Optional[str]=None
    country:Optional[str]=None
    cityName:Optional[str]=None
    status:Optional[str]=Field(default="PENDING")
    syncStatus:Optional[bool]=Field(default=False)

class PricelabsListings(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    operatorId: Optional[str] = None
    pricelabsListings:Optional[list[PricelabsListing]] = None
    createdAt:Optional[datetime] = Field(default_factory=datetime.utcnow)
    updatedAt:Optional[datetime] = Field(default_factory=datetime.utcnow)
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        populate_by_name = True
        use_enum_values = True