from app.models.Operator import OperatorModel
from app.models.OnboardingStatus import OnboardingStatusModel
from app.models.FilterPreset import FilterPresetModel
from app.schemas.Operator import CreateOperator
from typing import List, Optional
from bson import ObjectId
from fastapi import HTTPException
from datetime import datetime

class OperatorService:
    def __init__(self):
        self.operator_model = OperatorModel()
        self.onboarding_model = OnboardingStatusModel()
        self.filter_preset_model = FilterPresetModel()

    async def create_operator(self, data: CreateOperator, user_id: str) -> dict:
        try:
            # Convert the CreateOperator model to dict and add userId as array
            operator_data = data.model_dump()
            operator_data["userId"] = [user_id]
            
            inserted_id = await self.operator_model.create_operator(operator_data)
            operator_id_str = str(inserted_id)
            
            # Create default filter presets for the new operator
            try:
                await self._create_default_filter_presets(operator_id_str, user_id)
            except Exception as preset_error:
                # Log error but don't fail operator creation if preset creation fails
                print(f"Warning: Failed to create default presets for operator {operator_id_str}: {str(preset_error)}")
            
            return {
                "success": True,
                "data": operator_id_str
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to create operator: {str(e)}"
            }
    
    async def _create_default_filter_presets(self, operator_id: str, user_id: str) -> None:
        """Create default filter presets for a new operator"""
        default_presets = [
            {
                "operatorId": operator_id,
                "name": "Week 1 for CM",
                "description": "Remove STLY if no comparison and retry \nFilter on review and share with client",
                "propertyIds": None,
                "filters": {
                    "occupancyTMMin": 0,
                    "occupancyTMMax": 30,
                    "occupancy7DaysMin": 0,
                    "occupancy7DaysMax": 75,
                    "pickUpOcc7DaysMin": 0,
                    "pickUpOcc7DaysMax": 30,
                    "stlyVarOccMin": -100,
                    "stlyVarOccMax": 0,
                    "stlyVarADRMin": -100,
                    "stlyVarADRMax": 5
                },
                "isAllpropertiesSelected": False,
                "userId": user_id,
                "createdAt": datetime.utcnow()
            },
            {
                "operatorId": operator_id,
                "name": "Week 2 for CM",
                "description": "Look for any restriction if the unit is still below 10%",
                "propertyIds": None,
                "filters": {
                    "mpiMin": 0,
                    "mpiMax": 60,
                    "occupancyTMMin": 0,
                    "occupancyTMMax": 50,
                    "occupancy7DaysMin": 0,
                    "occupancy7DaysMax": 75,
                    "pickUpOcc7DaysMin": 0,
                    "pickUpOcc7DaysMax": 30
                },
                "isAllpropertiesSelected": False,
                "userId": user_id,
                "createdAt": datetime.utcnow()
            },
            {
                "operatorId": operator_id,
                "name": "Week 3 for CM",
                "description": "Check for availability if occupancy still below 25%",
                "propertyIds": None,
                "filters": {
                    "mpiMin": 0,
                    "mpiMax": 100,
                    "occupancyTMMin": 0,
                    "occupancyTMMax": 70,
                    "occupancy7DaysMin": 0,
                    "occupancy7DaysMax": 100,
                    "pickUpOcc7DaysMin": 0,
                    "pickUpOcc7DaysMax": 10
                },
                "isAllpropertiesSelected": False,
                "userId": user_id,
                "createdAt": datetime.utcnow()
            },
            {
                "operatorId": operator_id,
                "name": "Week 4 for CM",
                "description": "The units to be shared with Partner as CM+1 is also not very strong",
                "propertyIds": None,
                "filters": {
                    "occupancyTMMin": 0,
                    "occupancyTMMax": 70,
                    "occupancyNMMin": 0,
                    "occupancyNMMax": 10,
                    "occupancy7DaysMin": 0,
                    "occupancy7DaysMax": 100,
                    "pickUpOcc7DaysMin": 0,
                    "pickUpOcc7DaysMax": 10
                },
                "isAllpropertiesSelected": False,
                "userId": user_id,
                "createdAt": datetime.utcnow()
            },
            {
                "operatorId": operator_id,
                "name": "CM+1 check to be run on 15th of CM",
                "description": None,
                "propertyIds": None,
                "filters": {
                    "occupancyNMMin": 0,
                    "occupancyNMMax": 15,
                    "pickUpOcc14DaysMin": 0,
                    "pickUpOcc14DaysMax": 10
                },
                "isAllpropertiesSelected": False,
                "userId": user_id,
                "createdAt": datetime.utcnow()
            }
        ]
        
        # Create all default presets
        for preset_data in default_presets:
            try:
                await self.filter_preset_model.create_filter_preset(preset_data)
            except Exception as e:
                # Log error but continue creating other presets
                print(f"Warning: Failed to create preset '{preset_data.get('name')}': {str(e)}")
                continue

    async def list_operators(self, page: int = 1, limit: int = 10,user_id:str=None) -> dict:
        try:
            limit=limit
            # Query operators where userId array contains the user_id
            # MongoDB automatically handles array matching: {"userId": user_id} will match if user_id is in the array
            filter_query = {"userId": user_id} if user_id else {}
            total = await self.operator_model.collection.count_documents(filter_query)
            total_pages = (total + limit - 1) // limit
            number_to_skip = (page - 1) * limit
            operators = await self.operator_model.list_operators(filter_query, number_to_skip, limit)
            
            # Batch fetch all onboarding statuses in a single query
            operator_ids = [str(operator.get("_id")) for operator in operators]
            onboarding_statuses = await self.onboarding_model.get_onboarding_statuses_by_operators(operator_ids)
            
            # Add onboarding status for each operator
            operators_with_status = []
            for operator in operators:
                operator_dict = operator
                operator_id = str(operator_dict.get("_id"))
                
                # Get onboarding status from the batch-fetched map
                onboarding_status = onboarding_statuses.get(operator_id)
                
                if onboarding_status:
                    operator_dict["onboardingStatus"] = onboarding_status.dict(by_alias=True)
                else:
                    operator_dict["onboardingStatus"] = None
                
                operators_with_status.append(operator_dict)
            
            return {
                "success": True,
                "data": {
                    "operators": operators_with_status,
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
                "error": f"Unable to list operators: {str(e)}"
            }

    async def get_operator_by_id(self, operator_id: str) -> dict:
        try:
            if not ObjectId.is_valid(operator_id):
                raise HTTPException(status_code=400, detail="Invalid Operator ID")
            operator = await self.operator_model.get_operator({"_id": ObjectId(operator_id)})
            if not operator:
                raise HTTPException(status_code=404, detail="Operator not found")
            return {
                "success": True,
                "data": operator.model_dump()
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to get operator: {str(e)}"
            }

    async def update_operator(self, operator_id: str, data: dict) -> dict:
        try:
            if not ObjectId.is_valid(operator_id):
                raise HTTPException(status_code=400, detail="Invalid Operator ID")
            updated = await self.operator_model.update_operator(operator_id, data)
            if not updated:
                raise HTTPException(status_code=404, detail="Operator not found or not updated")
            return {
                "success": True,
                "data": "Operator updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to update operator: {str(e)}"
            }

    async def delete_operator(self, operator_id: str) -> dict:
        try:
            if not ObjectId.is_valid(operator_id):
                raise HTTPException(status_code=400, detail="Invalid Operator ID")
            data = await self.operator_model.delete_operator(operator_id)
            return {
                "success": True,
                "data":  "Operator deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to delete operator: {str(e)}"
            }
            
    async def remove_user_from_operator(self, operator_id: str, user_id: str) -> dict:
        try:
            if not ObjectId.is_valid(operator_id):
                raise HTTPException(status_code=400, detail="Invalid Operator ID")
            updated = await self.operator_model.remove_user_from_operator(operator_id, user_id)
            if not updated:
                raise HTTPException(status_code=404, detail="Operator not found or user not associated")
            return {
                "success": True,
                "data": "User removed from operator successfully"
            }
        except HTTPException:
            raise
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to remove user from operator: {str(e)}"
            }
