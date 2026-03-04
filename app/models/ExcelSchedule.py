from app.helpers.Database import MongoDB
from bson import ObjectId
from app.schemas.ExcelSchedule import ExcelScheduleSchema
import os

class ExcelScheduleModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="ExcelSchedule"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_excel_schedule(self, schedule_data: dict) -> str:
        """Create a new Excel schedule entry"""
        result = await self.collection.insert_one(schedule_data)
        return str(result.inserted_id)

    async def get_excel_schedule(self, filter_query: dict) -> ExcelScheduleSchema:
        """Get a single Excel schedule by filter"""
        schedule_doc = await self.collection.find_one(filter_query)
        if schedule_doc:
            return ExcelScheduleSchema(**schedule_doc)
        return None

    async def update_excel_schedule(self, schedule_id: str, update_data: dict) -> bool:
        """Update an Excel schedule entry"""
        result = await self.collection.update_one(
            {"_id": ObjectId(schedule_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def get_excel_schedules_by_operator(self, operator_id: str) -> list[ExcelScheduleSchema]:
        """Get all Excel schedules for a specific operator"""
        filter_query = {
            "operatorId": operator_id
        }
        sort_by = {"createdAt": -1}  # Sort by creation date, newest first
        cursor = self.collection.find(filter_query).sort(list(sort_by.items()))
        schedules = []
        async for doc in cursor:
            schedules.append(ExcelScheduleSchema(**doc))
        return schedules

    async def find_existing_schedule(self, operator_id: str, start_date: str, end_date: str) -> ExcelScheduleSchema:
        """Find existing schedule with same operator, start date, and end date"""
        filter_query = {
            "operatorId": operator_id,
            "startDate": start_date,
            "endDate": end_date
        }
        schedule_doc = await self.collection.find_one(filter_query)
        if schedule_doc:
            return ExcelScheduleSchema(**schedule_doc)
        return None

    async def delete_excel_schedule(self, schedule_id: str) -> bool:
        """Delete an Excel schedule entry"""
        result = await self.collection.delete_one({"_id": ObjectId(schedule_id)})
        return result.deleted_count > 0

