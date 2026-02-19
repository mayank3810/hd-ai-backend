"""
MongoDB model for Speaker Profile (progressive onboarding + final save).
"""
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId

from app.helpers.Database import MongoDB
from app.config.speaker_profile_steps import get_next_step

# Profile field names (for updates)
PROFILE_FIELDS = [
    "full_name", "email", "topics", "speaking_formats", "delivery_mode", "linkedin_url",
    "past_speaking_examples", "video_links", "talk_description", "key_takeaways", "target_audiences",
]


class SpeakerProfileModel:
    def __init__(
        self,
        db_name: Optional[str] = None,
        collection_name: str = "speaker_profiles",
    ):
        self.collection = MongoDB.get_database(db_name or os.getenv("DB_NAME"))[
            collection_name
        ]

    async def create_profile(
        self,
        full_name: str,
        user_id: Optional[str] = None,
    ) -> dict:
        """
        Create a new profile document after first valid step (full_name).
        Sets current_step to the next step and completed_steps to ["full_name"].
        """
        next_step = get_next_step("full_name")
        next_step_name = next_step.step_name if next_step else "topics"
        doc = {
            "full_name": full_name.strip(),
            "current_step": next_step_name,
            "completed_steps": ["full_name"],
            "conversation": [],
            "user_id": user_id,
            "createdAt": datetime.utcnow(),
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def append_conversation(
        self,
        profile_id: str,
        agent_content: Any,
        user_content: Any,
    ) -> Optional[dict]:
        """
        Append one agent message (question) and one user message (answer) to the profile's conversation array.
        content can be str or list (e.g. for topics/target_audiences).
        """
        try:
            oid = ObjectId(profile_id)
        except Exception:
            return None
        result = await self.collection.update_one(
            {"_id": oid},
            {
                "$push": {
                    "conversation": {
                        "$each": [
                            {"role": "agent", "content": agent_content},
                            {"role": "user", "content": user_content},
                        ]
                    }
                }
            },
        )
        if result.matched_count == 0:
            return None
        return await self.get_profile(profile_id)

    async def update_last_assistant_message(self, profile_id: str, message: str) -> Optional[dict]:
        """Store the last AI-generated assistant message so it can be used as the agent content for the next step's conversation entry."""
        try:
            oid = ObjectId(profile_id)
        except Exception:
            return None
        result = await self.collection.update_one(
            {"_id": oid},
            {"$set": {"last_assistant_message": message, "updatedAt": datetime.utcnow()}},
        )
        if result.matched_count == 0:
            return None
        return await self.get_profile(profile_id)

    async def update_step(
        self,
        profile_id: str,
        updates: Dict[str, Any],
        next_step_name: Optional[str],
        completed_steps: List[str],
        last_assistant_message: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Update profile with new field values and progress.
        Only allowed profile fields are written; current_step and completed_steps are set.
        Optionally set last_assistant_message (AI-generated transition shown before the next step).
        """
        try:
            oid = ObjectId(profile_id)
        except Exception:
            return None
        allowed_updates = {k: v for k, v in updates.items() if k in PROFILE_FIELDS}
        allowed_updates["current_step"] = next_step_name
        allowed_updates["completed_steps"] = completed_steps
        allowed_updates["updatedAt"] = datetime.utcnow()
        if last_assistant_message is not None:
            allowed_updates["last_assistant_message"] = last_assistant_message
        result = await self.collection.update_one(
            {"_id": oid},
            {"$set": allowed_updates},
        )
        if result.matched_count == 0:
            return None
        return await self.get_profile(profile_id)

    async def get_profile(self, profile_id: str) -> Optional[dict]:
        """Return profile document by id, or None if not found."""
        try:
            oid = ObjectId(profile_id)
        except Exception:
            return None
        doc = await self.collection.find_one({"_id": oid})
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def get_profile_by_id_and_user(self, profile_id: str, user_id: str) -> Optional[dict]:
        """Return profile document by id and user_id, or None if not found."""
        try:
            oid = ObjectId(profile_id)
        except Exception:
            return None
        doc = await self.collection.find_one({"_id": oid, "user_id": user_id})
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def get_profiles_by_user_id(self, user_id: str) -> List[dict]:
        """Return all speaker profiles for the given user_id, newest first."""
        cursor = self.collection.find({"user_id": user_id}).sort("createdAt", -1)
        docs = await cursor.to_list(length=None)
        for doc in docs:
            if doc and "_id" in doc:
                doc["_id"] = str(doc["_id"])
        return docs

    async def create_speaker_profile(self, user_id: str, profile_data: dict) -> dict:
        """
        Insert a new speaker profile (full save). profile_data must include all profile fields.
        Adds user_id and createdAt.
        """
        doc = {
            **profile_data,
            "user_id": user_id,
            "createdAt": datetime.utcnow(),
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc
