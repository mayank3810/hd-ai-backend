import os
import tempfile
from datetime import datetime
from typing import Dict, Any, List
from fastapi import BackgroundTasks
from bson import ObjectId
from app.models.ExcelSchedule import ExcelScheduleModel
from app.models.Operator import OperatorModel
from app.models.Listings import ListingModel
from app.schemas.ExcelSchedule import ExcelScheduleCreateSchema
from app.helpers.ExcelFormatting import ExcelFormattingHelper
from app.helpers.AzureStorage import AzureBlobUploader
from app.helpers.PriceLabsAdmin import PriceLabsAdmin
import re

# Global constants
LOGO_URL = "https://strategycuesstorage.blob.core.windows.net/strategy-cues-storage/strategy-cues-storage/7574c178258039f8.png"

# Exact column sequence as specified
EXCEL_COLUMN_SEQUENCE = [
    "Listing Name",
    "Occupancy",
    "Occupancy STLY",
    "Occupancy STLY YoY difference",
    "Occupancy LY",
    "Occupancy YoY difference",
    "Occupancy Benchmark Completion %",
    "Average Market Occupancy",
    "Average Market Occupancy STLY",
    "Average Market Occupancy LY",
    "Market Penetration Index",
    "Rental Revenue",
    "Rental Revenue STLY",
    "Rental Revenue STLY YoY %",
    "Rental Revenue LY",
    "Rental Revenue YoY %",
    "Rental Revenue Benchmark Completion %",
    "ADR",
    "ADR STLY",
    "ADR STLY YoY %",
    "ADR LY",
    "ADR YoY %",
    "Average Market ADR",
    "Average Market ADR LY",
    "Market Penetration ADR Index",
    "RevPar",
    "RevPar STLY",
    "RevPar STLY YoY %",
    "RevPar LY",
    "RevPar YoY %",
    "RevPar Benchmark Completion %",
    "Market Penetration RevPar Index",
    "Average Market Price",
    "Average Market Price LY",
    "Market 25Percentile Price",
    "Market 75Percentile Price",
    "Market 90Percentile Price",
    "Occupancy Pickup 7",
    "Occupancy Pickup 14",
    "Occupancy Pickup 30",
    "BookingImage",
    "AirbnbImage",
    "BookingUrl",
    "AirbnbUrl"
]

