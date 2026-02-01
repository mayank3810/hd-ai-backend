from datetime import datetime
from app.helpers.Utilities import Utils
from app.helpers.AzureStorage import AzureBlobUploader
from bson import ObjectId
from app.models.User import UserModel

class ProfileService:
    def __init__(self):
        self.azure_uploader = AzureBlobUploader()
        self.user_model=UserModel()
    
    async def change_profile_picture(self, user_id: str, file):
        """Replace existing profile picture with a new one using the existing upload function."""
        try:
            if not ObjectId.is_valid(user_id):
                return {"success": False, "data": None, "error": "Invalid ObjectId format."}
            existing_profile = await self.profile_model.get_profile(ObjectId(user_id))
            if existing_profile and existing_profile.get("profilePic"):
                self.azure_uploader.delete_file(existing_profile["profilePic"])
            new_filename = self.azure_uploader.upload_profile_picture(file.file, file.filename)
            await self.profile_model.update_profile(ObjectId(user_id), new_filename)       
            return {"success": True, "data": f"Profile picture updated successfully with name {new_filename}"}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
        
    async def update_user_info(self, user_id: str, data: dict):
        """
        Update user information with enhanced validation
        """
        try:
            # Validate user exists
            user = await self.user_model.get_user({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "data": None,
                    "error": "User not found"
                }

            # Validate update data
            if not data:
                return {
                    "success": False,
                    "data": None,
                    "error": "No data provided for update"
                }

            # Add updatedOn timestamp
            data["updatedOn"] = datetime.utcnow()

            # Update user
            updated = await self.user_model.update_user(user_id, data)
            if not updated:
                return {
                    "success": True,
                    "data": "No changes detected in the provided data"
                }

            # Get updated user data
            updated_user = await self.user_model.get_user({"_id": ObjectId(user_id)})
            if not updated_user:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to retrieve updated user data"
                }

            # Prepare response
            user_data = updated_user.dict()
            user_data.pop("password", None)

            return {
                "success": True,
                "data": {
                    "message": "User information updated successfully",
                    "user": user_data
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
        
    async def get_current_user(self, token: str):
        """
        Get current user information from JWT token with enhanced validation
        """
        try:
            # Decode and validate token
            payload = Utils.decode_jwt_token(token)
            if not payload:
                return {
                    "success": False,
                    "data": None,
                    "error": "Invalid token"
                }

            # Extract user identifiers
            email = payload.get("email")
            if not email:
                return {
                    "success": False,
                    "data": None,
                    "error": "Email missing in token"
                }

            # Get user from database
            user = await self.user_model.get_user({"email": email})
            if not user:
                return {
                    "success": False,
                    "data": None,
                    "error": "User not found"
                }

            # Prepare user data for response
            user_data = user.dict()
            user_data.pop("password", None)  # Remove sensitive data

            return {
                "success": True,
                "data": {
                    "user": user_data
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
                 