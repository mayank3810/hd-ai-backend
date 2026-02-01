import os
from typing import Optional, List
from bson import ObjectId
from datetime import datetime, timezone

from app.helpers.Database import MongoDB
from app.schemas.PyObjectId import PyObjectId
from app.schemas.CueProperties import CuePropertyCreateSchema, CuePropertyUpdateSchema, CuePropertySchema


class CuePropertiesModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="CueProperties"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_cue_property(self, data: CuePropertyCreateSchema) -> str:
        cue_property_dict = data.model_dump(exclude_none=True,exclude_unset=True)
        result = await self.collection.insert_one(cue_property_dict)
        return str(result.inserted_id)

    async def get_cue_property(self, filters: dict) -> Optional[CuePropertySchema]:
        cue_property_doc = await self.collection.find_one(filters)
        if cue_property_doc:
            return CuePropertySchema(**cue_property_doc)
        return None

    async def get_cue_properties(
        self, filters: dict = {}
    ) -> List[CuePropertySchema]:
        cursor = self.collection.find(filters).sort("createdAt", -1)
        cue_properties_docs = await cursor.to_list(length=None)
        return [CuePropertySchema(**doc) for doc in cue_properties_docs]

    async def update_cue_property(self, cue_property_id: str, data: CuePropertyUpdateSchema) -> bool:
        data_dict = data.model_dump(exclude_none=True, exclude_unset=True)
        data_dict["updatedAt"] = datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {"_id": ObjectId(cue_property_id)},
            {"$set": data_dict}
        )
        return result.modified_count > 0
    
    async def delete_cue_property(self, cue_property_id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(cue_property_id)})
        return result.deleted_count > 0
