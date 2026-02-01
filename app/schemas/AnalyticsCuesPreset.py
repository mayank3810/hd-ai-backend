from datetime import datetime, date
from pydantic import BaseModel, Field
from typing import Optional
from app.schemas.PyObjectId import PyObjectId
from bson import ObjectId

class AnalyticsCuesPresetSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    operatorId: str = Field(..., alias="operator_id")
    presetName: str = Field(..., alias="preset_name")
    startDate: str = Field(..., alias="start_date")
    endDate: str = Field(..., alias="end_date")
    createdAt: datetime = Field(default_factory=datetime.utcnow, alias="created_at")

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class AnalyticsCuesPresetCreateSchema(BaseModel):
    operatorId: str = Field(..., alias="operator_id")
    presetName: str = Field(..., alias="preset_name")
    startDate: str = Field(..., alias="start_date")
    endDate: str = Field(..., alias="end_date")

    class Config:
        populate_by_name = True

