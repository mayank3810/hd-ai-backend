from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from app.schemas.PyObjectId import PyObjectId
from bson import ObjectId

class FilterPresetSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    operatorId: str = Field(..., alias="operator_id")
    userId: Optional[str] = Field(None, alias="user_id")  # Made optional for backward compatibility
    name: str
    description: Optional[str] = None
    propertyIds: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    isAllpropertiesSelected: Optional[bool] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class FilterPresetCreateSchema(BaseModel):
    operatorId: str = Field(..., alias="operator_id")
    name: str
    description: Optional[str] = None
    propertyIds: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    isAllpropertiesSelected: Optional[bool] = False

    class Config:
        populate_by_name = True

class FilterPresetUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    isAllpropertiesSelected: Optional[bool] = None

    class Config:
        populate_by_name = True
