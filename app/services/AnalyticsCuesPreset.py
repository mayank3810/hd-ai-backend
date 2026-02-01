from datetime import datetime
from app.models.AnalyticsCuesPreset import AnalyticsCuesPresetModel
from app.schemas.AnalyticsCuesPreset import AnalyticsCuesPresetSchema, AnalyticsCuesPresetCreateSchema
from bson import ObjectId

class AnalyticsCuesPresetService:
    def __init__(self):
        self.preset_model = AnalyticsCuesPresetModel()

    async def create_analytics_cues_preset(self, preset_data: AnalyticsCuesPresetCreateSchema) -> dict:
        """Create a new analytics cues preset"""
        try:
            # Convert to dict and add createdAt
            preset_dict = preset_data.model_dump()
            preset_dict["createdAt"] = datetime.utcnow()

            preset_id = await self.preset_model.create_analytics_cues_preset(preset_dict)
            
            # Get created preset
            created_preset = await self.preset_model.get_analytics_cues_preset({"_id": ObjectId(preset_id)})
            if not created_preset:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to retrieve created analytics cues preset"
                }

            return {
                "success": True,
                "data": created_preset.id
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_analytics_cues_presets_by_operator(self, operator_id: str) -> dict:
        """Get 5 analytics cues presets for a specific operator"""
        try:
            presets = await self.preset_model.get_analytics_cues_presets_by_operator(operator_id, limit=5)

            return {
                "success": True,
                "data": {
                    "presets": presets
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def delete_analytics_cues_preset(self, preset_id: str, operator_id: str = None) -> dict:
        """Delete an analytics cues preset with optional operator validation"""
        try:
            # Check if preset exists and belongs to the operator
            query = {"_id": ObjectId(preset_id)}
            if operator_id:
                query["operatorId"] = operator_id
                
            existing_preset = await self.preset_model.get_analytics_cues_preset(query)
            if not existing_preset:
                return {
                    "success": False,
                    "data": None,
                    "error": "Analytics cues preset not found"
                }

            # Delete preset
            deleted = await self.preset_model.delete_analytics_cues_preset(preset_id)
            if not deleted:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to delete analytics cues preset"
                }

            return {
                "success": True,
                "data": "Analytics cues preset deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

