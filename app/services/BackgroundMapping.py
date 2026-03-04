# from datetime import datetime
# from typing import Optional, Dict, Any
# import logging

# from app.models.CompetitorComparsionQueue import CompetitorComparisonQueue
# from app.models.Listings import ListingModel
# from app.models.Property import PropertyModel
# from app.models.PricelabsAdminData import PricelabsAdminDataModel
# from app.models.BookingAdminData import BookingAdminDataModel
# from app.schemas.Property import PropertyStatus
# # No schema imports needed - storing as dictionaries

# # Set up logging
# logger = logging.getLogger(__name__)

# class BackgroundMappingService:
#     def __init__(self):
#         self.listing_model = ListingModel()
#         self.property_model = PropertyModel()
#         self.pricelabs_admin_model = PricelabsAdminDataModel()
#         self.booking_admin_model = BookingAdminDataModel()
#         self.competitor_comparison_queue = CompetitorComparisonQueue()

#     async def execute_mapping(self, operator_id: str, booking_id: Optional[str] = None, 
#                        airbnb_id: Optional[str] = None, pricelabs_id: Optional[str] = None) -> None:
#         """
#         Execute data mapping task - any one of booking_id, airbnb_id, or pricelabs_id can be provided
        
#         Args:
#             operator_id: Mandatory operator ID
#             booking_id: Optional booking ID
#             airbnb_id: Optional airbnb ID  
#             pricelabs_id: Optional pricelabs ID
#         """
#         try:
#             # Validate that at least one ID is provided
#             if not any([booking_id, airbnb_id, pricelabs_id]):
#                 logger.error(f"At least one ID (booking_id, airbnb_id, or pricelabs_id) must be provided for operator: {operator_id}")
#                 return          
#             logger.info(f"Starting data mapping for operator: {operator_id}, booking_id: {booking_id}, airbnb_id: {airbnb_id}, pricelabs_id: {pricelabs_id}")
#             # Get PricelabsAdminData
#             pricelabs_admin_data = await self.pricelabs_admin_model.get_pricelabs_admin_data({"operatorId": operator_id})
#             if not pricelabs_admin_data:
#                 logger.error(f"No PricelabsAdminData found for operator {operator_id}")
#                 return
#             # Process based on which ID is available (priority: booking_id > airbnb_id > pricelabs_id)
#             if booking_id:
#                 await self._update_property_by_booking_id(operator_id, int(booking_id), pricelabs_admin_data, pricelabs_id)
#             elif airbnb_id:
#                 await self._update_property_by_airbnb_id(operator_id, airbnb_id, pricelabs_admin_data, pricelabs_id)
#             elif pricelabs_id:
#                 await self._update_property_by_pricelabs_id(operator_id, pricelabs_id, pricelabs_admin_data)

#             logger.info(f"Data mapping completed for operator: {operator_id}")
            
#         except Exception as e:
#             logger.error(f"Error in data mapping: {str(e)}")


#     async def _update_property_by_booking_id(self, operator_id: str, booking_id: int, 
#                                       pricelabs_admin_data, pricelabs_id: Optional[str]) -> None:
#         """
#         Find and update property by booking ID
#         """
#         property_id = None
#         try:
#             # Find property by operator_id and booking ID
#             property_filter = {
#                 "operator_id": operator_id,
#                 "BookingId": str(booking_id)  # Property stores as string
#             }
#             existing_property = await self.property_model.get_property(property_filter)
            
#             if not existing_property:
#                 logger.warning(f"Property not found for booking_id: {booking_id}")
#                 return
            
#             property_id = str(existing_property.id)
            
#             # Set status to in_progress
#             await self.property_model.update_status(property_id, PropertyStatus.MAPPING_IN_PROGRESS)
#             logger.info(f"Property mapping status set to in_progress for booking_id: {booking_id}")
            
#             # Get listing data for this booking ID (bookingListing stores id as int)
#             listing = await self.listing_model.get_listing({
#                 "operatorId": operator_id,
#                 "bookingListing.id": booking_id  
#             })
#             if not listing:
#                 logger.warning(f"Listing not found for booking_id: {booking_id}")
#                 # Set status to failed if listing not found
#                 await self.property_model.update_status(property_id, PropertyStatus.ERROR_IN_MAPPING)
#                 return
            
#             # Get Airbnb ID for mapping
#             airbnb_id = None
#             if hasattr(listing, 'airbnbListing') and listing.airbnbListing:
#                 # Get the Airbnb ID from airbnb_details.property_id
#                 airbnb_details = getattr(listing.airbnbListing, 'airbnb_details', None)
#                 if airbnb_details:
#                     airbnb_id = getattr(airbnb_details, 'property_id', None)
            
#             # Map data and update property
#             mapped_data = await self._map_data_to_property(listing, pricelabs_admin_data, pricelabs_id, operator_id, str(booking_id), airbnb_id)
            
            
#             # Add completed status to the mapped data
#             mapped_data["status"] = PropertyStatus.COMPLETED
#             await self.property_model.update_property(property_id, mapped_data)
#             comparison_queue = self.competitor_comparison_queue.collection.find_one_and_update(
#                     {"propertyId": property_id, "operator_id": operator_id},
#                     {
#                         "$set": {"updated_at": datetime.utcnow()},
#                         "$setOnInsert": {
#                             "propertyId": str(property_id),
#                             "operator_id": operator_id,
#                             "status":"pending",
#                             "created_at": datetime.utcnow()
#                         }
#                     },
#                     upsert=True,
#                     return_document=True
#                 )
#             logger.info(f"Property updated and status set to completed for booking_id: {booking_id}")
                
