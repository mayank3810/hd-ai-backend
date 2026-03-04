from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from app.schemas.PyObjectId import PyObjectId
from bson import ObjectId

class ImageCaptionViewSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    imageUrl: str
    caption: str
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class ImageCaptionCreateSchema(BaseModel):
    imageUrl: str
    caption: str

    class Config:
        populate_by_name = True

class ImageCaptionUpdateSchema(BaseModel):
    caption: str
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
