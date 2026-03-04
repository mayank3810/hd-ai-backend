from app.helpers.Database import MongoDB
from bson import ObjectId
from app.schemas.Property import PropertySchema
import os

class PropertyModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Properties"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_property(self, property_data: dict) -> str:
        """Create a new property"""
        result = await self.collection.insert_one(property_data)
        return str(result.inserted_id)

    async def get_property(self, filter_query: dict) -> PropertySchema:
        """Get a single property by filter"""
        filter_query = dict(filter_query or {})
        filter_query["Pricelabs_SyncStatus"] = True
        property_doc = await self.collection.find_one(filter_query)
        if property_doc:
            return PropertySchema(**property_doc)
        return None

    async def get_property_with_projection(self, filter_query: dict) -> dict:
        """Get a single property by filter with limited projection (returns raw dict)"""
        filter_query = dict(filter_query or {})
        filter_query["Pricelabs_SyncStatus"] = True
        projection = {
            "_id": 1,
            "operator_id": 1,
            "Listing_Name": 1,
            "listing_id": 1,
            "Photos": 1,
            "BookingId": 1,
            "BookingUrl": 1,
            "AirbnbId": 1,
            "AirbnbUrl": 1,
            "VRBOId": 1,
            "VRBOUrl": 1,
            "competitorIds": 1,
            "Amenities": 1
        }
        property_doc = await self.collection.find_one(filter_query, projection)
        if property_doc:
            # Convert ObjectId to string for JSON serialization
            if "_id" in property_doc:
                property_doc["_id"] = str(property_doc["_id"])
            return property_doc
        return None

    async def get_properties_for_csv(self, filter_query: dict = None, sort_by: dict = None) -> list[PropertySchema]:
        """Get multiple properties with pagination and sorting
        
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
        filter_query = dict(filter_query)
        filter_query["Pricelabs_SyncStatus"] = True
            
        cursor = self.collection.find(filter_query).sort(sort_by)
        properties = []
        async for doc in cursor:
            properties.append(PropertySchema(**doc))
        return properties

    async def get_properties_for_csv_optimized(self, filter_query: dict = None, sort_by: dict = None) -> list[dict]:
        """Get multiple properties with optimized projection (no schema validation, returns raw dicts)
        
        Args:
            filter_query: MongoDB filter query
            sort_by: MongoDB sort specification
        """
        if filter_query is None:
            filter_query = {}
        if sort_by is None:
            sort_by = {"_id": -1}
        filter_query = dict(filter_query)
        filter_query["Pricelabs_SyncStatus"] = True
            
        # Optimized projection for export_properties_to_excel - using nested structure
        projection = {
            "_id": 1,
            "operator_id": 1,
            "Listing_Name": 1,
            "Area": 1,
            "Room_Type": 1,
            "Property_Type": 1,
            "Occupancy": 1,  # Nested object with TM, NM, 7_days, 30_days
            "STLY_Var": 1,   # Nested object with Occ, ADR, RevPAR
            "STLM_Var": 1,   # Nested object with Occ, ADR, RevPAR
            "RevPAR": 1,     # Nested object with TM, NM
            "ADR": 1,        # Nested object with TM, NM
            "Pick_Up_Occ": 1, # Nested object with 7_Days, 14_Days, 30_Days
            "MPI": 1,        # Nested object with TM, NM, LYTM
            "Min_Rate_Threshold": 1,
            "Reviews": 1,    # Nested object with Airbnb, Booking, VRBO
            "Photos": 1,
            "BookingId": 1,
            "BookingUrl": 1,
            "AirbnbId": 1,
            "AirbnbUrl": 1,
            "VRBOId": 1,
            "VRBOUrl": 1,
            "BookingCom": 1  # Booking.com features: Genius, Mobile, Pref, Discounts
        }
        
        cursor = self.collection.find(filter_query, projection).sort(sort_by)
        properties = []
        async for doc in cursor:
            # Convert ObjectId to string for JSON serialization
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            properties.append(doc)
        return properties

    async def get_properties_for_content_cues_optimized(self, filter_query: dict = None, sort_by: dict = None) -> list[dict]:
        """Get properties optimized for content cues export with aggregated counts for photos, reviews, and amenities
        
        Args:
            filter_query: MongoDB filter query
            sort_by: MongoDB sort specification
        """
        if filter_query is None:
            filter_query = {}
        if sort_by is None:
            sort_by = {"_id": -1}
        filter_query = dict(filter_query)
        filter_query["Pricelabs_SyncStatus"] = True
            
        # Use aggregation pipeline to get all counts directly from database
        pipeline = [
            {"$match": filter_query},
            {"$sort": sort_by},
            {
                "$project": {
                    "_id": 1,
                    "operator_id": 1,
                    "Listing_Name": 1,
                    "Area": 1,
                    "Room_Type": 1,
                    "Property_Type": 1,
                    "BookingUrl": 1,
                    "AirbnbUrl": 1,
                    "VRBOUrl": 1,
                    "competitorIds": 1,
                    
                    # Photo counts by platform
                    "total_photos_booking": {"$size": {"$ifNull": ["$Photos.booking", []]}},
                    "total_photos_airbnb": {"$size": {"$ifNull": ["$Photos.airbnb", []]}},
                    "total_photos_vrbo": {"$size": {"$ifNull": ["$Photos.vrbo", []]}},
                    "total_photos": {
                        "$add": [
                            {"$size": {"$ifNull": ["$Photos.booking", []]}},
                            {"$size": {"$ifNull": ["$Photos.airbnb", []]}},
                            {"$size": {"$ifNull": ["$Photos.vrbo", []]}}
                        ]
                    },
                    "photos_with_captions_booking": {
                        "$size": {
                            "$filter": {
                                "input": {"$ifNull": ["$Photos.booking", []]},
                                "cond": {
                                    "$and": [
                                        {"$ne": ["$$this.caption", None]},
                                        {"$ne": ["$$this.caption", ""]}
                                    ]
                                }
                            }
                        }
                    },
                    "photos_with_captions_airbnb": {
                        "$size": {
                            "$filter": {
                                "input": {"$ifNull": ["$Photos.airbnb", []]},
                                "cond": {
                                    "$and": [
                                        {"$ne": ["$$this.caption", None]},
                                        {"$ne": ["$$this.caption", ""]}
                                    ]
                                }
                            }
                        }
                    },
                    "photos_with_captions_vrbo": {
                        "$size": {
                            "$filter": {
                                "input": {"$ifNull": ["$Photos.vrbo", []]},
                                "cond": {
                                    "$and": [
                                        {"$ne": ["$$this.caption", None]},
                                        {"$ne": ["$$this.caption", ""]}
                                    ]
                                }
                            }
                        }
                    },
                    
                    # Review counts by platform
                    "reviews_booking_total": {"$ifNull": ["$Reviews.Booking.Total_Rev", 0]},
                    "reviews_booking_score": {"$ifNull": ["$Reviews.Booking.Rev_Score", 0]},
                    "reviews_booking_last_date": "$Reviews.Booking.Last_Review_Date",
                    "reviews_booking_last_score": {"$ifNull": ["$Reviews.Booking.Last_Rev_Score", 0]},
                    
                    "reviews_airbnb_total": {"$ifNull": ["$Reviews.Airbnb.Total_Rev", 0]},
                    "reviews_airbnb_score": {"$ifNull": ["$Reviews.Airbnb.Rev_Score", 0]},
                    "reviews_airbnb_last_date": "$Reviews.Airbnb.Last_Review_Date",
                    "reviews_airbnb_last_score": {"$ifNull": ["$Reviews.Airbnb.Last_Rev_Score", 0]},
                    
                    "reviews_vrbo_total": {"$ifNull": ["$Reviews.VRBO.Total_Rev", 0]},
                    "reviews_vrbo_score": {"$ifNull": ["$Reviews.VRBO.Rev_Score", 0]},
                    "reviews_vrbo_last_date": "$Reviews.VRBO.Last_Review_Date",
                    "reviews_vrbo_last_score": {"$ifNull": ["$Reviews.VRBO.Last_Rev_Score", 0]},
                    
                    # Amenity counts by platform
                    "amenities_booking_count": {"$size": {"$ifNull": ["$Amenities.Booking", []]}},
                    "amenities_airbnb_count": {"$size": {"$ifNull": ["$Amenities.Airbnb", []]}},
                    "amenities_vrbo_count": {"$size": {"$ifNull": ["$Amenities.VRBO", []]}},
                    "amenities_total_count": {
                        "$add": [
                            {"$size": {"$ifNull": ["$Amenities.Booking", []]}},
                            {"$size": {"$ifNull": ["$Amenities.Airbnb", []]}},
                            {"$size": {"$ifNull": ["$Amenities.VRBO", []]}}
                        ]
                    }
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

    async def get_properties(self, filter_query: dict = None, skip: int = 0, limit: int = 10, sort_by: dict = None) -> list[PropertySchema]:
        """Get multiple properties with pagination and sorting
        
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
        filter_query = dict(filter_query)
        filter_query["Pricelabs_SyncStatus"] = True
            
        cursor = self.collection.find(filter_query).sort(sort_by).skip(skip).limit(limit)
        properties = []
        async for doc in cursor:
            properties.append(PropertySchema(**doc))
        return properties

    async def get_properties_optimized(self, filter_query: dict = None, skip: int = 0, limit: int = 10, sort_by: dict = None) -> list[PropertySchema]:
        """Get multiple properties with pagination and sorting (optimized with projection)
        
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
        filter_query = dict(filter_query)
        filter_query["Pricelabs_SyncStatus"] = True
        
        # Projection to only fetch fields needed for competitor comparison
        projection = {
            "_id": 1,
            "operator_id": 1,
            "Listing_Name": 1,
            "listing_id": 1,
            "Photos": 1,
            "Reviews": 1,
            "BookingId": 1,
            "BookingUrl": 1,
            "AirbnbId": 1,
            "AirbnbUrl": 1,
            "VRBOId": 1,
            "VRBOUrl": 1,
            "competitorIds": 1
        }
            
        cursor = self.collection.find(filter_query, projection).sort(sort_by).skip(skip).limit(limit)
        properties = []
        async for doc in cursor:
            properties.append(PropertySchema(**doc))
        return properties

    async def get_properties_with_projection_sliced_photos(self, filter_query: dict = None, skip: int = 0, limit: int = 10, sort_by: dict = None) -> list[PropertySchema]:
        """Get multiple properties with projection that excludes heavy fields and slices photos.
        - Excludes: Amenities, BookingCom, competitorIds
        - Photos: keep only first 2 from booking and airbnb
        """
        if filter_query is None:
            filter_query = {}
        if sort_by is None:
            sort_by = {"_id": -1}
        filter_query = dict(filter_query)
        filter_query["Pricelabs_SyncStatus"] = True

        # Build aggregation pipeline to slice nested arrays and exclude fields while keeping others
        pipeline = [
            {"$match": filter_query},
            {"$sort": sort_by},
            {"$set": {
                # Safely slice nested arrays even if missing
                "Photos.booking": {"$slice": [{"$ifNull": ["$Photos.booking", []]}, 2]},
                "Photos.airbnb": {"$slice": [{"$ifNull": ["$Photos.airbnb", []]}, 2]}
            }},
            {"$project": {
                "Amenities": 0,
                "BookingCom": 0,
                "Airbnb": 0,
                "competitorIds": 0
            }},
            {"$skip": skip},
            {"$limit": limit}
        ]

        cursor = self.collection.aggregate(pipeline)
        # properties: list[PropertySchema] = []
        # async for doc in cursor:
        #     properties.append(PropertySchema(**doc))
        data = []
        async for doc in cursor:
            doc['id'] = str(doc['_id'])  # convert ObjectId to string
            data.append(doc)
        return data

    async def get_properties_count(self, filter_query: dict = None) -> int:
        """Get total count of properties matching filter"""
        if filter_query is None:
            filter_query = {}
        filter_query = dict(filter_query)
        filter_query["Pricelabs_SyncStatus"] = True
        return await self.collection.count_documents(filter_query)

    async def update_property(self, property_id: str, update_data: dict) -> bool:
        """Update a property"""
        result = await self.collection.update_one(
            {"_id": ObjectId(property_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def update_status(self, property_id: str, status: str) -> bool:
        """Update the status of a property"""
        result = await self.collection.update_one(
            {"_id": ObjectId(property_id)},
            {"$set": {"status": status}}
        )
        return result.modified_count > 0

    async def delete_property(self, property_id: str) -> bool:
        """Delete a property"""
        result = await self.collection.delete_one({"_id": ObjectId(property_id)})
        return result.deleted_count > 0

    async def search_properties(self, search_query: str, skip: int = 0, limit: int = 10) -> list[PropertySchema]:
        """Search properties by listing name or area"""
        filter_query = {
            "$or": [
                {"Listing_Name": {"$regex": search_query, "$options": "i"}},
                {"Area": {"$regex": search_query, "$options": "i"}},
                {"Room_Type": {"$regex": search_query, "$options": "i"}}
            ]
        }
        filter_query["Pricelabs_SyncStatus"] = True
        cursor = self.collection.find(filter_query).skip(skip).limit(limit)
        properties = []
        async for doc in cursor:
            properties.append(PropertySchema(**doc))
        return properties

    async def search_properties_by_name(self, search_query: str, operator_id: str = None) -> list[PropertySchema]:
        """Search properties by listing name with optional operator_id filter (no pagination)"""
        filter_query = {
            "Listing_Name": {"$regex": search_query, "$options": "i"}
        }
        if operator_id:
            filter_query["operator_id"] = operator_id
        
        filter_query["Pricelabs_SyncStatus"] = True
        cursor = self.collection.find(filter_query).sort([("Listing_Name", 1)])
        properties = []
        async for doc in cursor:
            properties.append(PropertySchema(**doc))
        return properties

    async def remove_competitor_id_from_properties(self, competitor_id: str):
        """Remove a competitor ID from all properties that contain it and return their _ids."""
        # Find all documents that contain the competitor_id
        cursor = self.collection.find(
            {"competitorIds": competitor_id, "Pricelabs_SyncStatus": True},
            {"_id": 1}
        )
        docs = []
        async for doc in cursor:
            docs.append(doc)
        ids = [str(doc["_id"]) for doc in docs]

        if not ids:
            return []

        # Remove the competitor_id from competitorIds
        await self.collection.update_many(
            {"_id": {"$in": ids}},
            {"$pull": {"competitorIds": competitor_id}}
        )

        return ids