#         except Exception as e:
#             logger.error(f"Error updating property by booking_id {booking_id}: {str(e)}")
#             # Set status to failed if any error occurs
#             if property_id:
#                 try:
#                     await self.property_model.update_status(property_id, PropertyStatus.ERROR_IN_MAPPING)
#                     logger.info(f"Property mapping status set to failed for booking_id: {booking_id}")
#                 except Exception as status_error:
#                     logger.error(f"Failed to update status to failed for property {property_id}: {str(status_error)}")

#     async def _update_property_by_airbnb_id(self, operator_id: str, airbnb_id: str, 
#                                      pricelabs_admin_data, pricelabs_id: Optional[str]) -> None:
#         """
#         Find and update property by airbnb ID
#         """
#         property_id = None
#         try:
#             # Find property by operator_id and airbnb ID
#             property_filter = {
#                 "operator_id": operator_id,
#                 "AirbnbId": airbnb_id  # airbnb_id is already string
#             }
#             existing_property = await self.property_model.get_property(property_filter)
            
#             if not existing_property:
#                 logger.warning(f"Property not found for airbnb_id: {airbnb_id}")
#                 return
            
#             property_id = str(existing_property.id)
            
#             # Set status to in_progress
#             await self.property_model.update_status(property_id, PropertyStatus.MAPPING_IN_PROGRESS)
#             logger.info(f"Property mapping status set to in_progress for airbnb_id: {airbnb_id}")
            
#             # Get listing data for this airbnb ID (airbnbListing stores id as string)
#             listing = await self.listing_model.get_listing({
#                 "operatorId": operator_id,
#                 "airbnbListing.id": airbnb_id  # airbnb_id is already string
#             })
#             if not listing:
#                 logger.warning(f"Listing not found for airbnb_id: {airbnb_id}")
#                 # Set status to failed if listing not found
#                 await self.property_model.update_status(property_id, PropertyStatus.ERROR_IN_MAPPING)
#                 return
            
#             # Map data and update property
#             mapped_data = await self._map_data_to_property(listing, pricelabs_admin_data, pricelabs_id, operator_id, None, airbnb_id)
#             # Add completed status to the mapped data
#             mapped_data["status"] = PropertyStatus.COMPLETED
#             await self.property_model.update_property(property_id, mapped_data)
#             logger.info(f"Property updated and status set to completed for airbnb_id: {airbnb_id}")
                
#         except Exception as e:
#             logger.error(f"Error updating property by airbnb_id {airbnb_id}: {str(e)}")
#             # Set status to failed if any error occurs
#             if property_id:
#                 try:
#                     await self.property_model.update_status(property_id, PropertyStatus.ERROR_IN_MAPPING)
#                     logger.info(f"Property mapping status set to failed for airbnb_id: {airbnb_id}")
#                 except Exception as status_error:
#                     logger.error(f"Failed to update status to failed for property {property_id}: {str(status_error)}")

#     async def _update_property_by_pricelabs_id(self, operator_id: str, pricelabs_id: str, 
#                                         pricelabs_admin_data) -> None:
#         """
#         Find and update property by pricelabs ID
#         """
#         property_id = None
#         try:
#             # Find property by operator_id and pricelabs ID
#             property_filter = {
#                 "operator_id": operator_id,
#                 "PricelabsId": pricelabs_id
#             }
#             existing_property = await self.property_model.get_property(property_filter)
            
#             if not existing_property:
#                 logger.warning(f"Property not found for pricelabs_id: {pricelabs_id}")
#                 return
            
#             property_id = str(existing_property.id)
            
#             # Set status to in_progress
#             await self.property_model.update_status(property_id, PropertyStatus.MAPPING_IN_PROGRESS)
#             logger.info(f"Property mapping status set to in_progress for pricelabs_id: {pricelabs_id}")
            
#             # For pricelabs_id, we need to find the listing by checking both booking and airbnb listings
#             # that might have this pricelabs_id associated
#             listing = None
            
#             # Try to find listing by booking ID first
#             if hasattr(existing_property, 'BookingId') and existing_property.BookingId:
#                 booking_id = existing_property.BookingId
#                 if booking_id:
#                     # Convert string booking_id to int for listing query
#                     listing = await self.listing_model.get_listing({
#                         "operatorId": operator_id,
#                         "bookingListing.id": int(booking_id)
#                     })
            
#             # If not found by booking, try airbnb
#             if not listing and hasattr(existing_property, 'AirbnbId') and existing_property.AirbnbId:
#                 airbnb_id = existing_property.AirbnbId
#                 if airbnb_id:
#                     # airbnb_id is already string for listing query
#                     listing = await self.listing_model.get_listing({
#                         "operatorId": operator_id,
#                         "airbnbListing.id": airbnb_id
#                     })
            
#             if not listing:
#                 logger.warning(f"Listing not found for pricelabs_id: {pricelabs_id}")
#                 # Set status to failed if listing not found
#                 await self.property_model.update_status(property_id, PropertyStatus.ERROR_IN_MAPPING)
#                 return
            
#             # Map data and update property
#             mapped_data = await self._map_data_to_property(listing, pricelabs_admin_data, pricelabs_id, operator_id, None, None)
#             # Add completed status to the mapped data
#             mapped_data["status"] = PropertyStatus.COMPLETED
#             await self.property_model.update_property(property_id, mapped_data)
#             logger.info(f"Property updated and status set to completed for pricelabs_id: {pricelabs_id}")
                
