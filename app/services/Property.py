from datetime import datetime
from app.models.Property import PropertyModel
from app.models.CompetitorProperty import CompetitorPropertyModel
from app.schemas.Property import PropertySchema, PropertyCreateSchema, PropertyUpdateSchema
from bson import ObjectId

class PropertyService:
    def __init__(self):
        self.property_model = PropertyModel()
        self.competitor_property_model = CompetitorPropertyModel()

    async def create_property(self, property_data: PropertyCreateSchema) -> dict:
        """Create a new property"""
        try:
            # Convert to dict and create property
            property_dict = property_data.model_dump()
            property_id = await self.property_model.create_property(property_dict)
            
            # Get created property
            created_property = await self.property_model.get_property({"_id": ObjectId(property_id)})
            if not created_property:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to retrieve created property"
                }

            return {
                "success": True,
                "data": created_property
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_property(self, property_id: str, operator_id: str = None) -> dict:
        """Get a property by ID"""
        try:
            # Build query with operator_id if provided
            query = {"_id": ObjectId(property_id)}
            if operator_id:
                query["operator_id"] = operator_id

            property_data = await self.property_model.get_property(query)
            if not property_data:
                return {
                    "success": False,
                    "data": None,
                    "error": "Property not found"
                }

            return {
                "success": True,
                "data": property_data
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_properties(self, page: int = 1, limit: int = 10, filter_query: dict = None, sort_by: dict = None) -> dict:
        """Get all properties with pagination and sorting"""
        try:
            import asyncio
            skip = (page - 1) * limit
            query = filter_query if filter_query is not None else {}
            
            # Run both queries in parallel for better performance
            properties, total = await asyncio.gather(
                self.property_model.get_properties(query, skip, limit, sort_by),
                self.property_model.get_properties_count(query)
            )
            total_pages = (total + limit - 1) // limit

            return {
                "success": True,
                "data": {
                    "properties": properties,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "total_pages": total_pages,
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

    async def get_properties_projected(self, page: int = 1, limit: int = 10, filter_query: dict = None, sort_by: dict = None) -> dict:
        """Get properties with projection and sliced photos to reduce payload size"""
        try:
            import asyncio
            skip = (page - 1) * limit
            query = filter_query if filter_query is not None else {}

            properties, total = await asyncio.gather(
                self.property_model.get_properties_with_projection_sliced_photos(query, skip, limit, sort_by),
                self.property_model.get_properties_count(query)
            )
            total_pages = (total + limit - 1) // limit

            return {
                "success": True,
                "data": {
                    "properties": properties,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "total_pages": total_pages,
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

    async def update_property(self, property_id: str, update_data: PropertyUpdateSchema) -> dict:
        """Update a property with competitor ID logic"""
        try:
            # Check if property exists
            existing_property = await self.property_model.get_property({"_id": ObjectId(property_id)})
            if not existing_property:
                return {
                    "success": False,
                    "data": None,
                    "error": "Property not found"
                }

            # If operator_id is being updated, validate it exists
            if update_data.operator_id is not None:
                # Here you might want to add validation for operator_id if needed
                pass

            # Handle competitor IDs logic - append competitor IDs to property
            if update_data.competitorIds:
                # Check if competitor IDs are provided to add to property
                competitor_ids_to_add = update_data.competitorIds
                current_competitor_ids = existing_property.competitorIds or []
                
                # Check for duplicates
                for competitor_id in competitor_ids_to_add:
                    if competitor_id in current_competitor_ids:
                        return {
                            "success": False,
                            "data": None,
                            "error": f"Competitor {competitor_id} for this property already exists"
                        }
                
                # Add all new competitor IDs
                current_competitor_ids.extend(competitor_ids_to_add)
                # Update the property with the new competitor IDs array
                update_data.competitorIds = current_competitor_ids

            # Update property
            update_dict = update_data.model_dump(exclude_unset=True)
            if not update_dict:
                return {
                    "success": False,
                    "data": None,
                    "error": "No data provided for update"
                }

            updated = await self.property_model.update_property(property_id, update_dict)
            if not updated:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to update property"
                }

            # Get updated property
            updated_property = await self.property_model.get_property({"_id": ObjectId(property_id)})
            return {
                "success": True,
                "data": updated_property
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def delete_property(self, property_id: str, operator_id: str = None) -> dict:
        """Delete a property"""
        try:
            # Build query with operator_id if provided
            query = {"_id": ObjectId(property_id)}
            if operator_id:
                query["operator_id"] = operator_id

            # Check if property exists
            existing_property = await self.property_model.get_property(query)
            if not existing_property:
                return {
                    "success": False,
                    "data": None,
                    "error": "Property not found"
                }

            # Delete property
            deleted = await self.property_model.delete_property(property_id)
            if not deleted:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to delete property"
                }

            return {
                "success": True,
                "data": "Property deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def search_properties(self, search_query: str, operator_id: str = None) -> dict:
        """Search properties by listing name with optional operator_id filter (no pagination)"""
        try:
            properties = await self.property_model.search_properties_by_name(search_query, operator_id)
            
            return {
                "success": True,
                "data": {
                    "properties": properties,
                    "total": len(properties)
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def filter_properties(self, filters: dict, page: int = 1, limit: int = 10, property_ids: list = None) -> dict:
        """Filter properties based on multiple criteria
        
        Args:
            filters: Filter dictionary
            page: Page number for pagination
            limit: Number of items per page
            property_ids: Optional list of property IDs to filter by
            
        Logic:
            - If both filters and property_ids: Apply filters first, then filter results to only include property_ids
            - If only property_ids: Return only those properties (no other filters)
            - If only filters: Apply filters only (current behavior)
            - If neither: Return all properties for operator
        """
        try:
            # Build MongoDB query
            query = {}
            
            # Handle property_ids and filters logic
            has_filters = filters and any([
                filters.get("operator_id"),
                filters.get("area"),
                filters.get("room_type"),
                filters.get("adr_range", {}).get("min") is not None or filters.get("adr_range", {}).get("max") is not None,
                filters.get("revpar_range", {}).get("min") is not None or filters.get("revpar_range", {}).get("max") is not None,
                filters.get("mpi_range", {}).get("min") is not None or filters.get("mpi_range", {}).get("max") is not None,
                filters.get("min_rate_threshold", {}).get("min") is not None or filters.get("min_rate_threshold", {}).get("max") is not None,
                any([v for v in filters.get("occupancy", {}).values() if isinstance(v, dict) and (v.get("min") is not None or v.get("max") is not None)]),
                any([v for v in filters.get("pickup", {}).values() if isinstance(v, dict) and (v.get("min") is not None or v.get("max") is not None)]),
                any([v for v in filters.get("stly_var", {}).values() if isinstance(v, dict) and (v.get("min") is not None or v.get("max") is not None)]),
                any([v for v in filters.get("stlm_var", {}).values() if isinstance(v, dict) and (v.get("min") is not None or v.get("max") is not None)]),
                any([v for k, v in filters.get("booking_features", {}).items() if v is not None]),
                any([v for k, v in filters.get("airbnb_features", {}).items() if v is not None]),
                any([v for k, v in filters.get("vrbo_features", {}).items() if v is not None]),
                any([v for platform in filters.get("reviews", {}).values() for v in platform.values() if isinstance(v, dict) and (v.get("min") is not None or v.get("max") is not None)])
            ])
            
            if property_ids and has_filters:
                # Both provided: Apply filters first, then filter by property_ids in Python
                pass  # Continue with filter logic below
            elif property_ids:
                # Only property_ids: Query only those properties
                try:
                    object_ids = [ObjectId(pid) for pid in property_ids if ObjectId.is_valid(pid)]
                    if object_ids:
                        query["_id"] = {"$in": object_ids}
                        # Still need operator_id if provided
                        if filters and filters.get("operator_id"):
                            query["operator_id"] = filters["operator_id"]
                    else:
                        return {"success": False, "data": None, "error": "Invalid property IDs format"}
                except Exception as e:
                    return {"success": False, "data": None, "error": f"Invalid property IDs: {str(e)}"}
            elif has_filters:
                # Only filters: Apply filters only (continue with filter logic below)
                pass
            else:
                # Neither provided - query all properties for operator
                if filters and filters.get("operator_id"):
                    query["operator_id"] = filters["operator_id"]
            
            # Apply filter logic if filters are provided
            if has_filters:
                # Basic Filters
                if filters.get("operator_id"):
                    query["operator_id"] = filters["operator_id"]  # Exact match for operator_id
                if filters.get("area"):
                    query["Area"] = {"$regex": f"^{filters['area']}$", "$options": "i"}  # Case-insensitive exact match
                if filters.get("room_type"):
                    query["Room_Type"] = {"$regex": f"^{filters['room_type']}$", "$options": "i"}  # Case-insensitive exact match

                # ADR Range
                if filters.get("adr_range") and (filters["adr_range"]["min"] is not None or filters["adr_range"]["max"] is not None):
                    query["ADR.TM"] = self._build_range_query(
                        filters["adr_range"]["min"],
                        filters["adr_range"]["max"],
                        as_string=False
                    )

                # RevPAR Range
                if filters.get("revpar_range") and (filters["revpar_range"]["min"] is not None or filters["revpar_range"]["max"] is not None):
                    query["RevPAR.TM"] = self._build_range_query(
                        filters["revpar_range"]["min"],
                        filters["revpar_range"]["max"],
                        as_string=False
                    )

                # MPI Range
                if filters.get("mpi_range") and (filters["mpi_range"]["min"] is not None or filters["mpi_range"]["max"] is not None):
                    query["MPI"] = self._build_range_query(
                        self._strip_percentage(filters["mpi_range"]["min"]),
                        self._strip_percentage(filters["mpi_range"]["max"]),
                        as_string=False
                    )

                # Min Rate Threshold
                if filters.get("min_rate_threshold") and (filters["min_rate_threshold"]["min"] is not None or filters["min_rate_threshold"]["max"] is not None):
                    query["Min_Rate_Threshold"] = self._build_range_query(
                        self._strip_percentage(filters["min_rate_threshold"]["min"]),
                        self._strip_percentage(filters["min_rate_threshold"]["max"]),
                        as_string=False
                    )

                # Occupancy Filters
                if filters.get("occupancy"):
                    self._add_occupancy_filters(query, filters["occupancy"])
                if filters.get("pickup"):
                    self._add_pickup_filters(query, filters["pickup"])

                # Performance Filters
                if filters.get("stly_var"):
                    self._add_stly_filters(query, filters["stly_var"])
                if filters.get("stlm_var"):
                    self._add_stlm_filters(query, filters["stlm_var"])

                # Platform Features
                if filters.get("booking_features"):
                    self._add_booking_feature_filters(query, filters["booking_features"])
                if filters.get("airbnb_features"):
                    self._add_airbnb_feature_filters(query, filters["airbnb_features"])
                if filters.get("vrbo_features"):
                    self._add_vrbo_feature_filters(query, filters["vrbo_features"])

                # Review Filters
                if filters.get("reviews"):
                    self._add_review_filters(query, filters["reviews"])

            print("MongoDB Query:", query)  # Debug print

            # Get filtered properties (run queries in parallel)
            import asyncio
            skip = (page - 1) * limit
            properties, total = await asyncio.gather(
                self.property_model.get_properties(query, skip, limit),
                self.property_model.get_properties_count(query)
            )
            
            # If both filters and property_ids were provided, filter results by property_ids
            if property_ids and has_filters:
                property_ids_set = set(property_ids)
                properties = [
                    prop for prop in properties 
                    if str(prop.id) in property_ids_set  # Access id attribute (Pydantic model)
                ]
                # Recalculate total for pagination
                total = len(properties)
                # Apply pagination manually since we filtered in Python
                properties = properties[skip:skip + limit]
            
            total_pages = (total + limit - 1) // limit

            return {
                "success": True,
                "data": {
                    "properties": properties,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "total_pages": total_pages,
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

    def _strip_percentage(self, value):
        """Helper method to strip percentage sign from string values and handle None"""
        if value is None:
            return None
        if isinstance(value, str):
            return value.rstrip('%')
        return value

    def _build_range_query(self, min_val, max_val, as_string=False):
        """Helper method to build MongoDB range query
        
        Args:
            min_val: Minimum value for the range
            max_val: Maximum value for the range
            as_string: If True, converts values to strings (for string fields)
        """
        if as_string:
            if min_val is not None and max_val is not None:
                return {"$gte": str(min_val), "$lte": str(max_val)}
            elif min_val is not None:
                return {"$gte": str(min_val)}
            elif max_val is not None:
                return {"$lte": str(max_val)}
        else:
            if min_val is not None and max_val is not None:
                return {"$gte": float(min_val), "$lte": float(max_val)}
            elif min_val is not None:
                return {"$gte": float(min_val)}
            elif max_val is not None:
                return {"$lte": float(max_val)}
        return None

    def _add_occupancy_filters(self, query: dict, occupancy_filters: dict):
        """Add occupancy-related filters to query"""
        field_mapping = {
            "tm": "TM",
            "nm": "NM",
            "7_days": "7_days",
            "30_days": "30_days"
        }
        
        for period, range_vals in occupancy_filters.items():
            if period in field_mapping:
                field = f"Occupancy.{field_mapping[period]}"
                if range_vals["min"] is not None or range_vals["max"] is not None:
                    query[field] = self._build_range_query(
                        self._strip_percentage(range_vals["min"]),
                        self._strip_percentage(range_vals["max"]),
                        as_string=False
                    )

    def _add_pickup_filters(self, query: dict, pickup_filters: dict):
        """Add pickup-related filters to query"""
        field_mapping = {
            "7_days": "7_Days",
            "14_days": "14_Days",
            "30_days": "30_Days"
        }
        
        for period, range_vals in pickup_filters.items():
            if period in field_mapping:
                field = f"Pick_Up_Occ.{field_mapping[period]}"
                if range_vals["min"] is not None or range_vals["max"] is not None:
                    query[field] = self._build_range_query(
                        self._strip_percentage(range_vals["min"]),
                        self._strip_percentage(range_vals["max"]),
                        as_string=False
                    )

    def _add_stly_filters(self, query: dict, stly_filters: dict):
        """Add STLY variance filters to query"""
        field_mapping = {
            "occupancy": "Occ",
            "adr": "ADR",
            "revpar": "RevPAR"
        }
        
        for metric, range_vals in stly_filters.items():
            if metric in field_mapping:
                field = f"STLY_Var.{field_mapping[metric]}"
                if range_vals["min"] is not None or range_vals["max"] is not None:
                    query[field] = self._build_range_query(
                        self._strip_percentage(range_vals["min"]),
                        self._strip_percentage(range_vals["max"]),
                        as_string=False
                    )

    def _add_stlm_filters(self, query: dict, stlm_filters: dict):
        """Add STLM variance filters to query"""
        field_mapping = {
            "occupancy": "Occ",
            "adr": "ADR",
            "revpar": "RevPAR"
        }
        
        for metric, range_vals in stlm_filters.items():
            if metric in field_mapping:
                field = f"STLM_Var.{field_mapping[metric]}"
                if range_vals["min"] is not None or range_vals["max"] is not None:
                    query[field] = self._build_range_query(
                        self._strip_percentage(range_vals["min"]),
                        self._strip_percentage(range_vals["max"]),
                        as_string=False
                    )

    def _add_booking_feature_filters(self, query: dict, booking_features: dict):
        """Add Booking.com feature filters to query"""
        field_mapping = {
            "genius": "Genius",
            "mobile": "Mobile",
            "preferred": "Pref",
            "weekly": "Weekly",
            "monthly": "Monthly",
            "lastminute": "LM_Disc"
        }
        
        for feature, value in booking_features.items():
            if value is not None and feature in field_mapping:
                # Case-insensitive match for Yes/No values
                query[f"BookingCom.{field_mapping[feature]}"] = {
                    "$regex": f"^{'Yes' if value else 'No'}$",
                    "$options": "i"
                }

    def _add_airbnb_feature_filters(self, query: dict, airbnb_features: dict):
        """Add Airbnb feature filters to query"""
        field_mapping = {
            "weekly": "Weekly",
            "monthly": "Monthly",
            "member": "Member",
            "lastminute": "LM_Disc"
        }
        
        for feature, value in airbnb_features.items():
            if value is not None and feature in field_mapping:
                # Case-insensitive match for Yes/No values
                query[f"Airbnb.{field_mapping[feature]}"] = {
                    "$regex": f"^{'Yes' if value else 'No'}$",
                    "$options": "i"
                }

    def _add_vrbo_feature_filters(self, query: dict, vrbo_features: dict):
        """Add VRBO feature filters to query"""
        field_mapping = {
            "weekly": "Weekly",
            "monthly": "Monthly"
        }
        
        for feature, value in vrbo_features.items():
            if value is not None and feature in field_mapping:
                # Case-insensitive match for Yes/No values
                query[f"VRBO.{field_mapping[feature]}"] = {
                    "$regex": f"^{'Yes' if value else 'No'}$",
                    "$options": "i"
                }

    def _add_review_filters(self, query: dict, review_filters: dict):
        """Add review-related filters to query"""
        platform_mapping = {
            "booking": "Booking",
            "airbnb": "Airbnb",
            "vrbo": "VRBO"
        }
        
        for platform, filters in review_filters.items():
            if platform in platform_mapping:
                platform_name = platform_mapping[platform]
                
                # Review Score
                score_range = filters["score"]
                if score_range["min"] is not None or score_range["max"] is not None:
                    query[f"Reviews.{platform_name}.Rev_Score"] = self._build_range_query(
                        score_range["min"],
                        score_range["max"]
                    )
                
                # Total Reviews
                total_range = filters["total"]
                if total_range["min"] is not None or total_range["max"] is not None:
                    query[f"Reviews.{platform_name}.Total_Rev"] = self._build_range_query(
                        total_range["min"],
                        total_range["max"]
                    )
