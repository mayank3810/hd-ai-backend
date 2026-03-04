from app.helpers.Database import MongoDB
from bson import ObjectId
from app.schemas.CompetitorComparison import CompetitorComparisonViewSchema
from datetime import datetime
import os

class CompetitorComparisonModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="CompetitorComparisons"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_competitor_comparison(self, comparison_data: dict) -> str:
        """Create a new competitor comparison"""
        result = await self.collection.insert_one(comparison_data)
        return str(result.inserted_id)

    async def get_competitor_comparison(self, filter_query: dict) -> CompetitorComparisonViewSchema:
        """Get a single competitor comparison by filter"""
        comparison_doc = await self.collection.find_one(filter_query)
        if comparison_doc:
            return CompetitorComparisonViewSchema(**comparison_doc)
        return None

    async def get_competitor_comparisons(self, filter_query: dict = None, skip: int = 0, limit: int = 10, sort_by: dict = None) -> list[CompetitorComparisonViewSchema]:
        """Get multiple competitor comparisons with pagination and sorting"""
        if filter_query is None:
            filter_query = {}
        if sort_by is None:
            sort_by = {"_id": -1}  # Default sort by _id (which includes timestamp), newest first
            
        cursor = self.collection.find(filter_query).sort(list(sort_by.items())).skip(skip).limit(limit)
        comparisons = []
        async for doc in cursor:
            comparisons.append(CompetitorComparisonViewSchema(**doc))
        return comparisons

    async def get_competitor_comparisons_count(self, filter_query: dict = None) -> int:
        """Get total count of competitor comparisons matching filter"""
        if filter_query is None:
            filter_query = {}
        return await self.collection.count_documents(filter_query)

    async def update_competitor_comparison(self, comparison_id: str, update_data: dict) -> bool:
        """Update a competitor comparison"""
        result = await self.collection.update_one(
            {"_id": ObjectId(comparison_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def delete_competitor_comparison(self, comparison_id: str) -> bool:
        """Delete a competitor comparison"""
        result = await self.collection.delete_one({"_id": ObjectId(comparison_id)})
        return result.deleted_count > 0

    async def get_competitor_comparisons_by_operator_id(self, operator_id: str, skip: int = 0, limit: int = 10) -> list[CompetitorComparisonViewSchema]:
        """Get competitor comparisons by operator ID"""
        filter_query = {"operator_id": operator_id}
        cursor = self.collection.find(filter_query).skip(skip).limit(limit)
        comparisons = []
        async for doc in cursor:
            comparisons.append(CompetitorComparisonViewSchema(**doc))
        return comparisons

    async def get_competitor_comparison_by_operator_and_property_id(self, operator_id: str, property_id: str) -> CompetitorComparisonViewSchema:
        """Get competitor comparison by operator ID and property ID"""
        filter_query = {
            "operator_id": operator_id,
            "propertyId": property_id
        }
        comparison_doc = await self.collection.find_one(filter_query)
        if comparison_doc:
            return CompetitorComparisonViewSchema(**comparison_doc)
        return None

    async def upsert_competitor_comparison(self, operator_id: str, property_id: str, comparison_data: dict) -> str:
        """Create or update a competitor comparison"""
        filter_query = {
            "operator_id": operator_id,
            "propertyId": property_id
        }
        
        # Add updated_at timestamp
        comparison_data["updated_at"] = datetime.utcnow()
        
        result = await self.collection.update_one(
            filter_query,
            {"$set": comparison_data},
            upsert=True
        )
        
        if result.upserted_id:
            return str(result.upserted_id)
        else:
            # Return the existing document ID
            existing_doc = await self.collection.find_one(filter_query)
            return str(existing_doc["_id"])

    async def get_comparisons_for_ai_analysis(self, operator_id: str) -> list[dict]:
        """Get competitor comparisons with AI analysis data for export"""
        try:
            # Projection for AI analysis - only fields needed for AI insights
            # Updated to include platform-specific fields (Booking and Airbnb)
            projection = {
                "_id": 1,
                "operator_id": 1,
                "propertyId": 1,
                "aiPhotoAnalysisBooking": 1,
                "aiPhotoAnalysisAirbnb": 1,
                "competitors": 1,
                # Booking platform-specific fields
                "reviewAnalysisOwnBooking": 1,
                "reviewSuggestionsBasedOnOwnBooking": 1,
                "reviewAnalysisCompetitorBooking": 1,
                "reviewSuggestionsBasedOnCompetitorBooking": 1,
                "topAreaAmenitiesMissingBooking": 1,
                "conversionBoostersBooking": 1,
                # Airbnb platform-specific fields
                "reviewAnalysisOwnAirbnb": 1,
                "reviewSuggestionsBasedOnOwnAirbnb": 1,
                "reviewAnalysisCompetitorAirbnb": 1,
                "reviewSuggestionsBasedOnCompetitorAirbnb": 1,
                "topAreaAmenitiesMissingAirbnb": 1,
                "conversionBoostersAirbnb": 1,
                # Legacy fields (for backward compatibility)
                "reviewAnalysisOwn": 1,
                "reviewSuggestionsBasedOnOwn": 1,
                "reviewAnalysisCompetitor": 1,
                "reviewSuggestionsBasedOnCompetitor": 1,
                "topAreaAmenitiesMissing": 1
            }
            
            filter_query = {"operator_id": operator_id}
            cursor = self.collection.find(filter_query, projection)
            
            comparisons = []
            async for doc in cursor:
                comparisons.append(doc)
            
            return comparisons
        except Exception as e:
            print(f"Error fetching comparisons for AI analysis: {e}")
            return []

    async def get_comparisons_for_ai_analysis_by_property_ids(self, property_ids: list[str]) -> list[dict]:
        """Get competitor comparisons with AI analysis data for specific properties (optimized)"""
        try:
            # Projection for AI analysis - only fields needed for AI insights
            # Updated to include platform-specific fields (Booking and Airbnb)
            projection = {
                "_id": 1,
                "operator_id": 1,
                "propertyId": 1,
                "aiPhotoAnalysisBooking": 1,
                "aiPhotoAnalysisAirbnb": 1,
                "competitors": 1,
                # Booking platform-specific fields
                "reviewAnalysisOwnBooking": 1,
                "reviewSuggestionsBasedOnOwnBooking": 1,
                "reviewAnalysisCompetitorBooking": 1,
                "reviewSuggestionsBasedOnCompetitorBooking": 1,
                "topAreaAmenitiesMissingBooking": 1,
                "conversionBoostersBooking": 1,
                # Airbnb platform-specific fields
                "reviewAnalysisOwnAirbnb": 1,
                "reviewSuggestionsBasedOnOwnAirbnb": 1,
                "reviewAnalysisCompetitorAirbnb": 1,
                "reviewSuggestionsBasedOnCompetitorAirbnb": 1,
                "topAreaAmenitiesMissingAirbnb": 1,
                "conversionBoostersAirbnb": 1,
                # Legacy fields (for backward compatibility)
                "reviewAnalysisOwn": 1,
                "reviewSuggestionsBasedOnOwn": 1,
                "reviewAnalysisCompetitor": 1,
                "reviewSuggestionsBasedOnCompetitor": 1,
                "topAreaAmenitiesMissing": 1
            }
            
            # Filter by specific property IDs instead of operator_id (more targeted)
            filter_query = {"propertyId": {"$in": property_ids}}
            cursor = self.collection.find(filter_query, projection)
            
            comparisons = []
            async for doc in cursor:
                comparisons.append(doc)
            
            return comparisons
        except Exception as e:
            print(f"Error fetching comparisons for AI analysis by property IDs: {e}")
            return []

    async def add_image_caption(self, operator_id: str, property_id: str, source: str, image_caption: dict) -> bool:
        """Add image caption to the appropriate array based on source"""
        filter_query = {
            "operator_id": operator_id,
            "propertyId": property_id
        }
        
        # Determine the field name based on source
        field_name = f"imageCaptions{source.capitalize()}"
        
        # Check if image with same imageId already exists
        existing_doc = await self.collection.find_one(filter_query)
        if existing_doc and field_name in existing_doc:
            # Check if image with same imageId already exists
            for existing_caption in existing_doc[field_name]:
                if existing_caption.get("imageId") == image_caption["imageId"]:
                    # Update existing caption
                    result = await self.collection.update_one(
                        filter_query,
                        {
                            "$set": {
                                f"{field_name}.$[elem].caption": image_caption["caption"],
                                f"{field_name}.$[elem].generatedAt": image_caption["generatedAt"]
                            },
                            "updated_at": datetime.utcnow()
                        },
                        array_filters=[{"elem.imageId": image_caption["imageId"]}]
                    )
                    return result.modified_count > 0
        
        # Add new caption to array
        result = await self.collection.update_one(
            filter_query,
            {
                "$push": {field_name: image_caption},
                "$set": {"updated_at": datetime.utcnow()}
            },
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