#         except Exception as e:
#             logger.error(f"Error updating property by pricelabs_id {pricelabs_id}: {str(e)}")
#             # Set status to failed if any error occurs
#             if property_id:
#                 try:
#                     await self.property_model.update_status(property_id, PropertyStatus.ERROR_IN_MAPPING)
#                     logger.info(f"Property mapping status set to failed for pricelabs_id: {pricelabs_id}")
#                 except Exception as status_error:
#                     logger.error(f"Failed to update status to failed for property {property_id}: {str(status_error)}")


#     async def _map_data_to_property(self, listing, pricelabs_admin_data, pricelabs_id: Optional[str], operator_id: str = None, booking_id: str = None, airbnb_id: str = None) -> Dict:
#         """
#         Map listing and pricelabs admin data to property fields
#         """
#         property_data = {}
        
#         # Extract booking and airbnb data from listing
#         booking_data = listing.bookingListing if hasattr(listing, 'bookingListing') else None
#         airbnb_data = listing.airbnbListing if hasattr(listing, 'airbnbListing') else None
#         # Map basic information from booking data (priority)
#         if booking_data:
#             if hasattr(booking_data, 'title') and booking_data.title:
#                 property_data["Listing_Name"] = booking_data.title
#             if hasattr(booking_data, 'location') and booking_data.location and hasattr(booking_data.location, 'city'):
#                 property_data["Area"] = booking_data.location.city
#             if hasattr(booking_data, 'room_type') and booking_data.room_type:
#                 property_data["Room_Type"] = booking_data.room_type
#             if hasattr(booking_data, 'property_type') and booking_data.property_type:
#                 property_data["Property_Type"] = booking_data.property_type

#         # Fallback to airbnb data
#         if not property_data.get("Listing_Name") and airbnb_data:
#             if hasattr(airbnb_data, 'title') and airbnb_data.title:
#                 property_data["Listing_Name"] = airbnb_data.title
#         if not property_data.get("Area") and airbnb_data:
#             if hasattr(airbnb_data, 'location') and airbnb_data.location and hasattr(airbnb_data.location, 'city'):
#                 property_data["Area"] = airbnb_data.location.city
#         if not property_data.get("Room_Type") and airbnb_data:
#             if hasattr(airbnb_data, 'room_type') and airbnb_data.room_type:
#                 property_data["Room_Type"] = airbnb_data.room_type
#         if not property_data.get("Property_Type") and airbnb_data:
#             if hasattr(airbnb_data, 'property_type') and airbnb_data.property_type:
#                 property_data["Property_Type"] = airbnb_data.property_type

#         # Map reviews data - always replace existing data
#         reviews_data = await self._map_reviews_data(booking_data, airbnb_data, operator_id, booking_id, airbnb_id)
#         property_data["Reviews"] = reviews_data

#         # Map photos data
#         photos_data = await self._map_photos_data(booking_data, airbnb_data)
#         if photos_data:
#             property_data["Photos"] = photos_data

#         # Map cancellation policy data
#         booking_admin_data = None
#         if operator_id:
#             booking_admin_data = await self.booking_admin_model.get_booking_admin_data({"operatorId": operator_id})
        
#         cancellation_data = await self._map_cancellation_policy(booking_admin_data, airbnb_data,booking_id)
#         if cancellation_data:
#             property_data["CXL_Policy"] = cancellation_data

#         # Map pricelabs admin data if available
#         if pricelabs_admin_data and pricelabs_id:
#             pricelabs_data = await self._map_pricelabs_data_to_property(pricelabs_admin_data, pricelabs_id)
#             property_data.update(pricelabs_data)

#         # Map adult child configuration from BookingAdminData
#         if operator_id and booking_id:
#             adult_child_config = await self._map_booking_adult_child_config(operator_id, booking_id)
#             if adult_child_config:
#                 property_data["Adult_Child_Config"] = adult_child_config

#         # Map BookingCom data from BookingAdminData
#         if operator_id and booking_id:
#             booking_com_data = await self._map_booking_com_data(operator_id, booking_id)
#             if booking_com_data:
#                 property_data["BookingCom"] = booking_com_data
#         # Map Airbnbcom data from AirbnbAdminData
#         if operator_id and airbnb_id:
#             airbnb_admin_data = await self._map_airbnb_data(operator_id, airbnb_id)
#             if airbnb_admin_data:
#                 property_data["Airbnb"] = airbnb_admin_data

#         # Map amenities data from listing
#         amenities_data = await self._map_amenities_data(booking_data, airbnb_data)
#         if amenities_data:
#             property_data["Amenities"] = amenities_data

#         return property_data

#     async def _map_reviews_data(self, booking_data, airbnb_data, operator_id: str = None, booking_id: str = None, airbnb_id: str = None) -> Dict:
#         """
#         Map reviews data from booking and airbnb listings, always replacing existing data
#         """
#         reviews_data = {}

#         # Initialize empty review structure for all platforms
#         empty_review_data = {
#             "Last_Rev_Score": None,
#             "Rev_Score": None,
#             "Total_Rev": None,
#             "Last_Review_Date": None
#         }

#         # Map Booking reviews
#         booking_review_data = empty_review_data.copy()
#         if booking_data and hasattr(booking_data, 'reviews') and booking_data.reviews:
#             booking_reviews = booking_data.reviews
#             booking_review_data["Rev_Score"] = self._safe_float_convert(getattr(booking_reviews, "overall_rating", None))
#             booking_review_data["Total_Rev"] = self._safe_int_convert(getattr(booking_reviews, "review_count", None))

#         # Map additional Booking reviews from BookingAdminData (Last_Rev_Score and Last_Review_Date)
#         if operator_id and booking_id:
#             booking_admin_data = await self.booking_admin_model.get_booking_admin_data({"operatorId": operator_id})
#             if booking_admin_data and booking_admin_data.last_review_data:
#                 # Find review data for the specific booking_id (hotel_id)
#                 for review in booking_admin_data.last_review_data:
#                     if review.get("hotel_id") == booking_id:
#                         review_data = review.get("review", {})
#                         booking_review_data["Last_Rev_Score"] = review_data.get("review_score")
#                         booking_review_data["Last_Review_Date"] = review_data.get("review_date")
#                         break
#                 else:
#                     # If booking_id != hotel_id, set as N/A
#                     booking_review_data["Last_Rev_Score"] = "N/A"
#                     booking_review_data["Last_Review_Date"] = "N/A"

#         reviews_data["Booking"] = booking_review_data

#         # Map Airbnb reviews
#         airbnb_review_data = empty_review_data.copy()
#         if airbnb_data and hasattr(airbnb_data, 'reviews') and airbnb_data.reviews:
#             airbnb_reviews = airbnb_data.reviews
#             airbnb_review_data["Rev_Score"] = self._safe_float_convert(getattr(airbnb_reviews, "overall_rating", None))
#             airbnb_review_data["Total_Rev"] = self._safe_int_convert(getattr(airbnb_reviews, "review_count", None))

#         # Map additional Airbnb reviews from Listing data (Last_Rev_Score and Last_Review_Date)
#         if operator_id and airbnb_id:
#             listing = await self.listing_model.get_listing({
#                 "operatorId": operator_id,
#                 "airbnbListing.id": airbnb_id
#             })
            
#             if listing and hasattr(listing, 'airbnbListing') and listing.airbnbListing:
#                 airbnb_listing = listing.airbnbListing
#                 if hasattr(airbnb_listing, 'reviews') and airbnb_listing.reviews:
#                     last_review = getattr(airbnb_listing.reviews, 'last_review', None)
#                     if last_review:
#                         airbnb_review_data["Last_Rev_Score"] = str(last_review.get('rating', 'N/A'))
#                         airbnb_review_data["Last_Review_Date"] = last_review.get('created_at', None)

#         reviews_data["Airbnb"] = airbnb_review_data

#         # VRBO reviews (empty for now)
#         reviews_data["VRBO"] = empty_review_data.copy()

#         return reviews_data

#     async def _map_photos_data(self, booking_data, airbnb_data) -> Dict:
#         """
#         Map photos data from booking and airbnb listings
#         """
#         photos_data = {}

#         # Map booking photos
#         if booking_data and hasattr(booking_data, 'photos') and booking_data.photos:
#             booking_photos = []
#             for photo in booking_data.photos:
#                 if hasattr(photo, 'url'):
#                     photo_data = {
#                         "id": getattr(photo, 'id', None),
#                         "url": photo.url,
#                         "caption": getattr(photo, 'caption', None),
#                         "accessibility_label": getattr(photo, 'accessibility_label', None),
#                         "source": "booking"
#                     }
#                     booking_photos.append(photo_data)
#             if booking_photos:
#                 photos_data["booking"] = booking_photos

#         # Map airbnb photos
#         if airbnb_data and hasattr(airbnb_data, 'photos') and airbnb_data.photos:
#             airbnb_photos = []
#             for photo in airbnb_data.photos:
#                 if hasattr(photo, 'url'):
#                     photo_data = {
#                         "id": getattr(photo, 'id', None),
#                         "url": photo.url,
#                         "caption": getattr(photo, 'caption', None),
#                         "accessibility_label": getattr(photo, 'accessibility_label', None),
#                         "source": "airbnb"
#                     }
#                     airbnb_photos.append(photo_data)
#             if airbnb_photos:
#                 photos_data["airbnb"] = airbnb_photos

#         return photos_data

#     async def _map_cancellation_policy(self, booking_admin_data, airbnb_data, booking_id: str = None) -> Dict:
#         """
#         Map cancellation policy data from booking and airbnb listings
#         """
#         cancellation_data = {}

#         # Map booking cancellation policy
#         if booking_admin_data and hasattr(booking_admin_data, 'policyGroupsData'):
#             payterms_data = []
            
#             # Extract payterms from policyGroupsData structure
#             for policy_group in booking_admin_data.policyGroupsData:
#                 # Handle dictionary access for policy_group
#                 hotel_id = policy_group.get('hotel_id') if isinstance(policy_group, dict) else getattr(policy_group, 'hotel_id', None)
                
#                 if hotel_id and str(hotel_id) == str(booking_id):
#                     # Get policy_groups as dictionary
#                     policy_groups_dict = policy_group.get('policy_groups') if isinstance(policy_group, dict) else getattr(policy_group, 'policy_groups', None)
                    
#                     if policy_groups_dict:
#                         # Get data list from policy_groups dictionary
#                         data_list = policy_groups_dict.get('data') if isinstance(policy_groups_dict, dict) else getattr(policy_groups_dict, 'data', None)
                        
#                         if data_list:
#                             for data_item in data_list:
#                                 # Handle dictionary access for data_item
#                                 item_type = data_item.get('type') if isinstance(data_item, dict) else getattr(data_item, 'type', None)
                                
#                                 if item_type == 'ITEM_TYPE_BLOCKS_GROUP':
#                                     items = data_item.get('items') if isinstance(data_item, dict) else getattr(data_item, 'items', None)
                                    
