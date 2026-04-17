import os
from datetime import datetime
from typing import Any, Optional

from dotenv import load_dotenv
from pymongo import ReturnDocument

from app.helpers.Database import MongoDB

load_dotenv()


class SubscriptionsModel:
    """Mongo ``subscriptions`` collection (plan rows keyed by ``user_id`` / Stripe ids)."""

    def __init__(self, db_name: str | None = None, collection_name: str = "subscriptions"):
        db = db_name or os.getenv("DB_NAME")
        self.collection = MongoDB.get_database(db)[collection_name]

    async def find_by_user_id(self, user_id: str) -> Optional[dict[str, Any]]:
        doc = await self.collection.find_one({"user_id": user_id})
        return self._normalize(doc)

    async def find_all_by_user_id(self, user_id: str) -> list[dict[str, Any]]:
        cursor = self.collection.find({"user_id": user_id}).sort(
            [("createdOn", -1), ("_id", -1)]
        )
        docs = await cursor.to_list(length=None)
        out: list[dict[str, Any]] = []
        for doc in docs:
            norm = self._normalize(doc)
            if norm:
                out.append(norm)
        return out

    async def find_active_with_stripe(self, user_id: str) -> Optional[dict[str, Any]]:
        doc = await self.collection.find_one(
            {
                "user_id": user_id,
                "active": True,
                "stripe_subscription_id": {"$exists": True, "$nin": [None, ""]},
            }
        )
        return self._normalize(doc)

    async def find_by_stripe_customer_id(self, stripe_customer_id: str) -> Optional[dict[str, Any]]:
        doc = await self.collection.find_one({"stripe_customer_id": stripe_customer_id})
        return self._normalize(doc)

    async def insert_one(self, document: dict[str, Any]) -> dict[str, Any]:
        payload = dict(document)
        payload.setdefault("createdOn", datetime.utcnow())
        result = await self.collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return self._normalize(payload)

    async def update_by_user_id(
        self, user_id: str, set_fields: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        doc = await self.collection.find_one_and_update(
            {"user_id": user_id},
            {"$set": dict(set_fields)},
            return_document=ReturnDocument.AFTER,
        )
        return self._normalize(doc)

    async def update_by_stripe_customer_id(
        self, stripe_customer_id: str, set_fields: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        doc = await self.collection.find_one_and_update(
            {"stripe_customer_id": stripe_customer_id},
            {"$set": dict(set_fields)},
            return_document=ReturnDocument.AFTER,
        )
        return self._normalize(doc)

    def _normalize(self, doc: Any) -> Optional[dict[str, Any]]:
        if not doc:
            return None
        out = dict(doc)
        if out.get("_id") is not None:
            out["_id"] = str(out["_id"])
        return out
