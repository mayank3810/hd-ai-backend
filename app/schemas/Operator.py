from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from bson import ObjectId
from app.schemas.PyObjectId import PyObjectId


ConnectionStatus = Literal["PENDING", "CONNECTED", "FAILED"]


class PriceLabsConfig(BaseModel):
    userName: Optional[str] = None
    password: Optional[str] = None
    apiKey: Optional[str] = None
    status: Optional[ConnectionStatus] = "PENDING"
    cookies: Optional[List[Dict[str, Any]]] = None


class AirbnbConfig(BaseModel):
    userName: Optional[str] = None
    password: Optional[str] = None
    apiKey: Optional[str] = None
    status: Optional[ConnectionStatus] = "PENDING"
    cookies: Optional[List[Dict[str, Any]]] = None


class VrboConfig(BaseModel):
    userName: Optional[str] = None
    password: Optional[str] = None
    apiKey: Optional[str] = None
    status: Optional[ConnectionStatus] = "PENDING"
    cookies: Optional[List[Dict[str, Any]]] = None


class BookingConfig(BaseModel):
    userName: Optional[str] = None
    password: Optional[str] = None
    apiKey: Optional[str] = None
    status: Optional[ConnectionStatus] = "PENDING"
    cookies: Optional[List[Dict[str, Any]]] = None
    session_id:Optional[str] = None
    account_id:Optional[int] = None




class Operator(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    name: str
    userId: List[str]
    priceLabs: Optional[PriceLabsConfig] = None
    booking: Optional[BookingConfig] = None
    airbnb: Optional[AirbnbConfig] = None
    vrbo: Optional[VrboConfig] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        use_enum_values = True
        
        
class CreateOperator(BaseModel):
    name: str
    priceLabs: Optional[PriceLabsConfig] = None
    booking: Optional[BookingConfig] = None
    airbnb: Optional[AirbnbConfig] = None
    vrbo: Optional[VrboConfig] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        use_enum_values = True
        
        
class OperatorUpdate(BaseModel):
    name: Optional[str] = None
    userId: Optional[List[str]] = None
    priceLabs: Optional[PriceLabsConfig] = None
    booking: Optional[BookingConfig] = None
    airbnb: Optional[AirbnbConfig] = None
    vrbo: Optional[VrboConfig] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        use_enum_values = True

    

    