#                                     if items:
#                                         for item in items:
#                                             # Handle dictionary access for item
#                                             bulk_block = item.get('bulk_block') if isinstance(item, dict) else getattr(item, 'bulk_block', None)
#                                             item_data = item.get('data') if isinstance(item, dict) else getattr(item, 'data', None)
                                            
#                                             if bulk_block == 'Cancellation::Bulk' and item_data:
#                                                 # Get payterms from item_data
#                                                 payterms = item_data.get('payterms') if isinstance(item_data, dict) else getattr(item_data, 'payterms', None)
                                                
#                                                 if payterms:
#                                                     payterms_data.extend(payterms)
            
#             # Only set booking data if we found payterms or if the structure exists
#             if payterms_data:
#                 cancellation_data["Booking"] = payterms_data

#         # Map airbnb cancellation policy
#         if airbnb_data and hasattr(airbnb_data, 'cancellation_policy') and airbnb_data.cancellation_policy:
#             airbnb_policy = airbnb_data.cancellation_policy
#             cancellation_data["Airbnb"] = {
#                 "type": getattr(airbnb_policy, 'type', None),
#                 "description": getattr(airbnb_policy, 'description', None),
#                 "free_cancellation_until": getattr(airbnb_policy, 'free_cancellation_until', None)
#             }

#         # Set default values for missing platforms
#         if "Booking" not in cancellation_data:
#             cancellation_data["Booking"] = None
#         if "Airbnb" not in cancellation_data:
#             cancellation_data["Airbnb"] = None
#         cancellation_data["VRBO"] = None

#         return cancellation_data

#     async def _map_pricelabs_data_to_property(self, pricelabs_admin_data, pricelabs_id: str) -> Dict:
#         """
#         Map pricelabs admin data to property fields with new mappings
#         """
#         property_data = {}

#         if not pricelabs_admin_data or not pricelabs_admin_data.reportData:
#             return property_data

#         report_data = pricelabs_admin_data.reportData

#         # Find matching listing in pricelabs admin data
#         pricelabs_listing_data = {}

#         # Check thisMonthDashboard for pickup data and basic metrics
#         if hasattr(report_data, 'thisMonthDashboard') and report_data.thisMonthDashboard:
#             for listing in report_data.thisMonthDashboard:
#                 listing_id = listing.get("Listing ID", "")
#                 if listing_id == pricelabs_id:
#                     pricelabs_listing_data.update({
#                         "this_month_occupancy": listing.get("Occupancy", None),
#                         "this_month_adr": listing.get("ADR", None),
#                         "this_month_adr_stly": listing.get("ADR STLY", None),
#                         "this_month_revpar": listing.get("RevPar", None),
#                         "this_month_revpar_stly": listing.get("RevPar STLY", None),
#                         "this_month_occupancy_stly": listing.get("Occupancy STLY", None),
#                         "this_month_market_penetration_index": listing.get("Market Penetration Index", None),
#                         # Pickup data from thisMonthDashboard
#                         "occupancy_pickup_7": listing.get("Occupancy Pickup 7", None),
#                         "occupancy_pickup_14": listing.get("Occupancy Pickup 14", None),
#                         "occupancy_pickup_30": listing.get("Occupancy Pickup 30", None)
#                     })
#                     break

#         # Check nextMonthDashboard
#         if hasattr(report_data, 'nextMonthDashboard') and report_data.nextMonthDashboard:
#             for listing in report_data.nextMonthDashboard:
#                 listing_id = listing.get("Listing ID","")
#                 if listing_id == pricelabs_id:
#                     pricelabs_listing_data.update({
#                         "next_month_occupancy": listing.get("Occupancy", None),
#                         "next_month_adr": listing.get("ADR", None),
#                         "next_month_revpar": listing.get("RevPar", None),
#                         "next_month_market_penetration_index": listing.get("Market Penetration Index", None)
#                     })
#                     break

#         # Check lastMonthDashboard
#         if hasattr(report_data, 'lastMonthDashboard') and report_data.lastMonthDashboard:
#             for listing in report_data.lastMonthDashboard:
#                 listing_id = listing.get("Listing ID","")
#                 if listing_id == pricelabs_id:
#                     pricelabs_listing_data.update({
#                         "last_month_occupancy": listing.get("Occupancy", None),
#                         "last_month_adr": listing.get("ADR", None),
#                         "last_month_revpar": listing.get("RevPar", None)
#                     })
#                     break

#         # Check lastSevenDaysDashboard for 7_days occupancy
#         if hasattr(report_data, 'lastSevenDaysDashboard') and report_data.lastSevenDaysDashboard:
#             for listing in report_data.lastSevenDaysDashboard:
#                 listing_id = listing.get("Listing ID","")
#                 if listing_id == pricelabs_id:
#                     pricelabs_listing_data.update({
#                         "last_seven_days_occupancy": listing.get("Occupancy", None)
#                     })
#                     break

#         # Check lastThirtyDaysDashboard for 30_days occupancy
#         if hasattr(report_data, 'lastThirtyDaysDashboard') and report_data.lastThirtyDaysDashboard:
#             for listing in report_data.lastThirtyDaysDashboard:
#                 listing_id = listing.get("Listing ID","")
#                 if listing_id == pricelabs_id:
#                     pricelabs_listing_data.update({
#                         "last_thirty_days_occupancy": listing.get("Occupancy", None)
#                     })
#                     break

