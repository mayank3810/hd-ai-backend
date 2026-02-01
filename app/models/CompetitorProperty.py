from app.helpers.Database import MongoDB
from bson import ObjectId
from app.schemas.CompetitorProperty import CompetitorPropertySchema
from datetime import datetime
import os

class CompetitorPropertyModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="CompetitorProperties"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_competitor_property(self, competitor_property_data: dict) -> str:
        """Create a new competitor property"""
        result = await self.collection.insert_one(competitor_property_data)
        return str(result.inserted_id)

    async def get_competitor_property(self, filter_query: dict) -> CompetitorPropertySchema:
        """Get a single competitor property by filter"""
        competitor_property_doc = await self.collection.find_one(filter_query)
        if competitor_property_doc:
            return CompetitorPropertySchema(**competitor_property_doc)
        return None

    async def get_competitor_properties(self, filter_query: dict = None, skip: int = 0, limit: int = 10, sort_by: dict = None) -> list[CompetitorPropertySchema]:
        """Get multiple competitor properties with pagination and sorting
        
        Args:
            filter_query: MongoDB filter query
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort_by: MongoDB sort specification, e.g., {"createdAt": -1} for descending order
        """
        if filter_query is None:
            filter_query = {}
        if sort_by is None:
            sort_by = {"_id": -1}  # Default sort by _id (which includes timestamp), newest first
            
        cursor = self.collection.find(filter_query).sort(list(sort_by.items())).skip(skip).limit(limit)
        properties = []
        async for doc in cursor:
            properties.append(CompetitorPropertySchema(**doc))
        return properties

    async def get_competitor_properties_count(self, filter_query: dict = None) -> int:
        """Get total count of competitor properties matching filter"""
        if filter_query is None:
            filter_query = {}
        return await self.collection.count_documents(filter_query)

    async def update_competitor_property(self, competitor_property_id: str, update_data: dict) -> bool:
        """Update a competitor property"""
        result = await self.collection.update_one(
            {"_id": ObjectId(competitor_property_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def delete_competitor_property(self, competitor_property_id: str) -> bool:
        """Delete a competitor property"""
        result = await self.collection.delete_one({"_id": ObjectId(competitor_property_id)})
        return result.deleted_count > 0

    async def get_competitor_properties_by_operator_id(self, operator_id: str, skip: int = 0, limit: int = 10) -> list[CompetitorPropertySchema]:
        """Get competitor properties by operator ID"""
        filter_query = {"operatorId": operator_id}
        cursor = self.collection.find(filter_query).skip(skip).limit(limit)
        properties = []
        async for doc in cursor:
            properties.append(CompetitorPropertySchema(**doc))
        return properties

    async def get_competitor_properties_by_platform_ids(self, booking_id: str = None, airbnb_id: str = None, vrbo_id: str = None, skip: int = 0, limit: int = 10) -> list[CompetitorPropertySchema]:
        """Get competitor properties that match any of the specified platform IDs"""
        filter_query = {}
        if booking_id:
            filter_query["bookingId"] = booking_id
        if airbnb_id:
            filter_query["airbnbId"] = airbnb_id
        if vrbo_id:
            filter_query["vrboId"] = vrbo_id
        
        if not filter_query:
            return []
            
        cursor = self.collection.find(filter_query).skip(skip).limit(limit)
        properties = []
        async for doc in cursor:
            properties.append(CompetitorPropertySchema(**doc))
        return properties

    async def get_competitor_properties_by_operator_and_platform_ids(self, operator_id: str, booking_id: str = None, airbnb_id: str = None, vrbo_id: str = None, skip: int = 0, limit: int = 10) -> list[CompetitorPropertySchema]:
        """Get competitor properties by operator ID and platform IDs"""
        filter_query = {"operatorId": operator_id}
        
        platform_filter = {}
        if booking_id:
            platform_filter["bookingId"] = booking_id
        if airbnb_id:
            platform_filter["airbnbId"] = airbnb_id
        if vrbo_id:
            platform_filter["vrboId"] = vrbo_id
        
        if platform_filter:
            filter_query.update(platform_filter)
            
        cursor = self.collection.find(filter_query).skip(skip).limit(limit)
        properties = []
        async for doc in cursor:
            properties.append(CompetitorPropertySchema(**doc))
        return properties

    async def update_photo_counts(self, competitor_property_id: str, num_photos: int, captioned_count: int, missing_caption_count: int) -> bool:
        """Update photo counts for a competitor property"""
        update_data = {
            "numPhotos": num_photos,
            "captionedCount": captioned_count,
            "missingCaptionCount": missing_caption_count,
            "updatedAt": datetime.utcnow()
        }
        result = await self.collection.update_one(
            {"_id": ObjectId(competitor_property_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def get_competitors_by_ids(self, competitor_ids: list[str]) -> list[CompetitorPropertySchema]:
        """Get competitor properties by their IDs"""
        if not competitor_ids:
            return []
        filter_query = {"_id": {"$in": [ObjectId(comp_id) for comp_id in competitor_ids]}}
        cursor = self.collection.find(filter_query)
        properties = []
        async for doc in cursor:
            properties.append(CompetitorPropertySchema(**doc))
        return properties

    async def get_competitors_by_ids_with_projection(self, competitor_ids: list[str]) -> list[dict]:
        """Get competitor properties by their IDs with limited projection (returns raw dicts)"""
        if not competitor_ids:
            return []
        filter_query = {"_id": {"$in": [ObjectId(comp_id) for comp_id in competitor_ids]}}
        
        # Projection to only fetch essential fields
        projection = {
            "_id": 1,
            "operatorId": 1,
            "propertyName": 1,
            "bookingId": 1,
            "bookingLink": 1,
            "airbnbId": 1,
            "airbnbLink": 1,
            "vrboId": 1,
            "vrboLink": 1,
            "propertyBookingPhotos": 1,
            "propertyAirbnbPhotos": 1,
            "propertyVrboPhotos": 1,
            "amenitiesBooking": 1,
            "amenitiesAirbnb": 1,
        }
        
        cursor = self.collection.find(filter_query, projection)
        properties = []
        async for doc in cursor:
            # Convert ObjectId to string for JSON serialization
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            properties.append(doc)
        return properties

    async def get_competitors_with_counts_optimized(self, competitor_ids: list[str]) -> list[dict]:
        """Get competitor properties with aggregated counts for reviews and photos (optimized)"""
        if not competitor_ids:
            return []
        
        # Use aggregation pipeline to get counts directly from database
        pipeline = [
            {"$match": {"_id": {"$in": [ObjectId(comp_id) for comp_id in competitor_ids]}}},
            {
                "$project": {
                    "_id": 1,
                    "operatorId": 1,
                    "propertyName": 1,
                    "bookingId": 1,
                    "bookingLink": 1,
                    "airbnbId": 1,
                    "airbnbLink": 1,
                    "vrboId": 1,
                    "vrboLink": 1,
                    
                    # Photo counts by platform
                    "competitor_booking_photos_count": {"$size": {"$ifNull": ["$propertyBookingPhotos", []]}},
                    "competitor_airbnb_photos_count": {"$size": {"$ifNull": ["$propertyAirbnbPhotos", []]}},
                    "competitor_vrbo_photos_count": {"$size": {"$ifNull": ["$propertyVrboPhotos", []]}},
                    
                    # Review counts by platform
                    "competitor_booking_reviews_count": {"$size": {"$ifNull": ["$reviewsBooking", []]}},
                    "competitor_airbnb_reviews_count": {"$size": {"$ifNull": ["$reviewsAirbnb", []]}},
                    "competitor_vrbo_reviews_count": {"$size": {"$ifNull": ["$reviewsVrbo", []]}},
                    
                    # Amenity counts by platform
                    "competitor_booking_amenities_count": {"$size": {"$ifNull": ["$amenitiesBooking.highlights", []]}},
                    "competitor_airbnb_amenities_count": {"$size": {"$ifNull": ["$amenitiesAirbnb", []]}},
                    "competitor_vrbo_amenities_count": {"$size": {"$ifNull": ["$amenitiesVrbo", []]}}
                }
            }
        ]
        
        properties = []
        async for doc in self.collection.aggregate(pipeline):
            # Convert ObjectId to string for JSON serialization
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            properties.append(doc)
        return properties

    async def get_competitors_by_ids_optimized(self, competitor_ids: list[str]) -> list[CompetitorPropertySchema]:
        """Get competitor properties by their IDs (optimized with projection)"""
        if not competitor_ids:
            return []
        filter_query = {"_id": {"$in": [ObjectId(comp_id) for comp_id in competitor_ids]}}
        
        # Projection to only fetch fields needed for comparison
        projection = {
            "_id": 1,
            "propertyName": 1,
            "operatorId": 1,
            "bookingId": 1,
            "bookingLink": 1,
            "airbnbId": 1,
            "airbnbLink": 1,
            "vrboId": 1,
            "vrboLink": 1,
            "propertyBookingPhotos": 1,
            "propertyAirbnbPhotos": 1,
            "propertyVrboPhotos": 1
        }
        
        cursor = self.collection.find(filter_query, projection)
        properties = []
        async for doc in cursor:
            properties.append(CompetitorPropertySchema(**doc))
        return properties

    async def get_competitor_properties_for_export(self, operator_id: str, skip: int = 0, limit: int = 1000) -> list[dict]:
        """Get competitor properties for export with minimal projection (returns raw dicts)"""
        filter_query = {"operatorId": operator_id}
        
        # Projection to only fetch fields needed for export
        projection = {
            "_id": 1,
            "propertyName": 1,
            "bookingId": 1,
            "bookingLink": 1,
            "airbnbId": 1,
            "airbnbLink": 1,
            "vrboId": 1,
            "vrboLink": 1,
            "amenitiesBooking": 1,
            "amenitiesAirbnb": 1,
            "reviewsBooking": 1,
            "reviewsAirbnb": 1
        }
        
        cursor = self.collection.find(filter_query, projection).skip(skip).limit(limit)
        properties = []
        async for doc in cursor:
            # Convert ObjectId to string for JSON serialization
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            properties.append(doc)
        return properties

