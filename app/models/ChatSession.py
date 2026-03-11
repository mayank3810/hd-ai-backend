from app.helpers.Database import MongoDB
from bson import ObjectId
from datetime import datetime
import os
from typing import List, Optional, Dict, Any


class ChatSessionModel:
    """
    Chat session for speaker profile chatbot.
    Stores conversation history per speaker_profile_id.
    """

    def __init__(self, db_name: Optional[str] = None, collection_name: str = "chatSessions"):
        self.collection = MongoDB.get_database(db_name or os.getenv("DB_NAME"))[collection_name]

    async def create_session(
        self,
        speaker_profile_id: str,
        messages: List[Dict[str, Any]],
    ) -> dict:
        """
        Create a new chat session for a speaker profile.
        messages: list of {"role": "user"|"assistant", "content": str}
        """
        doc = {
            "speaker_profile_id": speaker_profile_id,
            "conversation": messages or [],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc

    async def append_messages(
        self,
        chat_session_id: str,
        messages: List[Dict[str, Any]],
    ) -> Optional[dict]:
        """
        Append messages to an existing chat session's conversation.
        """
        if not messages:
            return await self.get_by_id(chat_session_id)
        try:
            oid = ObjectId(chat_session_id)
        except Exception:
            return None
        await self.collection.update_one(
            {"_id": oid},
            {
                "$push": {"conversation": {"$each": messages}},
                "$set": {"updatedAt": datetime.utcnow()},
            },
        )
        return await self.get_by_id(chat_session_id)

    async def get_by_id(self, chat_session_id: str) -> Optional[dict]:
        """Get chat session by id."""
        try:
            oid = ObjectId(chat_session_id)
        except Exception:
            return None
        doc = await self.collection.find_one({"_id": oid})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return doc

    async def get_by_profile_id(self, speaker_profile_id: str) -> List[dict]:
        """Get all chat sessions for a speaker profile (newest first)."""
        cursor = (
            self.collection.find({"speaker_profile_id": speaker_profile_id})
            .sort("createdAt", -1)
        )
        sessions = await cursor.to_list(length=None)
        for s in sessions:
            if "_id" in s:
                s["_id"] = str(s["_id"])
        return sessions

