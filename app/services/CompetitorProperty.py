from datetime import datetime
from app.models.CompetitorComparsionQueue import CompetitorComparisonQueue
from app.models.CompetitorProperty import CompetitorPropertyModel
from app.models.Property import PropertyModel
from app.schemas.CompetitorProperty import CompetitorPropertySchema, CompetitorPropertyCreateSchema, CompetitorPropertyUpdateSchema
from bson import ObjectId
from typing import List

class CompetitorPropertyService:
    def __init__(self):
        self.competitor_property_model = CompetitorPropertyModel()
        self.property_model = PropertyModel()
        self.competitor_comparison_queue = CompetitorComparisonQueue()

    async def create_competitor_property(self, competitor_property_data: CompetitorPropertyCreateSchema) -> dict:
        """Create a new competitor property"""
        try:
            # Convert input to dict
            input_dict = competitor_property_data.model_dump()
            
            # Validate against full schema - Pydantic will automatically set defaults/None for missing fields
            from app.schemas.CompetitorProperty import CompetitorPropertySchema
            validated_data = CompetitorPropertySchema(**input_dict)
            
            # Convert to dict for database storage, excluding None values
            competitor_property_dict = validated_data.model_dump()
            
            competitor_property_id = await self.competitor_property_model.create_competitor_property(competitor_property_dict)

            return {
                "success": True,
                "data": {"id": competitor_property_id}
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def create_multiple_competitor_properties(self, competitor_properties_data: List[CompetitorPropertyCreateSchema]) -> dict:
        """Create multiple competitor properties in one request"""
        try:
            created_ids = []
            errors = []
            
            for i, competitor_data in enumerate(competitor_properties_data):
                try:
                    # Convert input to dict
                    input_dict = competitor_data.model_dump()
                    from app.schemas.CompetitorProperty import CompetitorPropertySchema
                    validated_data = CompetitorPropertySchema(**input_dict)
                    
                    # Convert to dict for database storage, excluding None values
                    competitor_property_dict = validated_data.model_dump()
                    
                    competitor_property_id = await self.competitor_property_model.create_competitor_property(competitor_property_dict)
                    created_ids.append(competitor_property_id)
                    
                except Exception as e:
                    errors.append(f"Item {i}: {str(e)}")
            
            if errors and not created_ids:
                # All failed
                return {
                    "success": False,
                    "data": None,
                    "error": f"All competitor properties failed to create. Errors: {'; '.join(errors)}"
                }
            elif errors:
                # Some failed, some succeeded
                return {
                    "success": True,
                    "data": {
                        "ids": created_ids,
                        "errors": errors,
                        "message": f"Created {len(created_ids)} competitor properties, {len(errors)} failed"
                    }
                }
            else:
                # All succeeded
                return {
                    "success": True,
                    "data": {
                        "ids": created_ids,
                        "message": f"Successfully created {len(created_ids)} competitor properties"
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_competitor_property(self, competitor_property_id: str) -> dict:
        """Get a competitor property by ID"""
        try:
            query = {"_id": ObjectId(competitor_property_id)}
            competitor_property_data = await self.competitor_property_model.get_competitor_property(query)
            if not competitor_property_data:
                return {
                    "success": False,
                    "data": None,
                    "error": "Competitor property not found"
                }

            return {
                "success": True,
                "data": competitor_property_data
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_competitor_properties(self, page: int = 1, limit: int = 10, filter_query: dict = None, sort_by: dict = None) -> dict:
        """Get all competitor properties with pagination and sorting"""
        try:
            import asyncio
            skip = (page - 1) * limit
            query = filter_query if filter_query is not None else {}
            
            # Run queries in parallel for better performance
            competitor_properties, total = await asyncio.gather(
                self.competitor_property_model.get_competitor_properties(query, skip, limit, sort_by),
                self.competitor_property_model.get_competitor_properties_count(query)
            )
            total_pages = (total + limit - 1) // limit

            return {
                "success": True,
                "data": {
                    "competitorProperties": competitor_properties,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "totalPages": total_pages,
                        "limit": limit
                    }
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def update_competitor_property(self, competitor_property_id: str, update_data: CompetitorPropertyUpdateSchema) -> dict:
        """Update a competitor property - only update fields that are not already present"""
        try:
            # Check if competitor property exists
            existing_competitor_property = await self.competitor_property_model.get_competitor_property({"_id": ObjectId(competitor_property_id)})
            if not existing_competitor_property:
                return {
                    "success": False,
                    "data": None,
                    "error": "Competitor property not found"
                }

            # Get update data as dict
            update_dict = update_data.model_dump(exclude_unset=True)
            if not update_dict:
                return {
                    "success": False,
                    "data": None,
                    "error": "No data provided for update"
                }

            # Filter out fields that are already present (not None/empty)
            fields_to_update = {}
            for field, value in update_dict.items():
                if field in ["operatorId", "bookingId", "airbnbId", "vrboId", "bookingLink", "airbnbLink", "vrboLink"]:
                    # Only update these fields if they are not already present in the existing record
                    existing_value = getattr(existing_competitor_property, field, None)
                    if existing_value is None or existing_value == "":
                        fields_to_update[field] = value
                else:
                    # For other fields (numPhotos, captionedCount, etc.), always update
                    fields_to_update[field] = value

            if not fields_to_update:
                return {
                    "success": False,
                    "data": None,
                    "error": "All provided fields are already present in the competitor property"
                }

            # Add updatedAt timestamp
            fields_to_update["updatedAt"] = datetime.utcnow()

            updated = await self.competitor_property_model.update_competitor_property(competitor_property_id, fields_to_update)
            if not updated:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to update competitor property"
                }

            # Get updated competitor property
            updated_competitor_property = await self.competitor_property_model.get_competitor_property({"_id": ObjectId(competitor_property_id)})
            return {
                "success": True,
                "data": updated_competitor_property
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def delete_competitor_property(self, competitor_property_id: str) -> dict:
        """Delete a competitor property and remove its ID from associated properties"""
        try:
            # Check if competitor property exists
            existing_competitor_property = await self.competitor_property_model.get_competitor_property({"_id": ObjectId(competitor_property_id)})
            if not existing_competitor_property:
                return {
                    "success": False,
                    "data": None,
                    "error": "Competitor property not found"
                }

            # Remove competitor ID from all properties that contain it
            properties_updated = await self.property_model.remove_competitor_id_from_properties(competitor_property_id)

            # Delete competitor property
            deleted = await self.competitor_property_model.delete_competitor_property(competitor_property_id)
            
            for propertyId in properties_updated:
            
                comparison_queue = self.competitor_comparison_queue.collection.find_one_and_update(
                        {"propertyId": propertyId, "operator_id": existing_competitor_property.operatorId},
                        {
                            "$set": {"updated_at": datetime.utcnow()},
                            "$setOnInsert": {
                                "propertyId": str(propertyId),
                                "operator_id": existing_competitor_property.operatorId,
                                "status":"pending",
                                "created_at": datetime.utcnow()
                            }
                        },
                        upsert=True,
                        return_document=True
                    )
            
            if not deleted:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to delete competitor property"
                }

            return {
                "success": True,
                "data": {
                    "message": "Competitor property deleted successfully",
                    "properties_updated": properties_updated
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_competitor_properties_by_operator_id(self, operator_id: str, page: int = 1, limit: int = 10) -> dict:
        """Get competitor properties by operator ID"""
        try:
            skip = (page - 1) * limit
            competitor_properties = await self.competitor_property_model.get_competitor_properties_by_operator_id(operator_id, skip, limit)
            total = len(competitor_properties) 
            total_pages = (total + limit - 1) // limit

            return {
                "success": True,
                "data": {
                    "competitorProperties": competitor_properties,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "totalPages": total_pages,
                        "limit": limit
                    }
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_competitor_properties_by_property_ids(self, property_ids: list[str], page: int = 1, limit: int = 10) -> dict:
        """Get competitor properties that contain any of the specified property IDs"""
        try:
            skip = (page - 1) * limit
            competitor_properties = await self.competitor_property_model.get_competitor_properties_by_property_ids(property_ids, skip, limit)
            total = len(competitor_properties)  # Note: This is a simplified count, for production you might want a separate count method
            total_pages = (total + limit - 1) // limit

            return {
                "success": True,
                "data": {
                    "competitorProperties": competitor_properties,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "totalPages": total_pages,
                        "limit": limit
                    }
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_competitor_properties_by_operator_and_property_ids(self, operator_id: str, property_ids: list[str], page: int = 1, limit: int = 10) -> dict:
        """Get competitor properties by operator ID and property IDs"""
        try:
            skip = (page - 1) * limit
            competitor_properties = await self.competitor_property_model.get_competitor_properties_by_operator_and_property_ids(operator_id, property_ids, skip, limit)
            total = len(competitor_properties)  # Note: This is a simplified count, for production you might want a separate count method
            total_pages = (total + limit - 1) // limit

            return {
                "success": True,
                "data": {
                    "competitorProperties": competitor_properties,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "totalPages": total_pages,
                        "limit": limit
                    }
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def update_photo_counts(self, competitor_property_id: str, num_photos: int, captioned_count: int, missing_caption_count: int) -> dict:
        """Update photo counts for a competitor property"""
        try:
            # Check if competitor property exists
            existing_competitor_property = await self.competitor_property_model.get_competitor_property({"_id": ObjectId(competitor_property_id)})
            if not existing_competitor_property:
                return {
                    "success": False,
                    "data": None,
                    "error": "Competitor property not found"
                }

            # Update photo counts
            updated = await self.competitor_property_model.update_photo_counts(competitor_property_id, num_photos, captioned_count, missing_caption_count)
            if not updated:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to update photo counts"
                }

            # Get updated competitor property
            updated_competitor_property = await self.competitor_property_model.get_competitor_property({"_id": ObjectId(competitor_property_id)})
            return {
                "success": True,
                "data": updated_competitor_property
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def calculate_photo_counts(self, property_photos: list) -> dict:
        """Calculate photo counts from property photos list"""
        try:
            if not property_photos:
                return {
                    "numPhotos": None,
                    "captionedCount": None,
                    "missingCaptionCount": None
                }

            num_photos = len(property_photos)
            captioned_count = sum(1 for photo in property_photos if photo.get("hasCaption", False) and photo.get("caption"))
            missing_caption_count = num_photos - captioned_count

            return {
                "numPhotos": num_photos,
                "captionedCount": captioned_count,
                "missingCaptionCount": missing_caption_count
            }
        except Exception as e:
            return {
                "numPhotos": None,
                "captionedCount": None,
                "missingCaptionCount": None
            }

    async def get_competitors_by_property_id(self, property_id: str) -> dict:
        """Get competitor properties for a given property ID"""
        try:
            # First, get the property to extract competitor IDs
            property_data = await self.property_model.get_property({"_id": ObjectId(property_id)})
            if not property_data:
                return {
                    "success": False,
                    "data": None,
                    "error": "Property not found"
                }

            # Extract competitor IDs from the property
            competitor_ids = getattr(property_data, 'competitorIds', [])
            if not competitor_ids:
                return {
                    "success": True,
                    "data": {
                        "competitors": [],
                        "message": "No competitors found for this property"
                    }
                }

            # Get competitor properties by their IDs
            competitors = await self.competitor_property_model.get_competitors_by_ids(competitor_ids)
            
            # Format the response with only the required fields
            formatted_competitors = []
            for competitor in competitors:
                competitor_data = {
                    "id": str(competitor.id),
                    "operatorId": competitor.operatorId,
                    "bookingId": competitor.bookingId,
                    "airbnbId": competitor.airbnbId,
                    "vrboId": competitor.vrboId,
                    "bookingLink": competitor.bookingLink,
                    "airbnbLink": competitor.airbnbLink,
                    "vrboLink": competitor.vrboLink,
                    "status": competitor.status
                }
                formatted_competitors.append(competitor_data)

            return {
                "success": True,
                "data": {
                    "competitors": formatted_competitors,
                    "total": len(formatted_competitors)
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }