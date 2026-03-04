from datetime import datetime
from app.models.DeploymentCues import DeploymentCuesModel
from app.schemas.DeploymentCues import (
    DeploymentCueCreateSchema, 
    DeploymentCueUpdateSchema, 
    DeploymentCuePropertiesSchema,
    AddNoteSchema,
    AssignUserSchema
)
from bson import ObjectId

class DeploymentCuesService:
    def __init__(self):
        self.deployment_cues_model = DeploymentCuesModel()

    async def create_deployment_cue(self, deployment_cue_data: DeploymentCueCreateSchema) -> dict:
        """Create a new deployment cue"""
        try:
            # Convert to dict and add auto-generated fields
            deployment_cue_dict = deployment_cue_data.model_dump()
            
            # Auto-generate backend fields
            deployment_cue_dict["createdAt"] = datetime.utcnow()
            
            deployment_cue_id = await self.deployment_cues_model.create_deployment_cue(deployment_cue_dict)
            
            # Get created deployment cue
            created_deployment_cue = await self.deployment_cues_model.get_deployment_cue({"_id": deployment_cue_id})
            if not created_deployment_cue:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to retrieve created deployment cue"
                }

            return {
                "success": True,
                "data": created_deployment_cue
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_deployment_cue(self, deployment_cue_id: str, operator_id: str = None) -> dict:
        """Get a deployment cue by ID"""
        try:
            # Build query with operator_id if provided
            query = {"_id": ObjectId(deployment_cue_id)}
            if operator_id:
                query["operatorId"] = operator_id

            deployment_cue_data = await self.deployment_cues_model.get_deployment_cue(query)
            if not deployment_cue_data:
                return {
                    "success": False,
                    "data": None,
                    "error": "Deployment cue not found"
                }

            return {
                "success": True,
                "data": deployment_cue_data
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_deployment_cues(self, page: int = 1, limit: int = 10, filter_query: dict = None, sort_by: dict = None) -> dict:
        """Get all deployment cues with pagination and sorting"""
        try:
            skip = (page - 1) * limit
            query = filter_query if filter_query is not None else {}
            deployment_cues = await self.deployment_cues_model.get_deployment_cues(query, skip, limit, sort_by)
            total = await self.deployment_cues_model.get_deployment_cues_count(query)
            total_pages = (total + limit - 1) // limit

            return {
                "success": True,
                "data": {
                    "deploymentCues": deployment_cues,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "total_pages": total_pages,
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

    async def update_deployment_cue(self, deployment_cue_id: str, update_data: DeploymentCueUpdateSchema) -> dict:
        """Update a deployment cue"""
        try:
            # Check if deployment cue exists
            existing_deployment_cue = await self.deployment_cues_model.get_deployment_cue({"_id": ObjectId(deployment_cue_id)})
            if not existing_deployment_cue:
                return {
                    "success": False,
                    "data": None,
                    "error": "Deployment cue not found"
                }

            # Update deployment cue
            update_dict = update_data.model_dump(exclude_unset=True)
            if not update_dict:
                return {
                    "success": False,
                    "data": None,
                    "error": "No data provided for update"
                }

            updated = await self.deployment_cues_model.update_deployment_cue(deployment_cue_id, update_dict)
            if not updated:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to update deployment cue"
                }

            # Get updated deployment cue
            updated_deployment_cue = await self.deployment_cues_model.get_deployment_cue({"_id": ObjectId(deployment_cue_id)})
            return {
                "success": True,
                "data": updated_deployment_cue
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def delete_deployment_cue(self, deployment_cue_id: str) -> dict:
        """Delete a deployment cue"""
        try:
            # Check if deployment cue exists
            existing_deployment_cue = await self.deployment_cues_model.get_deployment_cue({"_id": ObjectId(deployment_cue_id)})
            if not existing_deployment_cue:
                return {
                    "success": False,
                    "data": None,
                    "error": "Deployment cue not found"
                }

            # Delete deployment cue
            deleted = await self.deployment_cues_model.delete_deployment_cue(deployment_cue_id)
            if not deleted:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to delete deployment cue"
                }

            return {
                "success": True,
                "data": "Deployment cue deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def add_note_to_deployment_cue(self, deployment_cue_id: str, note_data: AddNoteSchema) -> dict:
        """Add a note to a deployment cue"""
        try:
            # Check if deployment cue exists
            existing_deployment_cue = await self.deployment_cues_model.get_deployment_cue({"_id": ObjectId(deployment_cue_id)})
            if not existing_deployment_cue:
                return {
                    "success": False,
                    "data": None,
                    "error": "Deployment cue not found"
                }

            # Add note
            note_dict = note_data.model_dump()
            note_dict["createdAt"] = datetime.utcnow()
            
            added = await self.deployment_cues_model.add_note_to_deployment_cue(deployment_cue_id, note_dict)
            if not added:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to add note to deployment cue"
                }

            # Get updated deployment cue
            updated_deployment_cue = await self.deployment_cues_model.get_deployment_cue({"_id": ObjectId(deployment_cue_id)})
            return {
                "success": True,
                "data": updated_deployment_cue
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def assign_user_to_deployment_cue(self, deployment_cue_id: str, user_data: AssignUserSchema) -> dict:
        """Assign a user to a deployment cue"""
        try:
            # Check if deployment cue exists
            existing_deployment_cue = await self.deployment_cues_model.get_deployment_cue({"_id": ObjectId(deployment_cue_id)})
            if not existing_deployment_cue:
                return {
                    "success": False,
                    "data": None,
                    "error": "Deployment cue not found"
                }

            # Check if user is already assigned
            user_dict = user_data.model_dump()
            for assigned_user in existing_deployment_cue.assignedTo:
                if assigned_user.userId == user_dict["userId"]:
                    return {
                        "success": False,
                        "data": None,
                        "error": "User is already assigned to this deployment cue"
                    }

            # Add user
            added = await self.deployment_cues_model.add_assigned_user_to_deployment_cue(deployment_cue_id, user_dict)
            if not added:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to assign user to deployment cue"
                }

            # Get updated deployment cue
            updated_deployment_cue = await self.deployment_cues_model.get_deployment_cue({"_id": ObjectId(deployment_cue_id)})
            return {
                "success": True,
                "data": updated_deployment_cue
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def remove_user_from_deployment_cue(self, deployment_cue_id: str, user_id: str) -> dict:
        """Remove a user from a deployment cue"""
        try:
            # Check if deployment cue exists
            existing_deployment_cue = await self.deployment_cues_model.get_deployment_cue({"_id": ObjectId(deployment_cue_id)})
            if not existing_deployment_cue:
                return {
                    "success": False,
                    "data": None,
                    "error": "Deployment cue not found"
                }

            # Check if user is assigned
            user_assigned = False
            for assigned_user in existing_deployment_cue.assignedTo:
                if assigned_user.userId == user_id:
                    user_assigned = True
                    break

            if not user_assigned:
                return {
                    "success": False,
                    "data": None,
                    "error": "User is not assigned to this deployment cue"
                }

            # Remove user
            removed = await self.deployment_cues_model.remove_assigned_user_from_deployment_cue(deployment_cue_id, user_id)
            if not removed:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to remove user from deployment cue"
                }

            # Get updated deployment cue
            updated_deployment_cue = await self.deployment_cues_model.get_deployment_cue({"_id": ObjectId(deployment_cue_id)})
            return {
                "success": True,
                "data": updated_deployment_cue
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_deployment_cues_by_operator(self, operator_id: str, page: int = 1, limit: int = 10) -> dict:
        """Get deployment cues by operator ID"""
        try:
            skip = (page - 1) * limit
            deployment_cues = await self.deployment_cues_model.get_deployment_cues_by_operator(operator_id, skip, limit)
            total = await self.deployment_cues_model.get_deployment_cues_count({"operatorId": operator_id})
            total_pages = (total + limit - 1) // limit

            return {
                "success": True,
                "data": {
                    "deploymentCues": deployment_cues,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "total_pages": total_pages,
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

    async def get_deployment_cues_by_property(self, property_id: str, page: int = 1, limit: int = 10) -> dict:
        """Get deployment cues by property ID"""
        try:
            skip = (page - 1) * limit
            deployment_cues = await self.deployment_cues_model.get_deployment_cues_by_property(property_id, skip, limit)
            total = await self.deployment_cues_model.get_deployment_cues_count({"propertyId": property_id})
            total_pages = (total + limit - 1) // limit

            return {
                "success": True,
                "data": {
                    "deploymentCues": deployment_cues,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "total_pages": total_pages,
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

    async def get_deployment_cues_by_status(self, status: str, page: int = 1, limit: int = 10) -> dict:
        """Get deployment cues by status"""
        try:
            skip = (page - 1) * limit
            deployment_cues = await self.deployment_cues_model.get_deployment_cues_by_status(status, skip, limit)
            total = await self.deployment_cues_model.get_deployment_cues_count({"status": status})
            total_pages = (total + limit - 1) // limit

            return {
                "success": True,
                "data": {
                    "deploymentCues": deployment_cues,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "total_pages": total_pages,
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

    async def search_deployment_cues(self, search_query: str, page: int = 1, limit: int = 10) -> dict:
        """Search deployment cues by name or deployment cue ID"""
        try:
            skip = (page - 1) * limit
            deployment_cues = await self.deployment_cues_model.search_deployment_cues(search_query, skip, limit)
            
            # Get total count for search results
            filter_query = {
                "$or": [
                    {"name": {"$regex": search_query, "$options": "i"}},
                    {"tag": {"$regex": search_query, "$options": "i"}},
                    {"description1": {"$regex": search_query, "$options": "i"}},
                    {"description2": {"$regex": search_query, "$options": "i"}}
                ]
            }
            total = await self.deployment_cues_model.get_deployment_cues_count(filter_query)
            total_pages = (total + limit - 1) // limit

            return {
                "success": True,
                "data": {
                    "deploymentCues": deployment_cues,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "total_pages": total_pages,
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