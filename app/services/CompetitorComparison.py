from datetime import datetime, timedelta
from typing import List, Dict, Any, Literal
from app.models.CompetitorComparsionQueue import CompetitorComparisonQueue
from app.models.Property import PropertyModel
from app.models.CompetitorProperty import CompetitorPropertyModel
from app.models.CompetitorComparison import CompetitorComparisonModel
from bson import ObjectId
import logging
import hashlib
import json

class CompetitorComparisonService:
    def __init__(self):
        self.property_model = PropertyModel()
        self.competitor_property_model = CompetitorPropertyModel()
        self.competitor_comparison_model = CompetitorComparisonModel()
        self.competitor_comparison_queue = CompetitorComparisonQueue()
        # Simple in-memory cache with TTL
        self._cache = {}
        self._cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes

    def _generate_cache_key(self, operator_id: str, page: int, limit: int) -> str:
        """Generate a cache key for the request"""
        key_data = f"{operator_id}:{page}:{limit}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> dict:
        """Get data from cache if it exists and is not expired"""
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self._cache_ttl:
                logging.info(f"Cache hit for key: {cache_key}")
                return cached_data
            else:
                # Remove expired cache entry
                del self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, data: dict):
        """Store data in cache with timestamp"""
        self._cache[cache_key] = (data, datetime.now())
        logging.info(f"Data cached with key: {cache_key}")

    def clear_cache_for_operator(self, operator_id: str):
        """Clear cache entries for a specific operator"""
        keys_to_remove = [key for key in self._cache.keys() if key.startswith(hashlib.md5(operator_id.encode()).hexdigest()[:8])]
        for key in keys_to_remove:
            del self._cache[key]
        logging.info(f"Cleared {len(keys_to_remove)} cache entries for operator: {operator_id}")

    def clear_all_cache(self):
        """Clear all cache entries"""
        self._cache.clear()
        logging.info("All cache entries cleared")

    async def get_comparisons_by_operator_id(self, operator_id: str, page: int = 1, limit: int = 10) -> dict:
        """
        Get all properties for operator and generate comparison reports for each property
        with their competitors. Optimized version with batch queries, reduced processing, and caching.
        """
        try:
            # Check cache first
            cache_key = self._generate_cache_key(operator_id, page, limit)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result
            # Get all properties for the operator with optimized projection (run in parallel)
            import asyncio
            skip = (page - 1) * limit
            properties, total = await asyncio.gather(
                self.property_model.get_properties_optimized(
                    {"operator_id": operator_id}, 
                    skip, 
                    limit
                ),
                self.property_model.get_properties_count({"operator_id": operator_id})
            )
            total_pages = (total + limit - 1) // limit

            if not properties:
                return {
                    "success": True,
                    "data": {
                        "comparisons": [],
                        "pagination": {
                            "total": total,
                            "page": page,
                            "totalPages": total_pages,
                            "limit": limit
                        }
                    }
                }

            # Batch fetch all competitor data to avoid N+1 queries
            all_competitor_ids = []
            property_competitor_map = {}
            
            for property_data in properties:
                competitor_ids = getattr(property_data, 'competitorIds', []) or []
                property_competitor_map[str(property_data.id)] = competitor_ids
                all_competitor_ids.extend(competitor_ids)
            
            # Remove duplicates and fetch all competitors in one query
            unique_competitor_ids = list(set(all_competitor_ids))
            competitors_data = {}
            if unique_competitor_ids:
                competitors = await self.competitor_property_model.get_competitors_by_ids_optimized(unique_competitor_ids)
                competitors_data = {str(comp.id): comp for comp in competitors}

            # Generate comparison reports for each property
            comparisons = []
            for property_data in properties:
                property_id = str(property_data.id)
                competitor_ids = property_competitor_map.get(property_id, [])
                
                # Get competitors for this property from pre-fetched data
                property_competitors = [competitors_data.get(comp_id) for comp_id in competitor_ids if comp_id in competitors_data]
                
                comparison_report = self._generate_comparison_report_optimized(property_data, property_competitors)
                if comparison_report:
                    comparisons.append(comparison_report)

            result = {
                "success": True,
                "data": {
                    "comparisons": comparisons,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "totalPages": total_pages,
                        "limit": limit
                    }
                }
            }
            
            # Cache the result
            self._set_cache(cache_key, result)
            return result
        except Exception as e:
            logging.error(f"Error getting comparisons by operator ID: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    def _generate_comparison_report_optimized(self, property_data, competitors: List) -> Dict[str, Any]:
        """
        Generate a comparison report for a single property with its competitors (optimized version)
        """
        try:
            property_id = str(property_data.id)
            operator_id = property_data.operator_id

            # Get property basic info
            property_info = {
                "propertyId": property_id,
                "operatorId": operator_id,
                "listingName": getattr(property_data, 'Listing_Name', None),
                "photos": getattr(property_data, 'Photos', None),
                "bookingId": getattr(property_data, 'BookingId', None),
                "bookingLink": getattr(property_data, 'BookingUrl', None),
                "airbnbId": getattr(property_data, 'AirbnbId', None),
                "airbnbLink": getattr(property_data, 'AirbnbUrl', None),
                "vrboId": getattr(property_data, 'VRBOId', None),
                "vrboLink": getattr(property_data, 'VRBOUrl', None)
            }

            # Get photo counts and captions for property (optimized)
            property_photos = self._get_property_photos_data_optimized(property_data)
            property_info.update(property_photos)

            # Get review data for property (optimized)
            property_reviews = self._get_property_reviews_data_optimized(property_data)
            property_info.update(property_reviews)

            # Process competitors (already fetched)
            competitor_reports = []
            for competitor in competitors:
                if competitor:
                    competitor_data = self._get_competitor_comparison_data_optimized(competitor, property_data)
                    if competitor_data:
                        competitor_reports.append(competitor_data)

            return {
                **property_info,
                "competitors": competitor_reports
            }

        except Exception as e:
            logging.error(f"Error generating comparison report for property {property_id}: {str(e)}")
            return None

    async def _generate_comparison_report(self, property_data) -> Dict[str, Any]:
        """
        Generate a comparison report for a single property with its competitors
        """
        try:
            property_id = str(property_data.id)
            operator_id = property_data.operator_id

            # Get property basic info
            property_info = {
                "propertyId": property_id,
                "operatorId": operator_id,
                "listingName": getattr(property_data, 'Listing_Name', None),
                "photos":getattr(property_data, 'Photos', None),
                "bookingId": getattr(property_data, 'BookingId', None),
                "bookingLink": getattr(property_data, 'BookingUrl', None),
                "airbnbId": getattr(property_data, 'AirbnbId', None),
                "airbnbLink": getattr(property_data, 'AirbnbUrl', None),
                "vrboId": getattr(property_data, 'VRBOId', None),
                "vrboLink": getattr(property_data, 'VRBOUrl', None)
            }

            # Get photo counts and captions for property
            property_photos = self._get_property_photos_data(property_data)
            property_info.update(property_photos)

            # Get review data for property
            property_reviews = self._get_property_reviews_data(property_data)
            property_info.update(property_reviews)

            # Get competitors for this property
            competitor_ids = getattr(property_data, 'competitorIds', []) or []
            competitors = []

            for competitor_id in competitor_ids:
                competitor_data = await self._get_competitor_comparison_data(competitor_id, property_data)
                if competitor_data:
                    competitors.append(competitor_data)

            return {
                **property_info,
                "competitors": competitors
            }

        except Exception as e:
            logging.error(f"Error generating comparison report for property {property_id}: {str(e)}")
            return None

    def _get_property_photos_data_optimized(self, property_data) -> Dict[str, Any]:
        """
        Extract photo counts and caption data from property photos (optimized version)
        """
        photos_data = {
            "bookingPhotos": {"count": 0, "withCaption": 0, "missingCaption": 0},
            "airbnbPhotos": {"count": 0, "withCaption": 0, "missingCaption": 0},
            "vrboPhotos": {"count": 0, "withCaption": 0, "missingCaption": 0}
        }

        if hasattr(property_data, 'Photos') and property_data.Photos:
            for platform in ['booking', 'airbnb', 'vrbo']:
                platform_photos = getattr(property_data.Photos, platform, None)
                if platform_photos:
                    count = len(platform_photos)
                    # Optimize caption counting with list comprehension
                    with_caption = sum(1 for photo in platform_photos 
                                     if hasattr(photo, 'caption') and photo.caption and photo.caption.strip())
                    missing_caption = count - with_caption
                    
                    photos_data[f"{platform}Photos"] = {
                        "count": count,
                        "withCaption": with_caption,
                        "missingCaption": missing_caption
                    }

        return photos_data

    def _get_property_reviews_data_optimized(self, property_data) -> Dict[str, Any]:
        """
        Extract review data from property (optimized version)
        """
        reviews_data = {
            "bookingReviews": {"score": None, "total": None},
            "airbnbReviews": {"score": None, "total": None},
            "vrboReviews": {"score": None, "total": None}
        }

        if hasattr(property_data, 'Reviews') and property_data.Reviews:
            for platform in ['Booking', 'Airbnb', 'VRBO']:
                platform_reviews = getattr(property_data.Reviews, platform, None)
                if platform_reviews:
                    score = getattr(platform_reviews, 'Rev_Score', None)
                    total = getattr(platform_reviews, 'Total_Rev', None)
                    
                    reviews_data[f"{platform.lower()}Reviews"] = {
                        "score": score,
                        "total": total
                    }

        return reviews_data

    def _get_competitor_comparison_data_optimized(self, competitor, property_data) -> Dict[str, Any]:
        """
        Get competitor data and generate comparison metrics (optimized version)
        """
        try:
            competitor_id = str(competitor.id)
            
            # Basic competitor info
            competitor_info = {
                "competitorId": competitor_id,
                "propertName": getattr(competitor, 'propertyName', None),
                "operatorId": getattr(competitor, 'operatorId', None),
                "bookingId": getattr(competitor, 'bookingId', None),
                "bookingLink": getattr(competitor, 'bookingLink', None),
                "airbnbId": getattr(competitor, 'airbnbId', None),
                "airbnbLink": getattr(competitor, 'airbnbLink', None),
                "vrboId": getattr(competitor, 'vrboId', None),
                "vrboLink": getattr(competitor, 'vrboLink', None)
            }

            # Get competitor photos data (optimized)
            competitor_photos = self._get_competitor_photos_data_optimized(competitor)
            competitor_info.update(competitor_photos)

            # Generate comparison metrics (optimized)
            comparison_metrics = self._generate_comparison_metrics_optimized(property_data, competitor)
            competitor_info.update(comparison_metrics)

            return competitor_info

        except Exception as e:
            logging.error(f"Error getting competitor comparison data for {competitor_id}: {str(e)}")
            return None

    def _get_competitor_photos_data_optimized(self, competitor) -> Dict[str, Any]:
        """
        Extract photo data from competitor property (optimized version)
        """
        photos_data = {
            "competitorBookingPhotos": {"count": 0, "withCaption": 0, "missingCaption": 0},
            "competitorAirbnbPhotos": {"count": 0, "withCaption": 0, "missingCaption": 0},
            "competitorVrboPhotos": {"count": 0, "withCaption": 0, "missingCaption": 0}
        }

        # Get photos from competitor property
        platform_mappings = {
            'booking': 'propertyBookingPhotos',
            'airbnb': 'propertyAirbnbPhotos', 
            'vrbo': 'propertyVrboPhotos'
        }
        
        for platform, field_name in platform_mappings.items():
            platform_photos = getattr(competitor, field_name, None)
            if platform_photos:
                count = len(platform_photos)
                # Optimize caption counting
                with_caption = sum(1 for photo in platform_photos 
                                 if photo.get('hasCaption', False) and photo.get('caption'))
                missing_caption = count - with_caption
                
                photos_data[f"competitor{platform.capitalize()}Photos"] = {
                    "count": count,
                    "withCaption": with_caption,
                    "missingCaption": missing_caption
                }

        return photos_data

    def _generate_comparison_metrics_optimized(self, property_data, competitor) -> Dict[str, Any]:
        """
        Generate comparison metrics between property and competitor (optimized version)
        """
        metrics = {
            "bookingPhotoComparison": {"status": "EQUAL", "gap": 0},
            "airbnbPhotoComparison": {"status": "EQUAL", "gap": 0},
            "vrboPhotoComparison": {"status": "EQUAL", "gap": 0}
        }

        # Pre-calculate property photo counts
        property_photo_counts = {}
        if hasattr(property_data, 'Photos') and property_data.Photos:
            for platform in ['booking', 'airbnb', 'vrbo']:
                platform_photos = getattr(property_data.Photos, platform, None)
                property_photo_counts[platform] = len(platform_photos) if platform_photos else 0
        else:
            property_photo_counts = {'booking': 0, 'airbnb': 0, 'vrbo': 0}

        # Compare photos for each platform
        platform_mappings = {
            'booking': 'propertyBookingPhotos',
            'airbnb': 'propertyAirbnbPhotos', 
            'vrbo': 'propertyVrboPhotos'
        }

        for platform in ['booking', 'airbnb', 'vrbo']:
            property_count = property_photo_counts[platform]
            competitor_photos = getattr(competitor, platform_mappings[platform], None)
            competitor_count = len(competitor_photos) if competitor_photos else 0

            # Calculate photo comparison
            photo_gap = property_count - competitor_count 
            if photo_gap > 0:
                photo_status = "AHEAD"
            elif photo_gap < 0:
                photo_status = "BEHIND"
                photo_gap = abs(photo_gap)
            else:
                photo_status = "EQUAL"

            metrics[f"{platform}PhotoComparison"] = {
                "status": photo_status,
                "gap": photo_gap
            }

        return metrics

    def _get_property_photos_data(self, property_data) -> Dict[str, Any]:
        """
        Extract photo counts and caption data from property photos
        """
        photos_data = {
            "bookingPhotos": {"count": 0, "withCaption": 0, "missingCaption": 0},
            "airbnbPhotos": {"count": 0, "withCaption": 0, "missingCaption": 0},
            "vrboPhotos": {"count": 0, "withCaption": 0, "missingCaption": 0}
        }

        if hasattr(property_data, 'Photos') and property_data.Photos:
            for platform in ['booking', 'airbnb', 'vrbo']:
                platform_photos = getattr(property_data.Photos, platform, None)
                if platform_photos:
                    count = len(platform_photos)
                    with_caption = sum(1 for photo in platform_photos 
                                     if hasattr(photo, 'caption') and photo.caption and photo.caption.strip())
                    missing_caption = count - with_caption
                    
                    photos_data[f"{platform}Photos"] = {
                        "count": count,
                        "withCaption": with_caption,
                        "missingCaption": missing_caption
                    }

        return photos_data

    def _get_property_reviews_data(self, property_data) -> Dict[str, Any]:
        """
        Extract review data from property
        """
        reviews_data = {
            "bookingReviews": {"score": None, "total": None},
            "airbnbReviews": {"score": None, "total": None},
            "vrboReviews": {"score": None, "total": None}
        }

        if hasattr(property_data, 'Reviews') and property_data.Reviews:
            for platform in ['Booking', 'Airbnb', 'VRBO']:
                platform_reviews = getattr(property_data.Reviews, platform, None)
                if platform_reviews:
                    score = getattr(platform_reviews, 'Rev_Score', None)
                    total = getattr(platform_reviews, 'Total_Rev', None)
                    
                    reviews_data[f"{platform.lower()}Reviews"] = {
                        "score": score,
                        "total": total
                    }

        return reviews_data

    async def _get_competitor_comparison_data(self, competitor_id: str, property_data) -> Dict[str, Any]:
        """
        Get competitor data and generate comparison metrics
        """
        try:
            # Get competitor property data
            competitor = await self.competitor_property_model.get_competitor_property({"_id": ObjectId(competitor_id)})
            if not competitor:
                return None

            # Basic competitor info
            competitor_info = {
                "competitorId": competitor_id,
                "propertName":getattr(competitor, 'propertyName', None),
                "operatorId": getattr(competitor, 'operatorId', None),
                "bookingId": getattr(competitor, 'bookingId', None),
                "bookingLink": getattr(competitor, 'bookingLink', None),
                "airbnbId": getattr(competitor, 'airbnbId', None),
                "airbnbLink": getattr(competitor, 'airbnbLink', None),
                "vrboId": getattr(competitor, 'vrboId', None),
                "vrboLink": getattr(competitor, 'vrboLink', None)
            }

            # Get competitor photos data
            competitor_photos = self._get_competitor_photos_data(competitor)
            competitor_info.update(competitor_photos)

            # Generate comparison metrics
            comparison_metrics = self._generate_comparison_metrics(property_data, competitor)
            competitor_info.update(comparison_metrics)

            return competitor_info

        except Exception as e:
            logging.error(f"Error getting competitor comparison data for {competitor_id}: {str(e)}")
            return None

    def _get_competitor_photos_data(self, competitor) -> Dict[str, Any]:
        """
        Extract photo data from competitor property
        """
        photos_data = {
            "competitorBookingPhotos": {"count": 0, "withCaption": 0, "missingCaption": 0},
            "competitorAirbnbPhotos": {"count": 0, "withCaption": 0, "missingCaption": 0},
            "competitorVrboPhotos": {"count": 0, "withCaption": 0, "missingCaption": 0}
        }

        # Get photos from competitor property
        platform_mappings = {
            'booking': 'propertyBookingPhotos',
            'airbnb': 'propertyAirbnbPhotos', 
            'vrbo': 'propertyVrboPhotos'
        }
        
        for platform, field_name in platform_mappings.items():
            platform_photos = getattr(competitor, field_name, None)
            if platform_photos:
                count = len(platform_photos)
                with_caption = sum(1 for photo in platform_photos 
                                 if photo.get('hasCaption', False) and photo.get('caption'))
                missing_caption = count - with_caption
                
                photos_data[f"competitor{platform.capitalize()}Photos"] = {
                    "count": count,
                    "withCaption": with_caption,
                    "missingCaption": missing_caption
                }

        return photos_data

    def _generate_comparison_metrics(self, property_data, competitor) -> Dict[str, Any]:
        """
        Generate comparison metrics between property and competitor
        """
        metrics = {
            "bookingPhotoComparison": {"status": "EQUAL", "gap": 0},
            "airbnbPhotoComparison": {"status": "EQUAL", "gap": 0},
            "vrboPhotoComparison": {"status": "EQUAL", "gap": 0}
        }

        # Compare photos for each platform
        for platform in ['booking', 'airbnb', 'vrbo']:
            # Get property photos count
            property_photos = getattr(property_data.Photos, platform, None) if hasattr(property_data, 'Photos') and property_data.Photos else None
            property_count = len(property_photos) if property_photos else 0

            # Get competitor photos count
            platform_mappings = {
                'booking': 'propertyBookingPhotos',
                'airbnb': 'propertyAirbnbPhotos', 
                'vrbo': 'propertyVrboPhotos'
            }
            competitor_photos = getattr(competitor, platform_mappings[platform], None)
            competitor_count = len(competitor_photos) if competitor_photos else 0

            # Calculate photo comparison
            photo_gap = property_count - competitor_count 
            if photo_gap > 0:
                photo_status = "AHEAD"
            elif photo_gap < 0:
                photo_status = "BEHIND"
                photo_gap = abs(photo_gap)
            else:
                photo_status = "EQUAL"

            metrics[f"{platform}PhotoComparison"] = {
                "status": photo_status,
                "gap": photo_gap
            }

        return metrics

    async def get_property_with_competitors_by_id(self, property_id: str) -> dict:
        """
        Get a single property with its competitor data by property ID
        Returns raw property and competitor data without comparison analysis
        Uses projection to fetch only essential fields for better performance
        """
        try:
            # Get the property by ID with projection
            property_data = await self.property_model.get_property_with_projection({"_id": ObjectId(property_id)})
            if not property_data:
                return {
                    "success": False,
                    "data": None,
                    "error": "Property not found"
                }

            # Get competitors for this property with projection
            competitor_ids = getattr(property_data, 'competitorIds', []) or []
            competitor_ids = property_data.get('competitorIds')
            competitors = await self.competitor_property_model.get_competitors_by_ids_with_projection(competitor_ids)

            return {
                "success": True,
                "data": {
                    "property": property_data,
                    "competitors": competitors,
                    "totalCompetitors": len(competitors)
                }
            }

        except Exception as e:
            logging.error(f"Error getting property with competitors by ID: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_competitor_review_analysis_by_type(
        self,
        property_id: str,
        operator_id: str,
        analysis_type: Literal["DIDNTLIKE", "WISHTOHAVE", "LOVEDTOHAVE"],
        platform: Literal["booking", "airbnb"] = "booking"
    ) -> dict:
        """
        Get competitor review analysis filtered by type for a specific property and operator
        """
        try:
            comparison = await self.competitor_comparison_model.get_competitor_comparison({
                "propertyId": property_id,
                "operator_id": operator_id
            })
            if not comparison:
                return {
                    "success": False,
                    "data": None,
                    "error": "Competitor comparison not found for this property and operator"
                }

            platform_field = f"reviewAnalysisCompetitor{platform.capitalize()}"
            insights_source = getattr(comparison, platform_field, None) or comparison.reviewAnalysisCompetitor

            filtered_analysis = [
                insight for insight in insights_source 
                if insight.type == analysis_type
            ]

            return {
                "success": True,
                "data": {
                    "propertyId": property_id,
                    "operatorId": operator_id,
                    "analysisType": analysis_type,
                    "insights": filtered_analysis
                }
            }

        except Exception as e:
            logging.error(f"Error getting competitor review analysis by type: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_own_review_analysis_by_type(
        self,
        property_id: str,
        operator_id: str,
        analysis_type: Literal["DIDNTLIKE", "WISHTOHAVE", "LOVEDTOHAVE"],
        platform: Literal["booking", "airbnb"] = "booking"
    ) -> dict:
        """
        Get own property review analysis filtered by type for a specific property and operator
        """
        try:
            comparison = await self.competitor_comparison_model.get_competitor_comparison({
                "propertyId": property_id,
                "operator_id": operator_id
            })
            if not comparison:
                return {
                    "success": False,
                    "data": None,
                    "error": "Competitor comparison not found for this property and operator"
                }

            platform_field = f"reviewAnalysisOwn{platform.capitalize()}"
            insights_source = getattr(comparison, platform_field, None) or comparison.reviewAnalysisOwn

            filtered_analysis = [
                insight for insight in insights_source 
                if insight.type == analysis_type
            ]

            return {
                "success": True,
                "data": {
                    "propertyId": property_id,
                    "operatorId": operator_id,
                    "analysisType": analysis_type,
                    "insights": filtered_analysis
                }
            }

        except Exception as e:
            logging.error(f"Error getting own review analysis by type: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_improvement_suggestions_based_on_competitor(
        self,
        property_id: str,
        operator_id: str,
        platform: Literal["booking", "airbnb"] = "booking"
    ) -> dict:
        """
        Get improvement suggestions based on competitor analysis for a specific property and operator
        """
        try:
            comparison = await self.competitor_comparison_model.get_competitor_comparison({
                "propertyId": property_id,
                "operator_id": operator_id
            })
            if not comparison:
                return {
                    "success": False,
                    "data": None,
                    "error": "Competitor comparison not found for this property and operator"
                }

            platform_field = f"reviewSuggestionsBasedOnCompetitor{platform.capitalize()}"
            suggestions_source = getattr(comparison, platform_field, None) or comparison.reviewSuggestionsBasedOnCompetitor

            return {
                "success": True,
                "data": {
                    "propertyId": property_id,
                    "operatorId": operator_id,
                    "platform": platform,
                    "suggestions": suggestions_source
                }
            }

        except Exception as e:
            logging.error(f"Error getting improvement suggestions based on competitor: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_improvement_suggestions_based_on_own_reviews(
        self,
        property_id: str,
        operator_id: str,
        platform: Literal["booking", "airbnb"] = "booking"
    ) -> dict:
        """
        Get improvement suggestions based on own property reviews for a specific property and operator
        """
        try:
            comparison = await self.competitor_comparison_model.get_competitor_comparison({
                "propertyId": property_id,
                "operator_id": operator_id
            })
            if not comparison:
                return {
                    "success": False,
                    "data": None,
                    "error": "Competitor comparison not found for this property and operator"
                }

            platform_field = f"reviewSuggestionsBasedOnOwn{platform.capitalize()}"
            suggestions_source = getattr(comparison, platform_field, None) or comparison.reviewSuggestionsBasedOnOwn

            return {
                "success": True,
                "data": {
                    "propertyId": property_id,
                    "operatorId": operator_id,
                    "platform": platform,
                    "suggestions": suggestions_source
                }
            }

        except Exception as e:
            logging.error(f"Error getting improvement suggestions based on own reviews: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_conversion_boosters_and_amenities(
        self,
        operator_id: str,
        property_id: str,
        platform: Literal["booking", "airbnb"] = "booking"
    ) -> dict:
        """
        Get conversion boosters (with meta object popped) and top area amenities missing 
        for a specific property and operator from CompetitorComparison collection
        """
        try:
            # Get the comparison document directly from database
            comparison_doc =await self.competitor_comparison_model.collection.find_one({
                "propertyId": property_id,
                "operator_id": operator_id
            })
            
            if not comparison_doc:
                return {
                    "success": False,
                    "data": None,
                    "error": "Competitor comparison not found for this property and operator"
                }
            platform_key = platform.capitalize()
            boosters_field = f'conversionBoosters{platform_key}'
            amenities_field = f'topAreaAmenitiesMissing{platform_key}'

            # Extract conversion boosters and pop meta object
            conversion_boosters = comparison_doc.get(boosters_field) or comparison_doc.get('conversionBoosters', {})
            if isinstance(conversion_boosters, dict) and 'meta' in conversion_boosters:
                # Create a copy and remove meta key
                conversion_boosters = conversion_boosters.copy()
                conversion_boosters.pop('meta')

            # Extract top area amenities missing
            top_area_amenities_missing = comparison_doc.get(amenities_field) or comparison_doc.get('topAreaAmenitiesMissing', [])

            return {
                "success": True,
                "data": {
                    "platform": platform,
                    "conversionBoosters": conversion_boosters,
                    "topAreaAmenitiesMissing": top_area_amenities_missing
                }
            }

        except Exception as e:
            logging.error(f"Error getting conversion boosters and amenities: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_ai_photo_analysis(self, operator_id: str, property_id: str, platform: Literal["booking", "airbnb"] = "booking") -> dict:
        """
        Get aiPhotoAnalysis object from database based on operator_id and propertyId for a specific platform
        Returns empty data if not found
        """
        try:
            # Get the comparison document directly from database
            comparison_doc = await self.competitor_comparison_model.collection.find_one({
                "propertyId": property_id,
                "operator_id": operator_id
            })
            
            if not comparison_doc:
                return {
                    "success": True,
                    "data": {}
                }
            
            # Extract platform-specific aiPhotoAnalysis field
            platform_key = platform.capitalize()
            platform_field = f'aiPhotoAnalysis{platform_key}'
            ai_photo_analysis = comparison_doc.get(platform_field) or comparison_doc.get('aiPhotoAnalysis', {})
            
            return {
                "success": True,
                "data": {
                    "platform": platform,
                    "aiPhotoAnalysis": ai_photo_analysis
                }
            }

        except Exception as e:
            logging.error(f"Error getting ai photo analysis: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
            
    async def add_to_competitor_comparison_queue(self, operator_id: str, property_id: str) -> dict:
            
            try:
                # Check if property already in queue
                existing_queue_item = await self.competitor_comparison_queue.collection.find_one({
                    "propertyId": property_id,
                    "operator_id": operator_id
                })
                if existing_queue_item: 
                    # Delete existing item if it exists
                    self.competitor_comparison_queue.collection.delete_one({
                        "propertyId": property_id,
                        "operator_id": operator_id
                    })
                    
                self.competitor_comparison_queue.collection.find_one_and_update(
                    {"propertyId": property_id, "operator_id": operator_id},
                    {
                        "$set": {"updated_at": datetime.utcnow()},
                        "$setOnInsert": {
                            "propertyId": str(property_id),
                            "operator_id": operator_id,
                            "status": "pending",
                            "current_step": "amenities_insights",
                            "created_at": datetime.utcnow()
                        }
                    },
                    upsert=True,
                    return_document=True
                )
                
                try:
                    property = await self.property_model.collection.find_one(
                        {"_id": ObjectId(property_id),"Pricelabs_SyncStatus":True}, {"competitorIds": 1}
                    )
                    
                    if property is None:
                        print(f"Property with ID {property_id} not found")
                        return [], []
                        
                    competitor_ids = property.get("competitorIds", [])
                    
                    if not competitor_ids:
                        return [], []
                except Exception as e:
                    print(f"Error fetching competitor reviews for property {property_id}: {e}")
                    return [], []
                
                query = {"_id": {"$in": [ObjectId(cid) for cid in competitor_ids]}}
                
                # await self.competitor_property_model.collection.update_many(query, { "$set": {"status": "pending"}})
                
                return {
                    "success": True,
                    "data": "Property added to queue"
                }
                
            except Exception as e:
                
                logging.error(f"Error adding property to queue: {str(e)}")
                return {
                    "success": False,
                    "data": None,
                    "error": str(e)
                }
                