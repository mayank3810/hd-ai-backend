from datetime import datetime, timezone
from fastapi import HTTPException
from app.models.CueProperties import CuePropertiesModel
from app.schemas.CueProperties import CuePropertySchema, CuePropertyCreateSchema, CuePropertyUpdateSchema
from bson import ObjectId
from app.models.Property import PropertyModel
class CuePropertiesService:
    def __init__(self):
        self.cue_properties_model = CuePropertiesModel()
        self.property_model = PropertyModel()

    async def create_cue_property(self, cue_property_data: CuePropertyCreateSchema) -> dict:
        """Create a new cue property"""
        try:
            # Check if cue property already exists
            existing_cue_property = await self.cue_properties_model.get_cue_property({
                "operatorId": cue_property_data.operatorId, 
                "propertyId": cue_property_data.propertyId
            })
            if existing_cue_property:
                return {
                    "success": True,
                    "data": {
                        "id": str(existing_cue_property.id)
                    }
                }
            
            # Create new cue property if it doesn't exist
            cue_property_id = await self.cue_properties_model.create_cue_property(cue_property_data)
            
            return {
                "success": True,
                "data": {
                    "id": cue_property_id
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_cue_property(self, cue_property_id: str) -> dict:
        """Get a cue property by ID"""
        try:
            cue_property = await self.cue_properties_model.get_cue_property({"_id": ObjectId(cue_property_id)})
            if not cue_property:
                return {
                    "success": False,
                    "data": None,
                    "error": "Cue property not found"
                }
            return {
                "success": True,
                "data": cue_property
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_cue_properties(self, filter_query: dict = {}) -> dict:
        """Get all cue properties with pagination and sorting"""
        try:
            cue_properties = await self.cue_properties_model.get_cue_properties(filter_query)
            cue_properties_with_data = []
            
            for cue_property in cue_properties:
                cue_property_dict = cue_property.model_dump(by_alias=True)
                
                if cue_property.propertyId:
                    property_data = await self.property_model.collection.find_one(
                        {"_id": ObjectId(cue_property.propertyId),"Pricelabs_SyncStatus":True},
                        {"Photos": 0,"Amenities": 0,"CXL_Policy":0}
                    )
                    cue_property_dict["propertyData"] = property_data
                
                cue_properties_with_data.append(cue_property_dict)
            
            return {
                "success": True,
                "data": cue_properties_with_data
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def update_cue_property(self, cue_property_id: str, update_data: CuePropertyUpdateSchema) -> dict:
        """Update a cue property"""
        try:
            # Check if cue property exists
            existing_cue_property = await self.cue_properties_model.get_cue_property({"_id": ObjectId(cue_property_id)})
            if not existing_cue_property:
                return {
                    "success": False,
                    "data": None,
                    "error": "Cue property not found"
                }

            # Update cue property
            updated = await self.cue_properties_model.update_cue_property(cue_property_id, update_data)
            if not updated:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to update cue property"
                }

            # Get updated cue property
            updated_cue_property = await self.cue_properties_model.get_cue_property({"_id": ObjectId(cue_property_id)})
            return {
                "success": True,
                "data": updated_cue_property
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def delete_cue_property(self, cue_property_id: str) -> dict:
        """Delete a cue property"""
        try:
            # Check if cue property exists
            existing_cue_property = await self.cue_properties_model.get_cue_property({"_id": ObjectId(cue_property_id)})
            if not existing_cue_property:
                return {
                    "success": False,
                    "data": None,
                    "error": "Cue property not found"
                }

            # Delete cue property
            deleted = await self.cue_properties_model.delete_cue_property(cue_property_id)
            if not deleted:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to delete cue property"
                }

            return {
                "success": True,
                "data": "Cue property deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