#         # Check lastYearThisMonthDashboard for LYTM MPI
#         if hasattr(report_data, 'lastYearThisMonthDashboard') and report_data.lastYearThisMonthDashboard:
#             for listing in report_data.lastYearThisMonthDashboard:
#                 listing_id = listing.get("Listing ID","")
#                 if listing_id == pricelabs_id:
#                     pricelabs_listing_data.update({
#                         "last_year_this_month_market_penetration_index": listing.get("Market Penetration Index", None)
#                     })
#                     break

#         # Check pricingDashboard for Min Price Hits (30N) to map to Min_Rate_Threshold
#         if hasattr(report_data, 'pricingDashboard') and report_data.pricingDashboard:
#             for listing in report_data.pricingDashboard:
#                 listing_id = listing.get("listingId","")
#                 if listing_id == pricelabs_id:
#                     pricelabs_listing_data.update({
#                         "min_price_hits_30n": listing.get("Min Price Hits (30N)", None)
#                     })
#                     break

#         if not pricelabs_listing_data:
#             return property_data

#         # Map occupancy data with new mappings
#         occupancy_data = {
#             "7_days": self._safe_float_convert(pricelabs_listing_data.get("last_seven_days_occupancy")),
#             "30_days": self._safe_float_convert(pricelabs_listing_data.get("last_thirty_days_occupancy")),
#             "TM": self._safe_float_convert(pricelabs_listing_data.get("this_month_occupancy")),
#             "NM": self._safe_float_convert(pricelabs_listing_data.get("next_month_occupancy"))
#         }
#         property_data["Occupancy"] = occupancy_data

#         # Map ADR data
#         adr_data = {
#             "TM": self._safe_float_convert(pricelabs_listing_data.get("this_month_adr")),
#             "NM": self._safe_float_convert(pricelabs_listing_data.get("next_month_adr"))
#         }
#         property_data["ADR"] = adr_data

#         # Map RevPAR data
#         revpar_data = {
#             "TM": self._safe_float_convert(pricelabs_listing_data.get("this_month_revpar")),
#             "NM": self._safe_float_convert(pricelabs_listing_data.get("next_month_revpar"))
#         }
#         property_data["RevPAR"] = revpar_data

#         # Map STLY_Var data
#         stly_data = {
#             "Occ": self._safe_float_convert(pricelabs_listing_data.get("this_month_occupancy_stly")),
#             "ADR": self._safe_float_convert(pricelabs_listing_data.get("this_month_adr_stly")),
#             "RevPAR": self._safe_float_convert(pricelabs_listing_data.get("this_month_revpar_stly"))
#         }
#         property_data["STLY_Var"] = stly_data

#         # Map STLM_Var data
#         stlm_data = {
#             "Occ": self._safe_float_convert(pricelabs_listing_data.get("last_month_occupancy")),
#             "ADR": self._safe_float_convert(pricelabs_listing_data.get("last_month_adr")),
#             "RevPAR": self._safe_float_convert(pricelabs_listing_data.get("last_month_revpar"))
#         }
#         property_data["STLM_Var"] = stlm_data

#         # Map Pick_Up_Occ data with new mappings
#         pickup_data = {
#             "7_Days": self._safe_float_convert(pricelabs_listing_data.get("occupancy_pickup_7")),
#             "14_Days": self._safe_float_convert(pricelabs_listing_data.get("occupancy_pickup_14")),
#             "30_Days": self._safe_float_convert(pricelabs_listing_data.get("occupancy_pickup_30"))
#         }
#         property_data["Pick_Up_Occ"] = pickup_data

#         # Map MPI with TM, NM, LYTM components
#         mpi_data = {}
        
#         # TM (This Month) - from thisMonthDashboard
#         tm_mpi = self._safe_float_convert(pricelabs_listing_data.get("this_month_market_penetration_index"))
#         if tm_mpi is not None:
#             mpi_data["TM"] = tm_mpi
        
#         # NM (Next Month) - from nextMonthDashboard  
#         nm_mpi = self._safe_float_convert(pricelabs_listing_data.get("next_month_market_penetration_index"))
#         if nm_mpi is not None:
#             mpi_data["NM"] = nm_mpi
        
#         # LYTM (Last Year This Month) - from lastYearThisMonthDashboard (if available)
#         lytm_mpi = self._safe_float_convert(pricelabs_listing_data.get("last_year_this_month_market_penetration_index"))
#         if lytm_mpi is not None:
#             mpi_data["LYTM"] = lytm_mpi
        
#         # Only set MPI if we have at least one component
#         if mpi_data:
#             property_data["MPI"] = mpi_data

#         # Map Min_Rate_Threshold from Min Price Hits (30N) as string
#         min_price_hits_30n = pricelabs_listing_data.get("min_price_hits_30n")
#         if min_price_hits_30n is not None:
#             property_data["Min_Rate_Threshold"] = str(min_price_hits_30n)

#         return property_data


#     def _safe_float_convert(self, value) -> float:
#         """
#         Safely convert value to float
#         """
#         if value is None:
#             return 0.0
#         try:
#             if isinstance(value, str):
#                 cleaned_value = value.replace('%', '').replace(',', '').strip()
#                 return float(cleaned_value)
#             return float(value)
#         except (ValueError, TypeError):
#             return 0.0

#     def _safe_int_convert(self, value) -> int:
#         """
#         Safely convert value to int
#         """
#         if value is None:
#             return 0
#         try:
#             if isinstance(value, str):
#                 cleaned_value = value.replace('%', '').replace(',', '').strip()
#                 return int(float(cleaned_value))  # Convert to float first to handle decimals
#             return int(value)
#         except (ValueError, TypeError):
#             return 0

