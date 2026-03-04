from datetime import datetime
from pydantic import BaseModel,Field
from typing import Optional, List, Dict, Any
from bson import ObjectId
from app.schemas.PyObjectId import PyObjectId





class AirbnbProperty(BaseModel):
    propertyId: str
    name: str
    locality: str
    listingStatus: str
    pricingSettings: Optional[Dict[str, Any]] = None
    availabilitySettings: Optional[Dict[str, Any]] = None
    
    
    


class AirbnbAdminData(BaseModel):
    operatorId: str
    properties: Optional[List[AirbnbProperty]] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        use_enum_values = True
