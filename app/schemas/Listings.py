from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union, Literal
from datetime import datetime
from enum import Enum
from app.schemas.PyObjectId import PyObjectId
from bson import ObjectId





class PropertyType(str, Enum):
    HOTELS="hotels"
    HOTEL = "hotel"
    APARTMENT = "apartment"
    HOUSE = "house"
    VILLA = "villa"
    GUESTHOUSE = "guesthouse"
    HOSTEL = "hostel"
    RESORT = "resort"
    OTHER = "other"


class RoomType(str, Enum):
    ENTIRE_PLACE = "entire_place"
    PRIVATE_ROOM = "private_room"
    SHARED_ROOM = "shared_room"
    HOTEL_ROOM = "hotel_room"


class CurrencyAmount(BaseModel):
    amount: float
    currency: str
    formatted_amount: Optional[str] = None


class Location(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    district: Optional[str] = None
    zip_code: Optional[str] = None


class Photo(BaseModel):
    id: Optional[Union[str, int]] = None  # Allow both string and integer IDs
    url: str
    caption: Optional[str] = None
    accessibility_label: Optional[str] = None


# class Amenity(BaseModel):
#     id: Optional[Union[str, int]] = None  # Allow both string and integer IDs
#     name: str
#     category: Optional[str] = None
#     icon: Optional[str] = None
#     available: bool = True

class Amenity(BaseModel):
    id: Optional[Union[str, int]] = None  # Allow both string and integer IDs
    name: Optional[str] = None  # For Booking.com compatibility
    title: Optional[str] = None  # For Airbnb (primary field)
    subtitle: Optional[str] = None  # For Airbnb
    category: Optional[str] = None
    icon: Optional[str] = None
    available: Optional[bool] = True
    image: Optional[str] = None  # For Airbnb
    images: Optional[List[Union[str, Dict[str, Any]]]] = None  # For Airbnb
    # Allow additional fields for flexibility
    class Config:
        extra = "allow"  # Allow extra fields that aren't explicitly defined




class ReviewRating(BaseModel):
    overall_rating: Optional[float] = None
    review_count: Optional[int] = None
    cleanliness: Optional[float] = None
    accuracy: Optional[float] = None
    communication: Optional[float] = None
    location: Optional[float] = None
    check_in: Optional[float] = None
    value: Optional[float] = None
    last_review: Optional[Dict[str, Any]] = None


class PriceBreakdown(BaseModel):
    base_price: Optional[CurrencyAmount] = None
    total_price: Optional[CurrencyAmount] = None
    taxes_and_fees: Optional[CurrencyAmount] = None
    cleaning_fee: Optional[CurrencyAmount] = None
    service_fee: Optional[CurrencyAmount] = None


class Host(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    profile_photo_url: Optional[str] = None
    is_superhost: Optional[bool] = None


class CancellationPolicy(BaseModel):
    type: Optional[str] = None
    description: Optional[str] = None
    free_cancellation_until: Optional[str] = None


# Base listing schema
class BaseListing(BaseModel):
    # Core identification    platform: str
    title: str
    description: Optional[str] = None
    
    # Property details
    property_type: PropertyType
    room_type: Optional[RoomType] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    beds: Optional[int] = None
    max_guests: Optional[int] = None
    
    # Location
    location: Location
    
    # Pricing
    pricing: Optional[PriceBreakdown] = None
        
    # Media
    photos: List[Photo] = Field(default_factory=list)
    
    # Amenities
    amenities: Union[List[Amenity], Dict[str, Any], Any] = Field(default_factory=list)
    
    # Reviews
    reviews: Optional[ReviewRating] = None
    
    # Host information
    host: Optional[Host] = None
    
    # Policies
    cancellation_policy: Optional[CancellationPolicy] = None
    house_rules: List[str] = Field(default_factory=list)
        # Additional data
    raw_data: Optional[Dict[str, Any]] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        # Allow extra fields and be flexible with amenities structure
        extra = "allow"
        # Don't validate assignment to allow dict/list flexibility
        validate_assignment = False




# Booking.com specific extensions
class BookingSpecific(BaseModel):
    hotel_id: Optional[int] = None
    ufi: Optional[int] = None
    accommodation_type_name: Optional[str] = None
    hotel_class: Optional[int] = None
    is_genius_deal: Optional[bool] = None
    breakfast_included: Optional[bool] = None
    free_cancellation: Optional[bool] = None
    payment_terms: Optional[Dict[str, Any]] = None
    room_details: Optional[Dict[str, Any]] = None
    facilities_block: Optional[Dict[str, Any]] = None


# Airbnb specific extensions
class AirbnbSpecific(BaseModel):
    property_id: Optional[str] = None
    home_tier: Optional[int] = None
    instant_book: Optional[bool] = None
    allows_children: Optional[bool] = None
    allows_infants: Optional[bool] = None
    allows_pets: Optional[bool] = None
    check_in_instructions: Optional[str] = None
    house_manual: Optional[str] = None


# VRBO specific extensions
class VrboSpecific(BaseModel):
    property_id: Optional[str] = None
    url: Optional[str] = None
    is_dead_link: Optional[bool] = None
    coordinate_accuracy: Optional[str] = None
    nightly_rate: Optional[float] = None
    sq_ft: Optional[float] = None
    state: Optional[str] = None
    headline_text: Optional[str] = None
    category: Optional[str] = None
    sections: Optional[List[Dict[str, Any]]] = None
    host_info: Optional[Dict[str, Any]] = None

# Complete listing schemas
class BookingListing(BaseListing):
    booking_details: BookingSpecific


class AirbnbListing(BaseListing):
    airbnb_details: AirbnbSpecific


class VrboListing(BaseListing):
    vrbo_details: VrboSpecific


# Union type for all listings
# Listing = Union[BookingListing, AirbnbListing, VrboListing]


class Listing(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    operatorId: Optional[str] = None
    bookingId: Optional[str] = None
    airbnbId: Optional[str] = None
    vrboId: Optional[str] = None    
    bookingListing: Optional[BookingListing] = None
    airbnbListing: Optional[AirbnbListing] = None
    vrboListing: Optional[VrboListing] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        populate_by_name = True
        use_enum_values = True



class CreateListing(BaseModel):
    operatorId: Optional[str] = None
    bookingId: Optional[str] = None
    airbnbId: Optional[str] = None
    vrboId: Optional[str] = None
    pricelabsId: Optional[str] = None