class ExcelScheduleService:
    def __init__(self):
        self.excel_schedule_model = ExcelScheduleModel()
        self.operator_model = OperatorModel()
        self.listing_model = ListingModel()
        self.azure_uploader = AzureBlobUploader()

    async def create_excel_schedule(self, schedule_data: ExcelScheduleCreateSchema, background_tasks: BackgroundTasks) -> dict:
        """Create a new Excel schedule entry and return immediately"""
        try:
            # Convert to dict
            schedule_dict = schedule_data.model_dump()
            operator_id = schedule_dict.get("operatorId")
            start_date = schedule_dict.get("startDate")
            end_date = schedule_dict.get("endDate")

            # Check for existing schedule with same operator, start date, and end date
            existing_schedule = await self.excel_schedule_model.find_existing_schedule(
                operator_id, start_date, end_date
            )

            # If existing schedule found, delete it and its file (if exists)
            if existing_schedule:
                # If file exists (status is completed), delete it from blob storage
                if existing_schedule.status == "completed" and existing_schedule.url:
                    try:
                        # Delete the Excel file from blob storage
                        self.azure_uploader.delete_file(existing_schedule.url)
                    except Exception as e:
                        # Silently continue if blob doesn't exist - this is expected behavior
                        # File might already be deleted or never existed
                        error_message = str(e)
                        # Only log if it's not a "BlobNotFound" error
                        if "BlobNotFound" not in error_message and "does not exist" not in error_message:
                            print(f"Warning: Failed to delete existing Excel file from blob storage: {error_message}")
                
                # Delete the MongoDB entry (regardless of status to avoid duplicates)
                await self.excel_schedule_model.delete_excel_schedule(str(existing_schedule.id))

            # Create new schedule entry
            schedule_dict["status"] = "pending"
            schedule_dict["url"] = None
            schedule_dict["createdAt"] = datetime.utcnow()

            schedule_id = await self.excel_schedule_model.create_excel_schedule(schedule_dict)
            
            # Add background task to generate Excel
            background_tasks.add_task(self._generate_excel_in_background, schedule_id, schedule_dict)

            return {
                "success": True,
                "data": {
                    "id": schedule_id,
                    "message": "Excel is being created in the background"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def _generate_excel_in_background(self, schedule_id: str, schedule_data: dict):
        """Background task to generate Excel file from PriceLabs API data"""
        price_labs_admin_helper = None
        try:
            operator_id = schedule_data.get("operatorId")
            start_date = schedule_data.get("startDate")
            end_date = schedule_data.get("endDate")

            # Fetch operator data to get PriceLabs cookies and name
            operator_data = await self.operator_model.get_operator({"_id": ObjectId(operator_id)})
            if not operator_data:
                await self.excel_schedule_model.update_excel_schedule(schedule_id, {
                    "status": "failed",
                    "updatedAt": datetime.utcnow()
                })
                return

            operator_dict = operator_data.model_dump()
            operator_name = operator_dict.get("name", str(operator_id))
            safe_operator_name = re.sub(r'[^a-zA-Z0-9_-]', '_', operator_name)

            # Get PriceLabs cookies from operator
            pricelabs_cfg = operator_dict.get("priceLabs")
            if not pricelabs_cfg or not pricelabs_cfg.get("cookies"):
                await self.excel_schedule_model.update_excel_schedule(schedule_id, {
                    "status": "failed",
                    "updatedAt": datetime.utcnow()
                })
                return

            pricelabs_cookies = pricelabs_cfg.get("cookies", [])

            # Initialize PriceLabs Admin helper
            price_labs_admin_helper = PriceLabsAdmin(pricelabs_cookies)

            # Fetch data from PriceLabs API using custom_range_dashboard
            pricelabs_data = await price_labs_admin_helper.custom_range_dashboard(start_date, end_date)
            
            if not pricelabs_data or isinstance(pricelabs_data, dict) and pricelabs_data.get("success") == False:
                await self.excel_schedule_model.update_excel_schedule(schedule_id, {
                    "status": "failed",
                    "updatedAt": datetime.utcnow()
                })
                return

            # Extract listings from PriceLabs data
            listings = self._extract_listings_from_pricelabs_data(pricelabs_data)
            
            if not listings:
                await self.excel_schedule_model.update_excel_schedule(schedule_id, {
                    "status": "failed",
                    "updatedAt": datetime.utcnow()
                })
                return

            # Enrich listings with Booking and Airbnb URLs and photos
            enriched_listings = await self._enrich_listings_with_listing_data(listings, operator_id)

            # Create Excel workbook from enriched PriceLabs data
            wb = await self._create_excel_workbook_from_pricelabs(enriched_listings, operator_name, operator_id, start_date, end_date)

            # Save Excel with operator name and "Analytics cues" prefix
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
                temp_file_path = temp_file.name
                wb.save(temp_file_path)

            file_name = f"Analytics cues_{safe_operator_name}"
            final_file_path = os.path.join(tempfile.gettempdir(), f"{file_name}.xlsx")
            os.rename(temp_file_path, final_file_path)

            # Apply filters by reopening the file
            final_file_path = ExcelFormattingHelper.apply_filters_to_excel_file(final_file_path, header_row=1)

            # Upload to Azure Blob
            folder_name = f"exports/{operator_id}"
            file_url = self.azure_uploader.upload_excel_file_to_azure_blob(
                final_file_path,
                folder_name=folder_name,
                file_name=file_name,
                file_type=".xlsx"
            )

            # Cleanup
            if final_file_path and os.path.exists(final_file_path):
                os.unlink(final_file_path)
            
            # Cleanup temp logo file if it exists
            temp_logo_path = os.path.join(tempfile.gettempdir(), "temp_logo.png")
            if os.path.exists(temp_logo_path):
                os.unlink(temp_logo_path)

            if file_url:
                # Update schedule with completed status and URL
                await self.excel_schedule_model.update_excel_schedule(schedule_id, {
                    "status": "completed",
                    "url": file_url,
                    "updatedAt": datetime.utcnow()
                })
            else:
                await self.excel_schedule_model.update_excel_schedule(schedule_id, {
                    "status": "failed",
                    "updatedAt": datetime.utcnow()
                })

        except Exception as e:
            # Update schedule with failed status
            await self.excel_schedule_model.update_excel_schedule(schedule_id, {
                "status": "failed",
                "updatedAt": datetime.utcnow()
            })
        finally:
            # Always close the PriceLabs helper client
            if price_labs_admin_helper:
                await price_labs_admin_helper.close()

    def _extract_listings_from_pricelabs_data(self, pricelabs_data: Any) -> List[Dict[str, Any]]:
        """Extract list of listing data from PriceLabs API response"""
        listings = []
        
        if isinstance(pricelabs_data, list):
            # If data is a list, use it directly
            listings = pricelabs_data
        elif isinstance(pricelabs_data, dict):
            # Check common keys that might contain listings
            if "listings" in pricelabs_data:
                listings = pricelabs_data["listings"]
            elif "data" in pricelabs_data:
                listings = pricelabs_data["data"]
            elif "reportData" in pricelabs_data:
                listings = pricelabs_data["reportData"]
        
        return listings if isinstance(listings, list) else []

    async def _enrich_listing_info(self, listing_id_value: str, operator_id_value: str) -> dict:
        """Enrich listing with Booking and Airbnb URLs and photos from Listings collection"""
        try:
            listing_doc = await self.listing_model.find_existing_listing_no_schema(
                operator_id=operator_id_value,
                pricelabs_id=str(listing_id_value)
            )
            if not listing_doc:
                return {
                    "bookingUrl": None,
                    "airbnbUrl": None,
                    "bookingPhoto": None,
                    "airbnbPhoto": None
                }

            # Extract URLs if present, else None
            booking_url = None
            airbnb_url = None

            booking_listing = listing_doc.get("bookingListing") or {}
            airbnb_listing = listing_doc.get("airbnbListing") or {}

            # Attempt common locations for URL inside nested listings or raw_data
            if isinstance(booking_listing, dict):
                booking_url = booking_listing.get("url") or (booking_listing.get("raw_data", {}) if isinstance(booking_listing.get("raw_data"), dict) else {}).get("url")
            if isinstance(airbnb_listing, dict):
                airbnb_url = airbnb_listing.get("url") or (airbnb_listing.get("raw_data", {}) if isinstance(airbnb_listing.get("raw_data"), dict) else {}).get("url")

            # Get separate photos for Booking and Airbnb from photos array
            booking_photo_url = None
            airbnb_photo_url = None
            booking_photos = booking_listing.get("photos") if isinstance(booking_listing, dict) else None
            airbnb_photos = airbnb_listing.get("photos") if isinstance(airbnb_listing, dict) else None

            # Extract URL from first photo in the array (photos is array of Photo objects with 'url' field)
            if isinstance(booking_photos, list) and len(booking_photos) > 0:
                first_booking_photo = booking_photos[0]
                if isinstance(first_booking_photo, dict):
                    booking_photo_url = first_booking_photo.get("url")
            if isinstance(airbnb_photos, list) and len(airbnb_photos) > 0:
                first_airbnb_photo = airbnb_photos[0]
                if isinstance(first_airbnb_photo, dict):
                    airbnb_photo_url = first_airbnb_photo.get("url")

            return {
                "bookingUrl": booking_url or None,
                "airbnbUrl": airbnb_url or None,
                "bookingPhoto": booking_photo_url or None,
                "airbnbPhoto": airbnb_photo_url or None
            }
        except Exception:
            return {
                "bookingUrl": None,
                "airbnbUrl": None,
                "bookingPhoto": None,
                "airbnbPhoto": None
            }

    async def _enrich_listings_with_listing_data(self, listings: List[Dict[str, Any]], operator_id: str) -> List[Dict[str, Any]]:
        """Enrich all listings with Booking and Airbnb URLs and photos"""
        enriched_listings = []
        
        for listing in listings:
            if not isinstance(listing, dict):
                continue
            
            # Find Listing ID from various possible field names
            listing_id = None
            for key in ["Listing ID", "Listing_ID", "listingId", "listing_id"]:
                if key in listing:
                    listing_id = listing[key]
                    break
            
            # Create enriched listing
            enriched_listing = dict(listing)
            
            # If we have a listing ID, enrich with Booking and Airbnb data
            if listing_id:
                listing_details = await self._enrich_listing_info(str(listing_id), operator_id)
                enriched_listing["listingDetails"] = listing_details
            else:
                enriched_listing["listingDetails"] = {
                    "bookingUrl": None,
                    "airbnbUrl": None,
                    "bookingPhoto": None,
                    "airbnbPhoto": None
                }
            
            enriched_listings.append(enriched_listing)
        
        return enriched_listings

    async def _create_excel_workbook_from_pricelabs(self, listings: List[Dict[str, Any]], operator_name: str, operator_id: str, start_date: str, end_date: str):
        """Create Excel workbook from PriceLabs data with exact column sequence"""
        from openpyxl import Workbook
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Analytics Report"

        if not listings:
            # If no listings found, return empty workbook with headers
            headers = EXCEL_COLUMN_SEQUENCE
            total_columns = len(headers)
            ExcelFormattingHelper.setup_sheet_header(ws, headers, operator_name, LOGO_URL, "Analytics Report")
            # Add logo even for empty workbook (header ends at row 2)
            last_data_row = 2
            ExcelFormattingHelper.add_logo_to_bottom(ws, LOGO_URL, total_columns, last_data_row)
            return wb

        # Use exact column sequence as specified
        headers = EXCEL_COLUMN_SEQUENCE
        total_columns = len(headers)

        # Setup header using helper
        ExcelFormattingHelper.setup_sheet_header(ws, headers, operator_name, LOGO_URL, "Analytics Report")

        # Populate data
        current_row = 3  # Start data from row 3 (after headers in row 1-2)
        for listing in listings:
            if not isinstance(listing, dict):
                continue
            
            # Get listing name (try multiple possible field names)
            listing_name = listing.get("Listing Name") or listing.get("Listing_Name") or ""
            
            # Get listing details (bookingUrl, airbnbUrl, bookingPhoto, airbnbPhoto)
            listing_details = listing.get("listingDetails", {})
            booking_url = listing_details.get("bookingUrl") if listing_details else None
            airbnb_url = listing_details.get("airbnbUrl") if listing_details else None
            booking_photo_url = listing_details.get("bookingPhoto") if listing_details else None
            airbnb_photo_url = listing_details.get("airbnbPhoto") if listing_details else None
            
            # Populate data in exact column sequence
            for col_idx, header in enumerate(headers, start=1):
                if header == "Listing Name":
                    ExcelFormattingHelper.set_cell_value_with_alignment(ws, current_row, col_idx, listing_name)
                elif header == "BookingUrl":
                    if booking_url:
                        ExcelFormattingHelper.add_hyperlink_to_cell(ws, current_row, col_idx, booking_url)
                    else:
                        ExcelFormattingHelper.set_cell_value_with_alignment(ws, current_row, col_idx, "")
                elif header == "AirbnbUrl":
                    if airbnb_url:
                        ExcelFormattingHelper.add_hyperlink_to_cell(ws, current_row, col_idx, airbnb_url)
                    else:
                        ExcelFormattingHelper.set_cell_value_with_alignment(ws, current_row, col_idx, "")
                elif header == "BookingImage":
                    if booking_photo_url:
                        ExcelFormattingHelper.add_hyperlink_to_cell(ws, current_row, col_idx, booking_photo_url)
                    else:
                        ExcelFormattingHelper.set_cell_value_with_alignment(ws, current_row, col_idx, "")
                elif header == "AirbnbImage":
                    if airbnb_photo_url:
                        ExcelFormattingHelper.add_hyperlink_to_cell(ws, current_row, col_idx, airbnb_photo_url)
                    else:
                        ExcelFormattingHelper.set_cell_value_with_alignment(ws, current_row, col_idx, "")
                else:
                    # For all other columns, get value from listing data
                    # Try exact match first, then case-insensitive match
                    value = listing.get(header) or listing.get(header.replace(" ", "_"))
                    if value is None:
                        # Try case-insensitive search
                        for key in listing.keys():
                            if key.lower() == header.lower():
                                value = listing[key]
                                break
                    ExcelFormattingHelper.set_cell_value_with_alignment(ws, current_row, col_idx, value or "")

            # Apply row coloring (light yellow)
            ExcelFormattingHelper.apply_row_coloring(ws, current_row, total_columns)
            current_row += 1

        # Freeze listing name column (first column)
        ExcelFormattingHelper.freeze_listing_name_column(ws, 1, 3)
        
        # Determine last data row for sizing/filtering
        last_data_row = current_row - 1

        # Auto-fit column widths (before adding any footer rows)
        ExcelFormattingHelper.auto_fit_columns(ws, total_columns, last_data_row)
        
        # Add column filters up to last data row
        ExcelFormattingHelper.add_column_filters(ws, total_columns, last_data_row)
        
        # Add logo to bottom (after filters, so it doesn't interfere)
        ExcelFormattingHelper.add_logo_to_bottom(ws, LOGO_URL, total_columns, last_data_row)

        return wb

    async def get_excel_schedule(self, schedule_id: str) -> dict:
        """Get Excel schedule by ID"""
        try:
            schedule = await self.excel_schedule_model.get_excel_schedule({"_id": ObjectId(schedule_id)})
            if not schedule:
                return {
                    "success": False,
                    "data": None,
                    "error": "Excel schedule not found"
                }

            return {
                "success": True,
                "data": schedule
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    async def get_excel_schedules_by_operator(self, operator_id: str) -> dict:
        """Get all Excel schedules for a specific operator"""
        try:
            schedules = await self.excel_schedule_model.get_excel_schedules_by_operator(operator_id)

            return {
                "success": True,
                "data": {
                    "schedules": schedules
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
