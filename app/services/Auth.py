from app.schemas.User import UserSchema
from app.models.User import UserModel
from app.models.Otp import OTPModel
from app.helpers.Utilities import Utils
from pydantic import ValidationError
from datetime import datetime, timedelta
from fastapi import HTTPException, UploadFile
from postmarker.core import PostmarkClient
from app.helpers.AzureStorage import AzureBlobUploader
import os
import random 
from bson import ObjectId
class AuthService:
    
    def __init__(self):
        self.user_model = UserModel()
        self.otp_model= OTPModel()
        self.uploader = AzureBlobUploader()
            
    async def get_user(self, email, password):
        try:
            user = await self.user_model.get_user({"email": email })
            if not user:
                return {
                    "success": False,
                    "data": None,
                    "error":'User does not exist'
                }
            password_match = Utils.verify_password(password,user.password)
            if(not password_match):
                return {
                    "success": False,
                    "data": None,
                    "error":'Invalid email or password'
                }
            if not user.isApproved:
                return {
                    "success": False,
                    "data": None,
                    "error": "Your account is not approved yet. Please try again later."
                }
            token = Utils.create_jwt_token(user.dict())
            return {
                    "success": True,
                    "data": token
                }
        except ValidationError as e:
            error_details = e.errors()
            raise ValueError(f"Invalid data: {error_details}")
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error":str(e)
            }
    
    async def signup(self, user_data) -> dict:
        """
        This function handles the signup process.
        It checks if the user already exists, hashes the password, and stores the user in the database.
        """
        try:
            existing_user = await self.user_model.get_user({"email": user_data.email})
            if existing_user:
                return {
                "success": False,
                "data": None,
                "error": "User Already Exists."
                }
                
            default_plan_id = os.getenv('DEFAULT_PLAN_ID')    
            
            hashed_password = Utils.hash_password(user_data.password)
            user_data_dict = user_data.dict()
            user_data_dict["password"] = hashed_password
            user_data_dict["createdOn"] = datetime.utcnow()
            user_data_dict["PlanId"] = default_plan_id
            # for pilot program onboarding step be 0,otherwise it will be default -1, 
            # Remove this after pilot program is over
            user_data_dict["onboardingStep"] = 0
            
            user_id = await self.user_model.create_user(user_data_dict)
            
            # Removed Generate JWT token for the user Pilot Program
            # user = await self.user_model.get_user({"_id": user_id})
            # token = Utils.create_jwt_token(user.dict())
            # response = {
            #     "success": True,
            #     "data": token
            # }
            
            response = {
                "success": True,
                "data": "User Created Successfully." 
            }

            return response
        
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def send_otp_email(self, email: str):
        try:
            user = await self.user_model.get_user({"email": email})
            if not user:
                return {"success": False, "data": None, "error": "User not found."}
            From=os.getenv('FROM_EMAIL_ID')
            otp = random.randint(100000,999999)
            await self.otp_model.save_otp(email, otp)
            postmark = PostmarkClient(os.getenv('POSTMARK-SERVER-API-TOKEN')) 
            response = postmark.emails.send_with_template(
                From=From,
                To=email,
                TemplateId=42732046,
                TemplateModel={"otp_code": otp})
            return {"data":"Email sent", "success":True}
        except Exception as e:
            return {"success": False, "data": None,"error": str(e)}
        
    async def verify_otp_reset_password(self, email: str, input_otp: int, new_password: str):
        """Verify OTP and update the user's password"""
        try:
            otp_record = await self.otp_model.get_otp(email)
            if not otp_record:
                return {
                        "success": False,
                        "data": None,
                        "error": "OTP not found."
                    }
            stored_otp = otp_record["otp"]
            created_at = otp_record["createdAt"]
            if datetime.utcnow() - created_at > timedelta(minutes=10):
                return {
                        "success": False,
                        "data": None,
                        "error": "OTP Expired. Request a new OTP."
                    }
            if str(stored_otp) != input_otp:
                return {
                        "success": False,
                        "data": None,
                        "error": "Invalid OTP."
                    }
            new_hashed_password= Utils.hash_password(new_password)
            await self.user_model.update_password(email, new_hashed_password)
            await self.otp_model.delete_otp(email)
            return  {
                        "success": True,
                        "data": "Password Updated Successfully."
                    }
        except Exception as e:
            return {"success": False, "data": None,"error": str(e)}
    
    def upload_profile_picture(self, file: UploadFile):
        try:
            file_content = file.file.read()  
            file_name = file.filename
            return self.uploader.upload_profile_picture(file_content, file_name)
        except Exception as e:
            raise Exception(f"Error uploading profile picture: {str(e)}")
        
    async def get_all_users(self, page: int = 1, limit: int = 10):
        try:
            filters = {}
            limit = limit
            total = await self.user_model.get_documents_count(filters)

            total_pages = (total + limit - 1) // limit
            number_to_skip = (page - 1) * limit
            # Sort by createdOn in descending order (latest first)
            sort = [("createdOn", -1)]
            users = await self.user_model.get_users(filters, number_to_skip, limit, sort)
            # Remove password from user dicts
            users_data = []
            for user in users:
                user_dict = user.dict()
                user_dict.pop('password', None)
                users_data.append(user_dict)
            return {
                "success": True,
                "data": {
                    "users": users_data,
                    "pagination": {
                        "totalPages": total_pages,
                        "currentPage": page,
                        "limit": limit
                }
            }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
        
    async def delete_user(self, user_id: str):
        try:
            deleted = await self.user_model.delete_user(user_id)
            if deleted:
                return {"success": True, "data": "User deleted successfully."}
            else:
                return {"success": False, "data": None, "error": "User not found or already deleted."}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
        
    async def update_user(self, user_id: str, update_data: dict) -> dict:
        """
        Update user information by user_id.
        """
        try:
            if not update_data:
                return {"success": False, "data": None, "error": "No data provided for update."}
            updated = await self.user_model.update_user(user_id, update_data)
            if not updated:
                return {"success": True, "data": "No new changes in data."}
            return {"success": True, "data": "User info updated successfully."}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
    
    async def get_user_by_id(self, user_id: str):
        try:
            user = await self.user_model.get_user({"_id": ObjectId(user_id)})
            if not user:
                return {"success": False, "data": None, "error": "User not found."}
            
            # Remove password from user dict
            user_dict = user.dict()
            user_dict.pop('password', None)
            
            return {"success": True, "data": user_dict}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
    
    async def approve_user(self, user_id: str, is_approved: bool) -> dict:
        """
        Update user approval status based on the provided isApproved value.
        """
        try:
            # Check if user exists
            user = await self.user_model.get_user({"_id": ObjectId(user_id)})
            if not user:
                return {"success": False, "data": None, "error": "User not found."}
            
            # Update user approval status
            updated = await self.user_model.update_user(user_id, {"isApproved": is_approved})
            if not updated:
                return {"success": False, "data": None, "error": "Failed to update user approval status."}
            
            # Send approval email if user is approved
            if is_approved and user.email:
                try:
                    From = os.getenv('FROM_EMAIL_ID')
                    postmark = PostmarkClient(os.getenv('POSTMARK-SERVER-API-TOKEN'))
                    postmark.emails.send_with_template(
                        From=From,
                        To=user.email,
                        TemplateId=42732065,
                        TemplateModel={"name": user.fullName,"app_name":"SOURCE HR","login_url":"https://kind-cliff-0e3c6e210.6.azurestaticapps.net/signin"}
                    )
                except Exception as email_error:
                    # Log email error but don't fail the approval process
                    print(f"Failed to send approval email: {str(email_error)}")
            
            action = "approved" if is_approved else "disapproved"
            return {"success": True, "data": f"User {action} successfully."}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
        
