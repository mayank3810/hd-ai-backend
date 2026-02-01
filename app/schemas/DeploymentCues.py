from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
from app.schemas.PyObjectId import PyObjectId
from bson import ObjectId
from enum import Enum

class DeploymentCueStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class AssignedUser(BaseModel):
    name: str
    userId: str

class DeploymentCueNote(BaseModel):
    note: str
    userId: str
    userName: str
    userEmail: str
    userCompleteName: str
    createdAt: datetime = Field(default_factory=datetime.utcnow)

class PickupItem(BaseModel):
    name: str
    description: str

class DeploymentCuePropertiesSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    operatorId: str
    name: str
    tag: str
    description1: str
    description2: str
    pickups: List[PickupItem] = []
    createdAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class DeploymentCueCreateSchema(BaseModel):
    operatorId: str
    name: str
    tag: str
    description1: str
    description2: str
    pickups: List[PickupItem] = []
    # assignedTo, status, createdAt, and notes will be auto-generated in backend

class DeploymentCueUpdateSchema(BaseModel):
    operatorId: Optional[str] = None
    name: Optional[str] = None
    tag: Optional[str] = None
    description1: Optional[str] = None
    description2: Optional[str] = None
    pickups: Optional[List[PickupItem]] = None

class AssignedUserCreateSchema(BaseModel):
    name: str
    userId: str

class DeploymentCueNoteCreateSchema(BaseModel):
    note: str
    userId: str
    userName: str
    userEmail: str
    userCompleteName: str
    createdAt: datetime = Field(default_factory=datetime.utcnow)

class AddNoteSchema(BaseModel):
    note: str
    userId: str
    userName: str
    userEmail: str
    userCompleteName: str

class AssignUserSchema(BaseModel):
    name: str
    userId: str