#     async def _map_booking_adult_child_config(self, operator_id: str, booking_id: str) -> Dict:
#         """
#         Map adult child configuration from BookingAdminData
        
#         Args:
#             operator_id: Operator ID to find BookingAdminData
#             booking_id: Booking ID to match with hotel_id in adultChildConfig
            
#         Returns:
#             Dict containing adult child configuration data
#         """
#         try:
#             # Get BookingAdminData for the operator
#             booking_admin_data = await self.booking_admin_model.get_booking_admin_data({"operatorId": operator_id})
            
#             if not booking_admin_data or not booking_admin_data.adultChildConfig:
#                 logger.warning(f"No adultChildConfig found for operator_id: {operator_id}")
#                 return None
            
#             # Find the room configuration for the specific booking_id (hotel_id)
#             room_config = None
#             for config in booking_admin_data.adultChildConfig:
#                 if config.get("hotel_id") == booking_id:
#                     # Find the room with matching id
#                     rooms = config.get("rooms", [])
#                     for room in rooms:
#                         room_config = room
#                         break
#                     break
            
#             if not room_config:
#                 logger.warning(f"No room configuration found for booking_id: {booking_id}")
#                 return None
            
#             # Get Airbnb data from Listing collection
#             airbnb_config = None
#             try:
#                 # Find listing with matching booking_id
#                 listing = await self.listing_model.get_listing({"bookingId": booking_id, "operatorId": operator_id})
#                 if listing and hasattr(listing, 'airbnbListing') and listing.airbnbListing:
#                     airbnb_listing = listing.airbnbListing
#                     if hasattr(airbnb_listing, 'max_guests') and airbnb_listing.max_guests is not None:
#                         airbnb_config = {
#                             "max_guests": airbnb_listing.max_guests
#                         }
#             except Exception as e:
#                 logger.warning(f"Error getting Airbnb data for booking_id {booking_id}: {str(e)}")
            
#             # Extract the room configuration data for Booking.com
#             adult_child_config = {
#                 "Booking": {
#                     "id": room_config.get("id"),
#                     "max_guests": room_config.get("max_guests"),
#                     "max_adults": room_config.get("max_adults"),
#                     "max_children": room_config.get("max_children"),
#                     "max_infants": room_config.get("max_infants"),
#                     "room_count": room_config.get("room_count")
#                 },
#                 "Airbnb": airbnb_config,
#                 "VRBO": None      # Will be populated when VRBO mapping is implemented
#             }
            
#             return adult_child_config
                
#         except Exception as e:
#             logger.error(f"Error mapping booking adult child config: {str(e)}")
#             return None


#     async def _map_booking_com_data(self, operator_id: str, booking_id: str) -> Dict:
#         """
#         Map BookingCom data from BookingAdminData
        
#         Args:
#             operator_id: Operator ID to find BookingAdminData
#             booking_id: Booking ID to match with propertyId in settingsData
            
#         Returns:
#             Dict containing BookingCom data
#         """
#         try:
#             # Get BookingAdminData for the operator
#             booking_admin_data = await self.booking_admin_model.get_booking_admin_data({"operatorId": operator_id})
            
#             if not booking_admin_data or not booking_admin_data.groupHomePage or not booking_admin_data.groupHomePage.settingsData:
#                 logger.warning(f"No settingsData found for operator_id: {operator_id}")
#                 return None
            
#             # Find the property settings for the specific booking_id
#             property_settings = None
#             for settings in booking_admin_data.groupHomePage.settingsData:
#                 if getattr(settings, "propertyId", None) == booking_id:
#                     property_settings = settings
#                     break
            
#             if not property_settings:
#                 logger.warning(f"No settings found for booking_id: {booking_id}")
#                 return None
            
#             # Map BookingCom data
#             booking_com_data = {}
            
#             # Genius: Check geniusData.isEnabled
#             genius_data = getattr(property_settings, "geniusData", None)
#             if genius_data:
#                 booking_com_data["Genius"] = "Yes" if genius_data.get("isEnabled", False) else "No"
#             else:
#                 booking_com_data["Genius"] = "No"
            
#             # Mobile: Check settingsMobileRates.isEnabled
#             mobile_rates = getattr(property_settings, "settingsMobileRates", None)
#             if mobile_rates:
#                 booking_com_data["Mobile"] = "Yes" if mobile_rates.get("isEnabled", False) else "No"
#             else:
#                 booking_com_data["Mobile"] = "No"
            
#             # Pref: Check preferredDetails.isEnabled
#             preferred_details = getattr(property_settings, "preferredDetails", None)
#             if preferred_details:
#                 booking_com_data["Pref"] = "Yes" if preferred_details.get("isEnabled", False) else "No"
#             else:
#                 booking_com_data["Pref"] = "No"
            
#             # Discounts: Extract promotions array from promotionsData by matching hotel_id
#             promotions_array = None
#             if booking_admin_data.promotionsData:
#                 for promotion_item in booking_admin_data.promotionsData:
#                     # Check if hotel_id matches booking_id
#                     hotel_id = promotion_item.get("hotel_id")
#                     if hotel_id and str(hotel_id) == str(booking_id):
#                         # Extract promotions_data object
#                         promotions_data = promotion_item.get("promotions_data")
#                         if promotions_data:
#                             # Extract the promotions array
#                             promotions_array = promotions_data.get("promotions")
#                         break
            
#             booking_com_data["Discounts"] = promotions_array if promotions_array else None
            
            
#             return booking_com_data
                
