from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Union, Dict, Any
from app.schemas.PyObjectId import PyObjectId
from bson import ObjectId


class CompetitorPhoto(BaseModel):
    photoId: str
    url: str
    sequence: int
    hasCaption: bool
    caption: Optional[str] = None
    type: str

    class Config:
        populate_by_name = True


class CompetitorPropertySchema(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id", exclude=True)
    propertyName:Optional[str]=None
    operatorId: str
    bookingId: Optional[str] = None
    airbnbId: Optional[str] = None
    vrboId: Optional[str] = None
    bookingLink: Optional[str] = None
    airbnbLink: Optional[str] = None
    vrboLink: Optional[str] = None
    status: str = Field(default="pending")
    propertyBookingPhotos: Optional[Union[List[dict], Dict[str, Any]]] = None
    propertyVrboPhotos: Optional[Union[List[dict], Dict[str, Any]]] = None
    propertyAirbnbPhotos: Optional[Union[List[dict], Dict[str, Any]]] = None
    reviewsAirbnb: Optional[Union[List[dict], Dict[str, Any]]] = None
    reviewsVrbo: Optional[Union[List[dict], Dict[str, Any]]] = None
    reviewsBooking: Optional[Union[List[dict], Dict[str, Any]]] = None
    amenitiesAirbnb: Optional[Union[List[dict], Dict[str, Any]]] = None
    amenitiesVrbo: Optional[Union[List[dict], Dict[str, Any]]] = None
    amenitiesBooking: Optional[Union[List[dict], Dict[str, Any]]] = None
    hotelPoliciesAirbnb: Optional[Union[List[dict], Dict[str, Any]]] = None
    hotelPoliciesVrbo: Optional[Union[List[dict], Dict[str, Any]]] = None
    hotelPoliciesBooking: Optional[Union[List[dict], Dict[str, Any]]] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: Optional[datetime] = None

    @validator('airbnbLink', 'bookingLink', 'vrboLink', pre=True)
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class CompetitorPropertyCreateSchema(BaseModel):
    operatorId: str
    bookingId: Optional[str] = None
    airbnbId: Optional[str] = None
    vrboId: Optional[str] = None
    bookingLink: Optional[str] = None
    airbnbLink: Optional[str] = None
    vrboLink: Optional[str] = None
    status: str = Field(default="pending")

    @validator('airbnbLink', 'bookingLink', 'vrboLink', pre=True)
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v

    class Config:
        populate_by_name = True


class CompetitorPropertyUpdateSchema(BaseModel):
    operatorId: Optional[str] = None
    bookingId: Optional[str] = None
    airbnbId: Optional[str] = None
    vrboId: Optional[str] = None
    bookingLink: Optional[str] = None
    airbnbLink: Optional[str] = None
    vrboLink: Optional[str] = None
    status: Optional[str] = None
    propertyBookingPhotos: Optional[Union[List[dict], Dict[str, Any]]] = None
    propertyVrboPhotos: Optional[Union[List[dict], Dict[str, Any]]] = None
    propertyAirbnbPhotos: Optional[Union[List[dict], Dict[str, Any]]] = None
    reviewsAirbnb: Optional[Union[List[dict], Dict[str, Any]]] = None
    reviewsVrbo: Optional[Union[List[dict], Dict[str, Any]]] = None
    reviewsBooking: Optional[Union[List[dict], Dict[str, Any]]] = None
    amenitiesAirbnb: Optional[Union[List[dict], Dict[str, Any]]] = None
    amenitiesVrbo: Optional[Union[List[dict], Dict[str, Any]]] = None
    amenitiesBooking: Optional[Union[List[dict], Dict[str, Any]]] = None
    hotelPoliciesAirbnb: Optional[Union[List[dict], Dict[str, Any]]] = None
    hotelPoliciesVrbo: Optional[Union[List[dict], Dict[str, Any]]] = None
    hotelPoliciesBooking: Optional[Union[List[dict], Dict[str, Any]]] = None
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    @validator('airbnbLink', 'bookingLink', 'vrboLink', pre=True)
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v

    class Config:
        populate_by_name = True
