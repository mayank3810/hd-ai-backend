import os
from typing import Optional, List
from datetime import datetime

from app.helpers.Database import MongoDB


class AnalyticsReportModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="analyticsReport"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def save_report(self, data: dict):
        data["createdAt"] = datetime.utcnow()
        result = await self.collection.insert_one(data)
        return result.inserted_id

    async def get_reports(self, filters: dict = {}, skip: int = 0, limit: int = 50) -> List[dict]:
        cursor = self.collection.find(filters).skip(skip).limit(limit).sort("createdAt", -1)
        result = []
        async for doc in cursor:
            result.append(doc)
        return result

    async def get_one(self, filters: dict) -> Optional[dict]:
        return await self.collection.find_one(filters)

    async def delete_reports_by_operator(self, operator_id: str) -> int:
        result = await self.collection.delete_many({"operatorId": operator_id})
        return result.deleted_count

