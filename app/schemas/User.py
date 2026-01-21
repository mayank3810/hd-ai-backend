from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
from enum import Enum
from app.schemas.PyObjectId import PyObjectId

class BillingInfoSchema(BaseModel):
    FirstName: Optional[str] = None
    LastName: Optional[str] = None
    Street: Optional[str] = None
    Country: Optional[str] = None
    City: Optional[str] = None
    PostalCode: Optional[str] = None
    VatNumber: Optional[str] = None

class CreateUserSchema(BaseModel):
    fullName: Optional[str] = None
    email: Optional[str] = None
    phone:Optional[str]=None 
    password: Optional[str] = None
    userType: str

    

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class UpdateUserSchema(BaseModel):
    email: Optional[EmailStr] = None
    fullName: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    zip: Optional[str] = None
    profilePicture: Optional[str] = None 
    phone:Optional[str]=None 

class AdminUpdateUserSchema(BaseModel):
    email: Optional[EmailStr] = None
    fullName: Optional[str] = None
    phone:Optional[str]=None 
    userType: Optional[str]=None

class UserSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId,alias="_id")
    email: EmailStr
    password: str
    fullName: str
    userType: Optional[str]=None
    address: Optional[str]=None
    city: Optional[str]=None
    country: Optional[str]=None
    zip: Optional[str]=None
    profilePicture: Optional[str] = None
    phone:Optional[str]=None 
    createdOn: Optional[datetime] = None
    updatedOn: Optional[datetime] = None
    isOnboarded:bool=False
    PlanId: Optional[str] = None
    PlanSubscribedOn: Optional[datetime] = None
    PlanNextBillingDate: Optional[str] = None
    StripeCustomerId: Optional[str] = None
    StripeSubscriptionId: Optional[str] = None
    StripePaymentMethodId: Optional[str] = None
    BillingInfo: Optional[BillingInfoSchema] = None
    onboardingStep:int=-1
    isApproved: bool = False

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

#Get user Schema 
class GetUserSchema(BaseModel):
    email: EmailStr
    password: str

#Reset Password Schema 
class ResetPassword(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        

class UpdateBillingInfoSchema(BaseModel):
    BillingInfo: Optional[BillingInfoSchema] = None

class ApproveUserSchema(BaseModel):
    isApproved: bool