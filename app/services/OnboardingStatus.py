from typing import Optional
from bson import ObjectId
from app.models.OnboardingStatus import OnboardingStatusModel
from app.schemas.OnboardingStatus import CreateOnboardingStatusSchema, OnboardingStatusSchema, PlatformStepsSchema

class OnboardingStatusService:
    def __init__(self):
        self.onboarding_model = OnboardingStatusModel()

    async def _handle_platform_steps(self, operator_id: str, steps_data: dict, field_name: str) -> dict:
        """
        Helper method to handle platform steps logic for any platform (Booking, Airbnb, Pricelabs).
        """
        if not steps_data or not isinstance(steps_data, dict):
            return steps_data
            
        # Convert to PlatformStepsSchema for validation
        platform_steps = PlatformStepsSchema(**steps_data)
        
        # Get existing onboarding status to check for existing steps
        existing_status = await self.onboarding_model.get_onboarding_status_by_operator(operator_id)
        
        if existing_status and getattr(existing_status, field_name):
            # Parse existing steps
            existing_steps_data = getattr(existing_status, field_name)
            
            # Handle different data types for existing steps
            if hasattr(existing_steps_data, 'steps') and hasattr(existing_steps_data, 'date'):
                # It's a Pydantic object with steps and date attributes
                existing_steps = getattr(existing_steps_data, 'steps', [])
                existing_date = getattr(existing_steps_data, 'date', "")
            elif isinstance(existing_steps_data, dict):
                # It's a regular dict
                existing_steps = existing_steps_data.get("steps", [])
                existing_date = existing_steps_data.get("date", "")
            elif isinstance(existing_steps_data, str):
                # If it's a string, treat as old format and replace
                existing_steps = []
                existing_date = ""
            else:
                # If it's any other type, treat as old format and replace
                existing_steps = []
                existing_date = ""
            
            # Normalize date values for comparison (handle datetime/date/str)
            def _extract_date_only(value):
                from datetime import datetime, date

                if not value:
                    return ""
                if hasattr(value, "date"):
                    return value.date()
                if isinstance(value, date):
                    return value
                if isinstance(value, str):
                    try:
                        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                        return parsed.date()
                    except ValueError:
                        # Fallback: try splitting date portion
                        return value.split("T")[0]
                return value

            existing_date_normalized = _extract_date_only(existing_date)
            incoming_date_normalized = _extract_date_only(platform_steps.date)

            # Booking platform special handling: if date changes, reset steps
            if (
                field_name == "bookingSteps"
                and existing_date_normalized
                and incoming_date_normalized
                and existing_date_normalized != incoming_date_normalized
            ):
                updated_steps = {
                    "date": platform_steps.date,
                    "steps": platform_steps.steps
                }
            else:
                # Append new steps to existing (avoid duplicates)
                if existing_steps:
                    combined_steps = list(dict.fromkeys([*existing_steps, *platform_steps.steps]))
                    updated_steps = {
                        "date": platform_steps.date,  # Use the new date
                        "steps": combined_steps
                    }
                else:
                    # No existing steps, use new steps
                    updated_steps = {
                        "date": platform_steps.date,
                        "steps": platform_steps.steps
                    }
        else:
            # No existing steps, create new
            updated_steps = {
                "date": platform_steps.date,
                "steps": platform_steps.steps
            }
        
        return updated_steps

    async def create_onboarding_status(self, onboarding_data: CreateOnboardingStatusSchema) -> dict:
        """
        Create or update onboarding status for an operator (operator_id based).
        Handles bookingSteps logic: create new or append to existing based on date.
        """
        try:
            # Convert schema to dict, excluding None values
            data_dict = onboarding_data.dict(exclude_unset=True)
            
            # Extract operatorId from data
            operator_id = data_dict.pop("operatorId")
            
            # Handle platform steps logic for all platforms using the helper method
            platform_step_fields = ["bookingSteps", "airBnbSteps", "priceLabsSteps"]
            
            for field_name in platform_step_fields:
                if field_name in data_dict and data_dict[field_name]:
                    steps_data = data_dict[field_name]
                    if isinstance(steps_data, dict):
                        # Use the helper method to handle steps logic
                        data_dict[field_name] = await self._handle_platform_steps(
                            operator_id, steps_data, field_name
                        )
            
            # Use upsert to create or update
            result = await self.onboarding_model.upsert_onboarding_status(operator_id, data_dict)
            
            # Convert Pydantic model to dict for proper serialization
            result_dict = result.dict(by_alias=True) if result else None
            
            return {
                "success": True,
                "data": result_dict,
                "message": "Onboarding status created/updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Failed to create/update onboarding status: {str(e)}"
            }


    async def get_onboarding_status_by_operator(self, operator_id: ObjectId) -> dict:
        """
        Get onboarding status for an operator.
        """
        try:
            result = await self.onboarding_model.get_onboarding_status_by_operator(operator_id)
            
            if result:
                # Convert Pydantic model to dict for proper serialization
                result_dict = result.dict(by_alias=True)
                return result_dict
            else:
                return None
        except Exception as e:
            return None

