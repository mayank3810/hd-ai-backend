from bson import ObjectId
from app.helpers.BookingHelper import BookingHelper
from app.helpers.AirbnbHelper import AirbnbHelper
from app.helpers.VrboHelper import VrboHelper
from app.models.DataSyncQueue import DataSyncQueueModel
from app.models.Listings import ListingModel
from app.models.OnboardingStatus import OnboardingStatusModel
from app.schemas.Listings import CreateListing
from app.models.Property import PropertyModel
from app.schemas.Property import PropertyStatus
from app.models.ExcelImportsForListing import ExcelImportsForListing
from app.helpers.AzureStorage import AzureBlobUploader
# from app.services.BackgroundMapping import BackgroundMappingService
from collections.abc import Mapping, Sequence
import os
import shutil
from datetime import datetime


class ListingsService:
    def __init__(self):
        self.booking_helper = BookingHelper()
        self.airbnb_helper = AirbnbHelper()
        self.vrbo_helper = VrboHelper()
        self.listing_model = ListingModel()
        self.property_model = PropertyModel()
        self.excel_imports_model = ExcelImportsForListing()
        self.azure_uploader = AzureBlobUploader()
        self.onboarding_model = OnboardingStatusModel()
        self.data_sync_queue_model = DataSyncQueueModel()
        # self.mapping_service = BackgroundMappingService()

    def deep_merge(self, original, updates):
        """
        Recursively merge `updates` into `original`.
        - Dictionaries are merged.
        - Lists are concatenated.
        - Other values are replaced.
        """
        if isinstance(original, dict) and isinstance(updates, dict):
            for key, value in updates.items():
                if key in original:
                    original[key] = self.deep_merge(original[key], value)
                else:
                    original[key] = value
            return original
        elif isinstance(original, list) and isinstance(updates, list):
            return original + updates
        else:
            return updates

        

    async def save_listing(self, body: CreateListing):
        try:
            # Check if listing already exists for this operator_id with any external ID
            existing_listing = await self.listing_model.find_existing_listing(
                operator_id=body.operatorId,
                booking_id=body.bookingId,
                airbnb_id=body.airbnbId,
                pricelabs_id=body.pricelabsId
            )
            query = {"operator_id": body.operatorId,"Pricelabs_SyncStatus":True}

            or_conditions = []

            if getattr(body, "bookingId", None):
                or_conditions.append({
                    "BookingId": body.bookingId
                })

            if getattr(body, "airbnbId", None):
                or_conditions.append({
                    "AirbnbId": body.airbnbId
                })

            if getattr(body, "vrboId", None):
                or_conditions.append({
                    "VRBOId": body.vrboId
                })

            if or_conditions:
                query["$or"] = or_conditions

            property_doc = await self.property_model.collection.find_one(query)
                


            await self.property_model.update_property(property_doc.get("_id"), {"status": PropertyStatus.SCRAPING_IN_PROGRESS})
            
            # Create listing dictionary with only non-None ID fields
            listing = {
                "operatorId": body.operatorId
            }
            
            # If updating existing listing, preserve existing data
            if existing_listing:
                # Start with existing listing data
                listing = existing_listing.model_dump()
                # Remove MongoDB specific fields that shouldn't be updated
                listing.pop('_id', None)
                listing.pop('id', None)
                listing.pop('createdAt', None)
                listing.pop('updatedAt', None)
            
            # Update/add ID fields if they are provided (not None)
            if body.bookingId is not None:
                listing["bookingId"] = body.bookingId
            if body.airbnbId is not None:
                listing["airbnbId"] = body.airbnbId
            if body.vrboId is not None:
                listing["vrboId"] = body.vrboId
            if body.pricelabsId is not None:
                listing["pricelabsId"] = body.pricelabsId
            processed_sources = []
            errors = {}

            # Process Booking.com if provided
            if body.bookingId and body.bookingId:
                try:
                    raw_response = self.booking_helper.get_hotel_details(body.bookingId)
                    if raw_response.get("error"):
                        errors["booking"] = raw_response.get("message", "Failed to fetch booking details")
                    else:
                        booking_listing = self.booking_helper.format_booking_response(raw_response, operator_id=body.operatorId, listing_id=body.bookingId)
                        listing["bookingListing"] = booking_listing
                        processed_sources.append("booking")
                except Exception as ex:
                    errors["booking"] = str(ex)

            # Process Airbnb if provided
            if body.airbnbId and body.airbnbId:
                try:
                    raw_response = self.airbnb_helper.get_property_details(body.airbnbId)
                    if raw_response.get("error"):
                        errors["airbnb"] = raw_response.get("message", "Failed to fetch Airbnb details")
                    else:
                        airbnb_listing = self.airbnb_helper.format_airbnb_response(raw_response, operator_id=body.operatorId, listing_id=body.airbnbId)
                        if not airbnb_listing:
                            errors["airbnb"] = "Failed to format Airbnb response"
                        else:
                            listing["airbnbListing"] = airbnb_listing
                            processed_sources.append("airbnb")
                except Exception as ex:
                    errors["airbnb"] = str(ex)

            # Process VRBO if provided
            if body.vrboId and body.vrboId:
                try:
                    raw_response = self.vrbo_helper.get_property_details(body.vrboId)
                    if raw_response.get("error"):
                        errors["vrbo"] = raw_response.get("message", "Failed to fetch VRBO details")
                    else:
                        vrbo_listing = self.vrbo_helper.format_vrbo_response(raw_response, operator_id=body.operatorId, listing_id=body.vrboId)
                        listing["vrboListing"] = vrbo_listing
                        processed_sources.append("vrbo")
                except Exception as ex:
                    errors["vrbo"] = str(ex)

            # If no known source fields were provided
            if not (body.bookingId or body.airbnbId or body.vrboId):
                await self.property_model.update_property(property_doc.get("_id"), {"status": PropertyStatus.ERROR_IN_SCRAPING})
                return {
                    "success": False,
                    "data": None,
                    "error": "Provide at least one of booking, airbnb, vrbo"
                }

            # If none succeeded
            if not processed_sources:
                await self.property_model.update_property(property_doc.get("_id"), {"status": PropertyStatus.ERROR_IN_SCRAPING})
                return {
                    "success": False,
                    "data": None,
                    "error": "; ".join([f"{k}: {v}" for k, v in errors.items()]) or "Failed to process any provided source"
                }

            # Save to database - either update existing or create new
            if existing_listing:
                # Update existing listing
                listing_id = existing_listing.id
                await self.listing_model.update_existing_listing(str(listing_id), listing)
                action = "updated"
            else:
                # Create new listing
                listing_id = await self.listing_model.create_listing(listing)
                action = "created"
            
            await self.property_model.update_property(property_doc.get("_id"), {"status": PropertyStatus.COMPLETED})
            return {
                "success": True,
                "data": {
                    "listing_id": str(listing_id),
                    "processedSources": processed_sources,
                    "errors": errors if errors else None
                }
            }
        
        except Exception as e:
            await self.property_model.update_property(property_doc.get("_id"), {"status": PropertyStatus.ERROR_IN_SCRAPING})
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    async def get_listings(self, filters: dict = {}, skip: int = 0, limit: int = 100):
        """Get listings from database with optional filters"""
        try:
            listings = await self.listing_model.list_listings(filters, skip, limit)
            return {
                "success": True,
                "data": listings,
                "count": len(listings)
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    async def get_listing_by_id(self, listing_id: str):
        """Get a specific listing by ID"""
        try:
            listing = await self.listing_model.get_listing_by_id(listing_id)
            if listing:
                return {
                    "success": True,
                    "data": listing.model_dump()
                }
            else:
                return {
                    "success": False,
                    "data": None,
                    "error": "Listing not found"
                }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
            
    async def get_property_urls(self, operator_id: str, page: int = 1, limit: int = 10) -> dict:
        """Get property URLs sorted by creation date (newest first)"""
        try:
            skip = (page - 1) * limit
            query = {"operator_id": operator_id,"Pricelabs_SyncStatus":True}
            sort_by = {"_id": -1}  # Newest first
            
            # Use aggregation pipeline to project fields and slice photos to only first photo from each platform
            pipeline = [
                {"$match": query},
                {"$sort": sort_by},
                {"$skip": skip},
                {"$limit": limit},
                {
                    "$project": {
                        "_id": 1,
                        "Listing_Name": 1,
                        "status": 1,
                        "BookingId": 1,
                        "BookingUrl": 1,
                        "AirbnbId": 1,
                        "AirbnbUrl": 1,
                        "VRBOId": 1,
                        "VRBOUrl": 1,
                        "PricelabsId": 1,
                        "PricelabsUrl": 1,
                        "Photos": {
                            "booking": {"$slice": ["$Photos.booking", 1]},
                            "airbnb": {"$slice": ["$Photos.airbnb", 1]},
                        },
                    }
                }
            ]
            
            # Execute aggregation pipeline
            properties = []
            async for doc in self.property_model.collection.aggregate(pipeline):
                # Convert ObjectId to string for JSON serialization
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                properties.append(doc)
            
            # Get total count
            total = await self.property_model.get_properties_count(query)
            total_pages = (total + limit - 1) // limit
              
            data_sync_queue = await self.data_sync_queue_model.collection.find_one({"operatorId": operator_id})
            
            last_sync_date = None
            if data_sync_queue:
                last_sync_date = data_sync_queue
            else:
                last_sync_date = None
            return {
                "success": True,
                "data": {
                    "lastSyncDates": last_sync_date,
                    "properties": [{ 
                        "id": p["_id"], 
                        "urls": {
                            "PropertyName": p.get("Listing_Name"),
                            "BookingId": p.get("BookingId"),
                            "BookingUrl": p.get("BookingUrl"),
                            "AirbnbId": p.get("AirbnbId"),
                            "AirbnbUrl": p.get("AirbnbUrl"),
                            "VRBOId": p.get("VRBOId"),
                            "VRBOUrl": p.get("VRBOUrl"),
                            "PricelabsId": p.get("PricelabsId"),
                            "PricelabsUrl": p.get("PricelabsUrl"),
                            "status": p.get("status"),
                            "Photos": p.get("Photos")
                        }
                    } for p in properties],
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

    async def scrape_and_map_listing(self, body: CreateListing):
        """
        Combined method that performs scraping and mapping in sequence
        """
        try:
            # Step 1: Perform scraping (save_listing handles property finding and status updates)
            scraping_result = await self.save_listing(body)
            
            if not scraping_result.get("success", False):
                return {
                    "success": False,
                    "data": None,
                    "error": f"Scraping failed: {scraping_result.get('error', 'Unknown error')}"
                }
            
            # Step 2: Perform mapping (BackgroundMappingService handles property finding and status updates)
            try:
                self.mapping_service.execute_mapping(
                    operator_id=body.operatorId,
                    booking_id=body.bookingId,
                    airbnb_id=body.airbnbId,
                    pricelabs_id=body.pricelabsId
                )
                
                return {
                    "success": True,
                    "data": {
                        "message": "Scraping and mapping completed successfully",
                        "listing_id": scraping_result.get("data", {}).get("listing_id"),
                        "processed_sources": scraping_result.get("data", {}).get("processedSources", []),
                        "errors": scraping_result.get("data", {}).get("errors")
                    }
                }
                
            except Exception as mapping_error:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Mapping failed: {str(mapping_error)}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
      
      
    async def update_property_status(self, _id: str):
        try:
            resp = await self.property_model.collection.find_one_and_update({"_id": ObjectId(_id),"Pricelabs_SyncStatus":True}, {"$set": {"status": PropertyStatus.PENDING}})
            
            return {
                "success": True,
                "data": resp
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }      
            
    async def get_booking_listings_by_operator_id(self, operator_id: str):
        try:
            cursor = self.listing_model.collection.find({"operatorId": operator_id})
            booking_listings_ids = []
            async for listing in cursor:
                if listing.get("bookingId"):
                    booking_listings_ids.append(listing.get("bookingId"))
            return {
                "success": True,
                "data": booking_listings_ids
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    async def upload_excel_for_listing(self, file, operator_id: str, user_id: str):
        """
        Upload excel file and save its URL to ExcelImportsForListing queue
        """
        temp_file_path = None
        try:
            # Validate file type
            if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
                return {
                    "success": False,
                    "data": None,
                    "error": "Invalid file type. Only Excel files (.xlsx, .xls) and CSV files are allowed."
                }
            
            # Save file temporarily
            from app.helpers.Utilities import Utils
            temp_file_path = Utils.generate_hex_string() + "_" + file.filename.replace(" ", "_")
            
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Upload to Azure Storage
            file_url = self.azure_uploader.upload_excel_file_to_azure_blob(
                temp_file_path,
                folder_name=f"excel-imports/{operator_id}",
                file_name=file.filename
            )
            
            if not file_url:
                return {
                    "success": False,
                    "data": None,
                    "error": "Failed to upload file to storage"
                }
            
            # Check if there's already a file in queue for this operator (any status)
            existing_entry = await self.excel_imports_model.collection.find_one({
                "operator_id": operator_id, "status": "pending"
            })
            
            if existing_entry:
                # Clean up the uploaded file since we won't use it
                try:
                    self.azure_uploader.delete_file(file_url)
                except Exception:
                    pass  # Ignore cleanup errors
                
                return {
                    "success": False,
                    "data": None,
                    "error": f"File already exists in queue. Current status: {existing_entry.get('status')}"
                }
            
            # Save to ExcelImportsForListing collection
            queue_entry = {
                "operator_id": operator_id,
                "user_id": user_id,
                "file_url": file_url,
                "file_name": file.filename,
                "status": "pending",
                "createdOn": datetime.utcnow(),
                "updatedOn": datetime.utcnow()
            }
            
            result = await self.excel_imports_model.collection.insert_one(queue_entry)
            
            return {
                "success": True,
                "data": {
                    "queue_id": str(result.inserted_id),
                    "file_url": file_url,
                    "status": "pending",
                    "message": "Excel file uploaded successfully and added to queue"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Failed to upload excel file: {str(e)}"
            }
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as cleanup_error:
                    print(f"Failed to clean up temporary file: {str(cleanup_error)}")
            