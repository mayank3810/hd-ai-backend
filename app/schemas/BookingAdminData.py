from datetime import datetime
from pydantic import BaseModel,Field
from typing import Optional, List, Dict, Any
from bson import ObjectId
from app.schemas.PyObjectId import PyObjectId


class OperationsData(BaseModel):
    propertyId: str
    address: Optional[str] = None
    cityName: Optional[str] = None
    countryCode: Optional[str] = None
    propertyName: Optional[str] = None
    status: Optional[int] = None
    arrivvalsInFortyEightHours: Optional[int] = None
    departuresInFortyEightHours: Optional[int] = None
    guestMessages: Optional[int] = None
    bookingDotComMessages: Optional[int] = None
    



class HotelsPerformanceMetric(BaseModel):
    propertyId: str
    metrics: Optional[List[Dict[str, Any]]] = None

class SettingsData(BaseModel):
    propertyId: str
    geniusData: Optional[Dict] = None
    preferredDetails:Optional[Dict] = None
    minLosDetails:Optional[Dict] = None
    settingsGeoRates:Optional[Dict] = None  
    settingsMobileRates:Optional[Dict] = None
    propertyScoreDetails:Optional[Dict] = None


class GroupHomePage(BaseModel):
    operationsData: Optional[List[OperationsData]] = None
    hotelsPerformanceMetrics: Optional[List[HotelsPerformanceMetric]] = None
    settingsData: Optional[List[SettingsData]] = None


class BookingAdminData(BaseModel):
    operatorId: str
    groupHomePage: Optional[GroupHomePage] = None
    last_review_data: Optional[List[Dict]] = None
    adultChildConfig: Optional[List[Dict]] = None
    # policyGroupsData: Optional[List[Dict[str, Any]]] = None
    promotionsData: Optional[List[Dict[str, Any]]] = None
    ratePlansData: Optional[List[Dict[str, Any]]] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        use_enum_values = True
