from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.User import UserType


class SpeakerProfileSummary(BaseModel):
    """Speaker profile fields exposed on user management APIs (no conversation)."""

    id: str = Field(..., description="Profile document id")
    full_name: Optional[str] = None
    email: Optional[str] = None
    current_step: Optional[str] = None
    isCompleted: Optional[bool] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True


class UserPublic(BaseModel):
    """User fields returned by admin user APIs (no password)."""

    id: str
    email: EmailStr
    fullName: str
    userType: UserType
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    zip: Optional[str] = None
    profilePicture: Optional[str] = None
    phone: Optional[str] = None
    adminId: Optional[str] = None
    createdOn: Optional[datetime] = None
    updatedOn: Optional[datetime] = None


class UserWithSpeakerProfiles(BaseModel):
    user: UserPublic
    speakerProfiles: List[SpeakerProfileSummary] = Field(default_factory=list)


class UsersListPagination(BaseModel):
    total: int
    totalPages: int
    currentPage: int
    limit: int


class UsersWithProfilesListData(BaseModel):
    users: List[UserWithSpeakerProfiles]
    pagination: UsersListPagination
