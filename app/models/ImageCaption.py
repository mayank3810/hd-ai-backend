from app.helpers.Database import MongoDB
from bson import ObjectId
from app.schemas.ImageCaption import ImageCaptionViewSchema
from datetime import datetime
import os

class ImageCaptionModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="ImageCaptions"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_image_caption(self, caption_data: dict) -> str:
        """Create a new image caption record"""
        result = await self.collection.insert_one(caption_data)
        return str(result.inserted_id)

    async def get_image_caption_by_url(self, image_url: str) -> ImageCaptionViewSchema:
        """Get image caption by image URL"""
        caption_doc = await self.collection.find_one({"imageUrl": image_url})
        if caption_doc:
            return ImageCaptionViewSchema(**caption_doc)
        return None

    async def update_image_caption(self, image_url: str, update_data: dict) -> bool:
        """Update an image caption"""
        result = await self.collection.update_one(
            {"imageUrl": image_url},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def upsert_image_caption(self, image_url: str, caption_data: dict) -> str:
        """Create or update an image caption"""
        # Add updated_at timestamp
        caption_data["updatedAt"] = datetime.utcnow()
        
        result = await self.collection.update_one(
            {"imageUrl": image_url},
            {"$set": caption_data},
            upsert=True
        )
        
        if result.upserted_id:
            return str(result.upserted_id)
        else:
            # Return the existing document ID
            existing_doc = await self.collection.find_one({"imageUrl": image_url})
            return str(existing_doc["_id"])

    async def get_image_captions_by_urls(self, image_urls: list) -> list:
        """Get image captions by multiple image URLs"""
        captions = []
        cursor = self.collection.find({"imageUrl": {"$in": image_urls}})
        
        async for caption_doc in cursor:
            captions.append(ImageCaptionViewSchema(**caption_doc))
        
        return captions
