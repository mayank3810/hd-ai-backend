from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from app.schemas.PyObjectId import PyObjectId

class PlatformStepsSchema(BaseModel):
    """Schema for platform steps with date and steps array - used for Booking, Airbnb, and Pricelabs"""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    steps: List[str] = Field(..., description="Array of platform step names")

class CreateOnboardingStatusSchema(BaseModel):
    """Schema for creating onboarding status"""
    operatorId: str = Field(...)
    bookingOnboarding: Optional[bool] = None
    airbnbOnboarding: Optional[bool] = None
    priceLbasOnboarding: Optional[bool] = None
    vrboOnboarding: Optional[bool] = None
    bookingSync: Optional[bool] = None
    airbnbSync: Optional[bool] = None
    priceLabsSync: Optional[bool] = None
    vrboSync: Optional[bool] = None
    bookingSteps: Optional[PlatformStepsSchema] = None
    airBnbSteps: Optional[PlatformStepsSchema] = None
    vrboSteps: Optional[str] = None
    priceLabsSteps: Optional[PlatformStepsSchema] = None

class OnboardingStatusSchema(BaseModel):
    """Schema for onboarding status response"""
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    userId: Optional[str] = Field(None, description="Optional user ID (deprecated - using operator_id only)")
    operatorId: str = Field(...)
    bookingOnboarding: Optional[bool] = None
    airbnbOnboarding: Optional[bool] = None
    priceLbasOnboarding: Optional[bool] = None
    vrboOnboarding: Optional[bool] = None
    bookingSync: Optional[bool] = None
    airbnbSync: Optional[bool] = None
    priceLabsSync: Optional[bool] = None
    vrboSync: Optional[bool] = None
    bookingSteps: Optional[PlatformStepsSchema] = None
    airBnbSteps: Optional[PlatformStepsSchema] = None
    vrboSteps: Optional[str] = None
    priceLabsSteps: Optional[PlatformStepsSchema] = None
    syncDate: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True
