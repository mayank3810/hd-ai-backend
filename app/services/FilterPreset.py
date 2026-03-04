from datetime import datetime
from app.models.FilterPreset import FilterPresetModel
from app.models.Property import PropertyModel
from app.schemas.FilterPreset import FilterPresetSchema, FilterPresetCreateSchema, FilterPresetUpdateSchema
from bson import ObjectId

class FilterPresetService:
    def __init__(self):
        self.filter_preset_model = FilterPresetModel()
        self.property_model = PropertyModel()

    async def create_filter_preset(self, filter_preset_data: FilterPresetCreateSchema) -> dict:
        """Create a new filter preset"""
        try:
            # Convert to dict and create filter preset
            filter_preset_dict = filter_preset_data.model_dump(exclude_unset=True)
            # Ensure createdAt
            if "createdAt" not in filter_preset_dict:
                filter_preset_dict["createdAt"] = datetime.utcnow()

            filter_preset_id = await self.filter_preset_model.create_filter_preset(filter_preset_dict)
            
            # Get created filter preset
            created_filter_preset = await self.filter_preset_model.get_filter_preset({"_id": ObjectId(filter_preset_id)})
            if not created_filter_preset:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to retrieve created filter preset"
                }

            return {
                "success": True,
                "data": created_filter_preset
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def create_filter_preset_with_dict(self, filter_preset_dict: dict) -> dict:
        """Create a new filter preset from dictionary"""
        try:
            # Ensure createdAt
            if "createdAt" not in filter_preset_dict:
                filter_preset_dict["createdAt"] = datetime.utcnow()

            # Handle isAllpropertiesSelected flag
            is_all_properties_selected = filter_preset_dict.get("isAllpropertiesSelected")
            
            if is_all_properties_selected:
                # Get operator_id from the dict
                operator_id = filter_preset_dict.get("operatorId")
                if not operator_id:
                    return {
                        "success": False,
                        "data": None,
                        "error": "operatorId is required when isAllpropertiesSelected is True"
                    }
                
                # Fetch all property IDs for the given operator (no limit)
                properties = await self.property_model.get_properties_for_csv(filter_query={"operator_id": operator_id})
                
                # Extract property IDs as strings
                property_ids = [str(prop.id) for prop in properties if prop.id]
                
                # Set propertyIds in the filter_preset_dict
                filter_preset_dict["propertyIds"] = property_ids

            filter_preset_id = await self.filter_preset_model.create_filter_preset(filter_preset_dict)
            
            # Get created filter preset
            created_filter_preset = await self.filter_preset_model.get_filter_preset({"_id": ObjectId(filter_preset_id)})
            if not created_filter_preset:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to retrieve created filter preset"
                }

            return {
                "success": True,
                "data": created_filter_preset
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_filter_preset(self, filter_preset_id: str, operator_id: str = None) -> dict:
        """Get a filter preset by ID with optional operator validation"""
        try:
            query = {"_id": ObjectId(filter_preset_id)}
            if operator_id:
                query["operatorId"] = operator_id
                
            filter_preset_data = await self.filter_preset_model.get_filter_preset(query)
            if not filter_preset_data:
                return {
                    "success": False,
                    "data": None,
                    "error": "Filter preset not found"
                }

            return {
                "success": True,
                "data": filter_preset_data
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_filter_presets_by_operator(self, operator_id: str) -> dict:
        """Get all filter presets for a specific operator"""
        try:
            filter_presets = await self.filter_preset_model.get_filter_presets_by_operator(operator_id)

            return {
                "success": True,
                "data": {
                    "filterPresets": filter_presets
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def update_filter_preset(self, filter_preset_id: str, update_data: FilterPresetUpdateSchema, operator_id: str = None) -> dict:
        """Update a filter preset with optional operator validation"""
        try:
            # Check if filter preset exists and belongs to the operator
            query = {"_id": ObjectId(filter_preset_id)}
            if operator_id:
                query["operatorId"] = operator_id
                
            existing_filter_preset = await self.filter_preset_model.get_filter_preset(query)
            if not existing_filter_preset:
                return {
                    "success": False,
                    "data": None,
                    "error": "Filter preset not found"
                }

            # Update filter preset
            update_dict = update_data.model_dump(exclude_unset=True)
            if not update_dict:
                return {
                    "success": False,
                    "data": None,
                    "error": "No data provided for update"
                }

            # Add updatedAt timestamp
            update_dict["updatedAt"] = datetime.utcnow()

            updated = await self.filter_preset_model.update_filter_preset(filter_preset_id, update_dict)
            if not updated:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to update filter preset"
                }

            # Get updated filter preset
            updated_filter_preset = await self.filter_preset_model.get_filter_preset({"_id": ObjectId(filter_preset_id)})
            return {
                "success": True,
                "data": updated_filter_preset
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def delete_filter_preset(self, filter_preset_id: str, operator_id: str = None) -> dict:
        """Delete a filter preset with optional operator validation"""
        try:
            # Check if filter preset exists and belongs to the operator
            query = {"_id": ObjectId(filter_preset_id)}
            if operator_id:
                query["operatorId"] = operator_id
                
            existing_filter_preset = await self.filter_preset_model.get_filter_preset(query)
            if not existing_filter_preset:
                return {
                    "success": False,
                    "data": None,
                    "error": "Filter preset not found"
                }

            # Delete filter preset
            deleted = await self.filter_preset_model.delete_filter_preset(filter_preset_id)
            if not deleted:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to delete filter preset"
                }

            return {
                "success": True,
                "data": "Filter preset deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
