from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId
from app.schemas.PyObjectId import PyObjectId

class CreateQueueStatusSchema(BaseModel):
    """Schema for creating/updating queue status"""
    operator_id: str = Field(..., description="ID of the operator")
    booking_id: Optional[str] = Field(None, description="Booking.com property ID")
    airbnb_id: Optional[str] = Field(None, description="Airbnb property ID")
    vrbo_id: Optional[str] = Field(None, description="VRBO property ID")
    pricelabs_id: Optional[str] = Field(None, description="Pricelabs property ID")
    status: Optional[str] = Field(None, description="Current status of the queue entry")
    error_message: Optional[str] = Field(None, description="Error message if status is error")

class QueueStatusSchema(BaseModel):
    """Schema for queue status response"""
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    operator_id: str = Field(..., description="ID of the operator")
    booking_id: Optional[str] = Field(None, description="Booking.com property ID")
    airbnb_id: Optional[str] = Field(None, description="Airbnb property ID")
    vrbo_id: Optional[str] = Field(None, description="VRBO property ID")
    pricelabs_id: Optional[str] = Field(None, description="Pricelabs property ID")
    status: str = Field(default="pending", description="Current status of the queue entry")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the entry was created")
    started_at: Optional[datetime] = Field(None, description="When processing started")
    completed_at: Optional[datetime] = Field(None, description="When processing completed")
    error_message: Optional[str] = Field(None, description="Error message if status is error")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    
    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True
