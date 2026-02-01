from typing import List, Optional
from app.helpers.Database import MongoDB
from bson import ObjectId
import os
from app.schemas.OnboardingStatus import OnboardingStatusSchema
from datetime import datetime
from app.schemas.PyObjectId import PyObjectId

class OnboardingStatusModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="OnboardingStatus"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_onboarding_status(self, onboarding_data: dict) -> OnboardingStatusSchema:
        """
        Create a new onboarding status record.
        """
        onboarding_data["syncDate"] = datetime.utcnow()
        
        result = await self.collection.insert_one(onboarding_data)
        onboarding_data["_id"] = result.inserted_id
        return OnboardingStatusSchema(**onboarding_data)

    async def get_onboarding_status_by_user_and_operator(self, user_id: str, operator_id: str) -> Optional[OnboardingStatusSchema]:
        """
        Retrieve onboarding status by user ID and operator ID.
        """
        document = await self.collection.find_one({"userId": user_id, "operatorId": operator_id})
        if document:
            return OnboardingStatusSchema(**document)
        return None
    
    async def get_onboarding_status_by_operator(self, operator_id: str) -> Optional[OnboardingStatusSchema]:
        """
        Retrieve onboarding status by operator ID.
        """
        document = await self.collection.find_one({"operatorId": operator_id})
        if document:
            return OnboardingStatusSchema(**document)
        return None
    
    async def get_onboarding_statuses_by_operators(self, operator_ids: List[str]) -> dict:
        """
        Batch retrieve onboarding statuses for multiple operator IDs.
        Returns a dict mapping operator_id -> OnboardingStatusSchema
        """
        if not operator_ids:
            return {}
        
        cursor = self.collection.find({"operatorId": {"$in": operator_ids}})
        status_map = {}
        async for document in cursor:
            operator_id = document.get("operatorId")
            if operator_id:
                status_map[operator_id] = OnboardingStatusSchema(**document)
        return status_map

    async def upsert_onboarding_status(self, operator_id: str, onboarding_data: dict) -> OnboardingStatusSchema:
        """
        Create or update onboarding status for an operator (operator_id based).
        """
        existing = await self.get_onboarding_status_by_operator(operator_id)
        
        if existing:
            # Update existing record
            result = await self.collection.update_one(
                {"operatorId": operator_id},
                {"$set": onboarding_data}
            )
            
            if result.modified_count > 0:
                # Return updated document
                document = await self.collection.find_one({"operatorId": operator_id})
                if document:
                    return OnboardingStatusSchema(**document)
            return existing
        else:
            # Create new record
            onboarding_data["operatorId"] = operator_id
            return await self.create_onboarding_status(onboarding_data)
