from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Any, Dict, Optional, Union, List
from app.schemas.PyObjectId import PyObjectId
from bson import ObjectId
from enum import Enum

class PropertyType(str, Enum):
    HOTELS = "hotels"
    HOTEL = "hotel"
    APARTMENT = "apartment"
    HOUSE = "house"
    VILLA = "villa"
    GUESTHOUSE = "guesthouse"
    HOSTEL = "hostel"
    RESORT = "resort"
    OTHER = "other"

class PropertyStatus(str, Enum):
    PENDING = "pending"
    SCRAPING_IN_PROGRESS = "scraping_in_progress"
    ERROR_IN_SCRAPING = "error_in_scraping"
    MAPPING_IN_PROGRESS = "mapping_in_progress"
    ERROR_IN_MAPPING = "error_in_mapping"
    COMPLETED = "completed"

class Photo(BaseModel):
    id: Optional[Union[str, int]] = None  # Allow both string and integer IDs
    url: str
    caption: Optional[str] = None
    accessibility_label: Optional[str] = None
    source: Optional[str] = None  # "booking", "airbnb", "vrbo", etc.

class PhotosBySource(BaseModel):
    booking: Optional[List[Photo]] = None
    airbnb: Optional[List[Photo]] = None
    vrbo: Optional[List[Photo]] = None

class OccupancySchema(BaseModel):
    seven_days: Optional[float] = Field(None, alias="7_days")
    thirty_days: Optional[float] = Field(None, alias="30_days")
    TM: Optional[float]=None
    NM: Optional[float]=None

class ADRSchema(BaseModel):
    TM:Optional[float]=None
    NM: Optional[float]=None

class RevPARSchema(BaseModel):
    TM: Optional[float]=None
    NM: Optional[float]=None

class STLYVarSchema(BaseModel):
    Occ: Optional[float]=None 
    ADR: Optional[float]=None
    RevPAR: Optional[float]=None

class STLMVarSchema(BaseModel):
    Occ: Optional[float]=None
    ADR: Optional[float]=None
    RevPAR: Optional[float]=None

class PickUpOccSchema(BaseModel):
    seven_Days: Optional[float] = Field(None, alias="7_Days")
    fourteen_Days: Optional[float] = Field(None, alias="14_Days")
    thirty_Days: Optional[float] = Field(None, alias="30_Days")

class MPISchema(BaseModel):
    TM: Optional[float] = None  # This Month from thisMonthDashboard
    NM: Optional[float] = None  # Next Month from nextMonthDashboard  
    LYTM: Optional[float] = None  # Last Year This Month from lastYearThisMonthDashboard

class LastMinuteDiscountSchema(BaseModel):
    __typename: Optional[str] = None
    leadDays: Optional[int] = None
    priceChange: Optional[int] = None

class BookingComSchema(BaseModel):
    Genius: Optional[str] = None
    Mobile: Optional[str] = None
    Pref: Optional[str] = None
    Weekly: Optional[str] = None
    Monthly: Optional[str] = None
    LM_Disc: Optional[LastMinuteDiscountSchema] = None
    Discounts: Optional[List[Dict]] = None

class AirbnbSchema(BaseModel):
    Weekly: Optional[str] = None
    Monthly: Optional[str] = None
    LM_Disc: Optional[LastMinuteDiscountSchema] = None

class VRBOSchema(BaseModel):
    Weekly: str
    Monthly: str

class CancellationPolicySchema(BaseModel):
    type: Optional[str] = None
    description: Optional[str] = None
    free_cancellation_until: Optional[str] = None

class CXLPolicySchema(BaseModel):
    Booking: Optional[list] = None
    Airbnb: Optional[CancellationPolicySchema] = None
    VRBO: Optional[CancellationPolicySchema] = None

class BookingRoomConfigSchema(BaseModel):
    id: Optional[str] = None
    max_guests: Optional[str] = None
    max_adults: Optional[str] = None
    max_children: Optional[str] = None
    max_infants: Optional[str] = None
    room_count: Optional[str] = None

class AirbnbRoomConfigSchema(BaseModel):
    max_guests: Optional[int] = None

class VRBORoomConfigSchema(BaseModel):
    # VRBO will have different parameters - to be defined later
    pass

class AdultChildConfigSchema(BaseModel):
    Booking: Optional[BookingRoomConfigSchema] = None
    Airbnb: Optional[AirbnbRoomConfigSchema] = None
    VRBO: Optional[VRBORoomConfigSchema] = None

class ReviewDetailSchema(BaseModel):
    Last_Rev_Score: Optional[Any] = None
    Rev_Score: Optional[Any]=None
    Total_Rev: Optional[Any]=None
    Last_Review_Date: Optional[Any]=None

class ReviewsSchema(BaseModel):
    Booking: Optional[ReviewDetailSchema] = None
    Airbnb: Optional[ReviewDetailSchema] = None
    VRBO: Optional[ReviewDetailSchema] = None

class AmenitySchema(BaseModel):
    name: str
    category: Optional[str] = None
    icon: Optional[str] = None

class AmenitiesSchema(BaseModel):
    Booking: Optional[List[AmenitySchema]] = None
    Airbnb: Optional[List[AmenitySchema]] = None
    VRBO: Optional[List[AmenitySchema]] = None

# Flattened URL fields - no longer need separate schema classes

class PropertySchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    operator_id: str
    listing_id: Optional[str] = None  # Reference to the original listing entry
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    status: PropertyStatus = Field(default=PropertyStatus.PENDING, description="Overall status of scraping and mapping process")
    Pricelabs_SyncStatus: Optional[bool] = None
    Listing_Name: Optional[str] = None
    Area: Optional[str] = None
    Room_Type: Optional[str] = None
    Property_Type: Optional[PropertyType] = None
    Photos: Optional[PhotosBySource] = None
    Occupancy: Optional[OccupancySchema] = None
    ADR: Optional[ADRSchema] = None
    RevPAR: Optional[RevPARSchema] = None
    MPI: Optional[MPISchema] = None
    STLY_Var: Optional[STLYVarSchema] = None
    STLM_Var: Optional[STLMVarSchema] = None
    Pick_Up_Occ: Optional[PickUpOccSchema] = None
    Min_Rate_Threshold: Optional[str] = None
    BookingCom: Optional[BookingComSchema] = None
    Airbnb: Optional[AirbnbSchema] = None
    VRBO: Optional[VRBOSchema] = None
    CXL_Policy: Optional[CXLPolicySchema] = None
    Adult_Child_Config: Optional[AdultChildConfigSchema] = None
    Reviews: Optional[ReviewsSchema] = None
    Amenities: Optional[AmenitiesSchema] = None
    BookingId: Optional[str] = None
    BookingUrl: Optional[str] = None
    AirbnbId: Optional[str] = None
    AirbnbUrl: Optional[str] = None
    VRBOId: Optional[str] = None
    VRBOUrl: Optional[str] = None
    PricelabsId: Optional[str] = None
    PricelabsUrl: Optional[str] = None
    competitorIds: Optional[List[str]] = None

    @validator('BookingUrl', 'AirbnbUrl', 'VRBOUrl', 'PricelabsUrl', pre=True)
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v

    @validator('VRBOId')
    def check_at_least_one(cls, v, values):
        if not any([values.get('BookingId'), values.get('AirbnbId'), v]):
            raise ValueError('At least one property ID (BookingId, AirbnbId, or VRBOId) must be provided')
        return v

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        
class MinimalPropertyCreateSchema(BaseModel):
    operator_id: str
    # Flattened URL fields
    BookingId: Optional[str] = None
    BookingUrl: Optional[str] = None
    AirbnbId: Optional[str] = None
    AirbnbUrl: Optional[str] = None
    VRBOId: Optional[str] = None
    VRBOUrl: Optional[str] = None
    PricelabsId: Optional[str] = None
    PricelabsUrl: Optional[str] = None

    @validator('VRBOId')
    def check_at_least_one(cls, v, values):
        if not any([values.get('BookingId'), values.get('AirbnbId'), v]):
            raise ValueError('At least one property ID (BookingId, AirbnbId, or VRBOId) must be provided')
        return v

class PropertyCreateSchema(BaseModel):
    operator_id: str
    listing_id: Optional[str] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    status: PropertyStatus = Field(default=PropertyStatus.PENDING, description="Overall status of scraping and mapping process")
    Pricelabs_SyncStatus: Optional[bool] = None
    Listing_Name: Optional[str] = None
    Area: Optional[str] = None
    Room_Type: Optional[str] = None
    Property_Type: Optional[PropertyType] = None
    Photos: Optional[PhotosBySource] = None
    Occupancy: Optional[OccupancySchema] = None
    ADR: Optional[ADRSchema] = None
    RevPAR: Optional[RevPARSchema] = None
    MPI: Optional[MPISchema] = None
    STLY_Var: Optional[STLYVarSchema] = None
    STLM_Var: Optional[STLMVarSchema] = None
    Pick_Up_Occ: Optional[PickUpOccSchema] = None
    Min_Rate_Threshold: Optional[str] = None
    BookingCom: Optional[BookingComSchema] = None
    Airbnb: Optional[AirbnbSchema] = None
    VRBO: Optional[VRBOSchema] = None
    CXL_Policy: Optional[CXLPolicySchema] = None
    Adult_Child_Config: Optional[AdultChildConfigSchema] = None
    Reviews: Optional[ReviewsSchema] = None
    Amenities: Optional[AmenitiesSchema] = None
    
    # Flattened URL fields
    BookingId: Optional[str] = None
    BookingUrl: Optional[str] = None
    AirbnbId: Optional[str] = None
    AirbnbUrl: Optional[str] = None
    VRBOId: Optional[str] = None
    VRBOUrl: Optional[str] = None
    PricelabsId: Optional[str] = None
    PricelabsUrl: Optional[str] = None
    competitorIds: Optional[List[str]] = None

    @validator('VRBOId')
    def check_at_least_one(cls, v, values):
        if not any([values.get('BookingId'), values.get('AirbnbId'), v]):
            raise ValueError('At least one property ID (BookingId, AirbnbId, or VRBOId) must be provided')
        return v

class PropertyUpdateSchema(BaseModel):
    operator_id: str
    BookingId: Optional[str] = None
    BookingUrl: Optional[str] = None
    AirbnbId: Optional[str] = None
    AirbnbUrl: Optional[str] = None
    VRBOId: Optional[str] = None
    VRBOUrl: Optional[str] = None
    PricelabsId: Optional[str] = None
    PricelabsUrl: Optional[str] = None
    # Flattened URL fields
    competitorIds: Optional[List[str]] = None