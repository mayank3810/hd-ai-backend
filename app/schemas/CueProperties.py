from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime, timezone
from bson import ObjectId
from app.schemas.PyObjectId import PyObjectId


class AssignedUser(BaseModel):
    name: Optional[str] = None
    userId: Optional[str] = None


class Note(BaseModel):
    note: Optional[str] = None
    userId: Optional[str] = None
    userName: Optional[str] = None
    userEmail: Optional[str] = None
    userCompleteName: Optional[str] = None
    createdAt: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), exclude=True)

class Pickup(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    
class CuePropertySchema(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    operatorId: Optional[str] = None
    propertyId: Optional[str] = None
    deploymentCueId: Optional[str] = None
    deploymentCueName: Optional[str] = None
    pickup: Optional[Pickup] = None
    assignedTo: Optional[AssignedUser] = None
    status: Optional[str] = None
    notes: Optional[List[Note]] = None
    createdAt: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        populate_by_name = True
        use_enum_values = True

class CuePropertyCreateSchema(BaseModel):
    operatorId: Optional[str] = None
    propertyId: Optional[str] = None
    deploymentCueId: Optional[str] = None
    deploymentCueName: Optional[str] = None
    pickup: Optional[Pickup] = None
    assignedTo: Optional[AssignedUser] = None
    status: Optional[str] = None
    notes: Optional[List[Note]] = None


class CuePropertyUpdateSchema(BaseModel):
    deploymentCueId: Optional[str] = None
    deploymentCueName: Optional[str] = None
    pickup: Optional[Pickup] = None
    assignedTo: Optional[AssignedUser] = None
    status: Optional[str] = None
    notes: Optional[List[Note]] = None

