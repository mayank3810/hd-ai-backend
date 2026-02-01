from typing import Optional
from bson import ObjectId
from app.models.QueueStatus import QueueStatusModel
from app.schemas.QueueStatus import CreateQueueStatusSchema, QueueStatusSchema

class QueueStatusService:
    def __init__(self):
        self.queue_model = QueueStatusModel()

    async def upsert_queue_status(self, queue_data: CreateQueueStatusSchema) -> dict:
        """
        Create or update queue status for an operator.
        """
        try:
            # Convert schema to dict, excluding None values
            data_dict = queue_data.dict(exclude_unset=True)
            
            # Extract operator_id from data
            operator_id = data_dict.get("operator_id")
            
            # Use upsert to create or update
            result = await self.queue_model.upsert_queue_status(operator_id, data_dict)
            
            # Convert Pydantic model to dict for proper serialization
            result_dict = result.dict(by_alias=True) if result else None
            
            return {
                "success": True,
                "data": result_dict,
                "message": "Queue status created/updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Failed to create/update queue status: {str(e)}"
            }

    async def get_queue_status_by_operator(self, operator_id: str, pricelabs_id: Optional[str] = None,
                                           airbnb_id: Optional[str] = None, booking_id: Optional[str] = None,
                                           vrbo_id: Optional[str] = None) -> dict:
        """
        Get queue status for an operator and platform IDs.
        Searches by operator_id AND any of the platform IDs provided.
        """
        try:
            result = await self.queue_model.get_queue_by_operator_and_platform_ids(
                operator_id, pricelabs_id, airbnb_id, booking_id, vrbo_id
            )
            
            if result:
                # Convert Pydantic model to dict for proper serialization
                result_dict = result.dict(by_alias=True)
                
                return {
                    "success": True,
                    "data": result_dict,
                    "message": "Queue status retrieved successfully"
                }
            else:
                return {
                    "success": True,
                    "data": None,
                    "message": "No queue status found for the given criteria"
                }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Failed to retrieve queue status: {str(e)}"
            }