#         except Exception as e:
#             logger.error(f"Error mapping booking com data: {str(e)}")
#             return None

#     async def _map_airbnb_data(self, operator_id: str, airbnb_id: str) -> Dict:
#         """
#         Map Airbnb data from AirbnbAdminData
        
#         Args:
#             operator_id: Operator ID to find AirbnbAdminData
#             airbnb_id: Airbnb ID to match with propertyId in properties
            
#         Returns:
#             Dict containing Airbnb data
#         """
#         try:
#             # Import AirbnbAdminData model
#             from app.models.AirbnbAdminDataModel import AirbnbAdminDataModel
#             airbnb_admin_model = AirbnbAdminDataModel()
            
#             # Get AirbnbAdminData for the operator
#             airbnb_admin_data = airbnb_admin_model.get_airbnb_admin_data({"operatorId": operator_id})
            
#             if not airbnb_admin_data or not airbnb_admin_data.properties:
#                 logger.warning(f"No AirbnbAdminData properties found for operator_id: {operator_id}")
#                 return None
            
#             # Find the property for the specific airbnb_id
#             property_data = None
#             for property_item in airbnb_admin_data.properties:
#                 if getattr(property_item, "propertyId", None) == airbnb_id:
#                     property_data = property_item
#                     break
            
#             if not property_data:
#                 logger.warning(f"No property found for airbnb_id: {airbnb_id}")
#                 return None
            
#             # Map Airbnb data
#             airbnb_data = {}
            
#             # Get pricing settings (nested structure: pricingSettings.pricingSettings)
#             pricing_settings = getattr(property_data, "pricingSettings", None)
            
#             if pricing_settings:
#                 # Get the nested pricingSettings
#                 nested_pricing_settings = pricing_settings.get("pricingSettings", None)
                
#                 if nested_pricing_settings:
#                     # Weekly: (1 - weeklyPriceFactor) * 100
#                     weekly_factor = nested_pricing_settings.get("weeklyPriceFactor", 0)
#                     if weekly_factor:
#                         airbnb_data["Weekly"] = str(round((1 - weekly_factor) * 100, 2))
#                     else:
#                         airbnb_data["Weekly"]="No Data Available"
#                     # Monthly: (1 - monthlyPriceFactor) * 100
#                     monthly_factor = nested_pricing_settings.get("monthlyPriceFactor", 0)
#                     if monthly_factor:
#                         airbnb_data["Monthly"] = str(round((1 - monthly_factor) * 100, 2))
#                     else:
#                         airbnb_data["Monthly"]="No Data Available"
#                 else:
#                     airbnb_data["Weekly"] = "0"
#                     airbnb_data["Monthly"] = "0"
#             else:
#                 airbnb_data["Weekly"] = "0"
#                 airbnb_data["Monthly"] = "0"
            
#             # LM_Disc: From lastMinuteDiscount array (inside nested_pricing_settings)
#             if nested_pricing_settings:
#                 last_minute_discounts = nested_pricing_settings.get("lastMinuteDiscounts", None)
#                 if last_minute_discounts and len(last_minute_discounts) > 0:
#                     # Extract data from the discount object
#                     discount_obj = last_minute_discounts[0]
#                     # Create structured discount object
#                     airbnb_data["LM_Disc"] = {
#                         "__typename": discount_obj.get("__typename", None),
#                         "leadDays": discount_obj.get("leadDays", None),
#                         "priceChange": discount_obj.get("priceChange", None)
#                     }
#                 else:
#                     airbnb_data["LM_Disc"] = None
#             else:
#                 airbnb_data["LM_Disc"] = None
            
#             return airbnb_data
                
#         except Exception as e:
#             logger.error(f"Error mapping airbnb data: {str(e)}")
#             return None

#     async def _map_amenities_data(self, booking_data, airbnb_data) -> Dict:
#         """
#         Map amenities data from booking and airbnb listings
        
#         Args:
#             booking_data: Booking listing data
#             airbnb_data: Airbnb listing data
            
#         Returns:
#             Dict containing amenities data for all platforms
#         """
#         try:
#             amenities_data = {}
            
#             # Map Booking amenities
#             booking_amenities = []
#             if booking_data and hasattr(booking_data, 'amenities') and booking_data.amenities:
#                 for amenity in booking_data.amenities:
#                     if hasattr(amenity, 'name') and amenity.name:
#                         amenity_data = {
#                             "name": amenity.name,
#                             "category": getattr(amenity, 'category', None),
#                             "icon": getattr(amenity, 'icon', None)
#                         }
#                         booking_amenities.append(amenity_data)
            
#             amenities_data["Booking"] = booking_amenities if booking_amenities else None
            
#             # Map Airbnb amenities
#             airbnb_amenities = []
#             if airbnb_data and hasattr(airbnb_data, 'amenities') and airbnb_data.amenities:
#                 for amenity in airbnb_data.amenities:
#                     if hasattr(amenity, 'name') and amenity.name:
#                         amenity_data = {
#                             "name": amenity.name,
#                             "category": getattr(amenity, 'category', None),
#                             "icon": getattr(amenity, 'icon', None)
#                         }
#                         airbnb_amenities.append(amenity_data)
            
#             amenities_data["Airbnb"] = airbnb_amenities if airbnb_amenities else None
            
#             # VRBO amenities (empty for now - will be populated when VRBO mapping is implemented)
#             amenities_data["VRBO"] = None
            
#             return amenities_data
                
#         except Exception as e:
#             logger.error(f"Error mapping amenities data: {str(e)}")
#             return None
