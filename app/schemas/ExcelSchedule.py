from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from app.schemas.PyObjectId import PyObjectId
from bson import ObjectId

class ExcelScheduleSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    operatorId: str = Field(..., alias="operator_id")
    startDate: str = Field(..., alias="start_date")
    endDate: str = Field(..., alias="end_date")
    status: str = Field(default="pending")
    url: Optional[str] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow, alias="created_at")
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class ExcelScheduleCreateSchema(BaseModel):
    operatorId: str = Field(..., alias="operator_id")
    startDate: str = Field(..., alias="start_date")
    endDate: str = Field(..., alias="end_date")

    class Config:
        populate_by_name = True

