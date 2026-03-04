from datetime import datetime, timezone
from app.models.DataSyncQueue import DataSyncQueueModel
from app.models.PricelabsAdminData import PricelabsAdminDataModel
from app.schemas.PricelabsAdminData import PricelabsAdminData
from typing import List, Optional
from bson import ObjectId
from fastapi import HTTPException
from app.helpers.PriceLabsAdmin import PriceLabsAdmin
from app.models.Operator import OperatorModel
from app.models.AnalyticsReport import AnalyticsReportModel
from app.models.Listings import ListingModel
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import asyncio

class PricelabsAdminService:
    def __init__(self):
        self.pricelabs_admin_model = PricelabsAdminDataModel()
        self.operator_model = OperatorModel()
        self.analytics_report_model = AnalyticsReportModel()
        self.listing_model = ListingModel()
        self.data_sync_queue_model = DataSyncQueueModel()
        self.allowed_metrics = {
            "Listing Name", "Listing ID",
            "Occupancy", "Occupancy STLY", "Occupancy STLY YoY difference", "Occupancy LY",
            "Occupancy YoY difference", "Occupancy Benchmark Completion %", "Average Market Occupancy",
            "Average Market Occupancy STLY", "Average Market Occupancy LY", "Market Penetration Index",
            "Rental Revenue", "Rental Revenue STLY", "Rental Revenue STLY YoY %", "Rental Revenue LY",
            "Rental Revenue YoY %", "Rental Revenue Benchmark Completion %", "ADR", "ADR STLY",
            "ADR STLY YoY %", "ADR LY", "ADR YoY %", "Average Market ADR", "Average Market ADR LY",
            "Market Penetration ADR Index", "RevPar", "RevPar STLY", "RevPar STLY YoY %", "RevPar LY",
            "RevPar YoY %", "RevPar Benchmark Completion %", "Market Penetration RevPar Index",
            "Average Market Price", "Average Market Price LY", "Market 25Percentile Price",
            "Market 75Percentile Price", "Market 90Percentile Price", "Occupancy Pickup 7",
            "Occupancy Pickup 14", "Occupancy Pickup 30"
        }

    def _filter_report_data(self, data):
        """Recursively filter dictionaries/lists to only include allowed metrics keys.
        Non-dict/list primitives pass through unchanged.
        """
        try:
            if isinstance(data, dict):
                # If this dict looks like a row with metric names, filter by allowed keys
                filtered = {k: self._filter_report_data(v) for k, v in data.items() if k in self.allowed_metrics}
                if filtered:
                    return filtered
                # Otherwise, recurse into children and keep structure
                return {k: self._filter_report_data(v) for k, v in data.items()}
            if isinstance(data, list):
                return [self._filter_report_data(item) for item in data]
            return data
        except Exception:
            return data

    async def _sync_price_labs_data_background(self, operator_id: str, pricelabs_cookies: list):
        """Background task to sync PriceLabs data"""
        try:
            operator = await self.operator_model.get_operator({"_id": ObjectId(operator_id)})
            existing_pricelabs_admin_data = await self.pricelabs_admin_model.get_pricelabs_admin_data_without_schema({"operatorId": operator_id})
            
            if not operator:
                logging.error(f"Operator not found: {operator_id}")
                return
            
            price_labs_admin_helper = PriceLabsAdmin(pricelabs_cookies)

            # Define dashboard methods to execute concurrently (all async now)
            dashboard_methods = {
                "thisMonthDashboard": price_labs_admin_helper.this_month_dashboard,
                "nextMonthDashboard": price_labs_admin_helper.next_month_dashboard,
                "lastMonthDashboard": price_labs_admin_helper.last_month_dashboard,
                "lastSevenDaysDashboard": price_labs_admin_helper.last_seven_days_dashboard,
                "lastThirtyDaysDashboard": price_labs_admin_helper.last_thirty_days_dashboard,
                "pricingDashboard": price_labs_admin_helper.fetch_pricing_dashboard,
                "lastYearThisMonthDashboard": price_labs_admin_helper.last_year_this_month_dashboard
            }
            
            # Execute dashboard methods concurrently - all async now, no thread pool needed
            report_data = {}
            try:
                tasks = [method() for method in dashboard_methods.values()]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for (method_name, _), result in zip(dashboard_methods.items(), results):
                    if isinstance(result, Exception):
                        logging.error(f"Error in {method_name}: {str(result)}")
                        report_data[method_name] = {"success": False, "error": "Pricelab Cookies are expired. Please update cookies."}
                    elif isinstance(result, dict) and result.get("success") == False:
                        # Error response from fetch_report_data (cookies expired)
                        report_data[method_name] = result
                        logging.error(f"Error in {method_name}: {result.get('error', 'Unknown error')}")
                    else:
                        report_data[method_name] = result
                        logging.info(f"Successfully completed {method_name}")
            finally:
                # Always close the client when done
                await price_labs_admin_helper.close()

            pricelabs_admin_data = {
                "operatorId": str(operator.id),
                "reportData": report_data
            }
            
            if existing_pricelabs_admin_data:
                # Update existing data
                updated = await self.pricelabs_admin_model.update_pricelabs_admin_data(str(operator_id), pricelabs_admin_data)
                if updated:
                    logging.info(f"Pricelabs admin data updated successfully for operator: {operator_id}")
                else:
                    logging.error(f"Failed to update pricelabs admin data for operator: {operator_id}")
            else:
                # Create new data
                inserted_id = await self.pricelabs_admin_model.save_pricelabs_admin_data(pricelabs_admin_data)
                logging.info(f"Pricelabs admin data created successfully for operator: {operator_id}, ID: {inserted_id}")
        except Exception as e:
            logging.error(f"Error in background sync for operator {operator_id}: {str(e)}")

    async def save_price_labs_admin_data(self, operator_id: str, background_tasks=None) -> dict:
        try:
            # Validate operator exists
            operator = await self.operator_model.get_operator({"_id": ObjectId(operator_id)})
            if not operator:
                raise HTTPException(status_code=404, detail="Operator not found")
            
            
            self.data_sync_queue_model.collection.find_one_and_update(
                {"operatorId": operator_id},
                {"$set": {"pricelabsStatus": "pending","pricelabsLastSyncDate": datetime.now(timezone.utc)}}
                ,upsert=True)

            # Check if PriceLabs cookies exist
            pricelabs_cookies = operator.priceLabs.cookies if operator.priceLabs and operator.priceLabs.cookies else None
            if not pricelabs_cookies or len(pricelabs_cookies) == 0:
                return {
                    "success": False,
                    "data": None,
                    "error": "No cookies found. Please sync data from chrome extension to get cookies"
                }

            # Start background task for data syncing using FastAPI BackgroundTasks if provided
            if background_tasks is not None:
                # Starlette BackgroundTasks supports async callables; pass the coroutine function
                background_tasks.add_task(self._sync_price_labs_data_background, operator_id, pricelabs_cookies)
            else:
                # Fallback to scheduling on the running event loop if BackgroundTasks isn't available
                asyncio.create_task(self._sync_price_labs_data_background(operator_id, pricelabs_cookies))

            # Return immediately with success response
            return {
                "success": True,
                "data": "Data Syncing started in Background",
                "message": "Data sync process has been initiated"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to start data sync: {str(e)}"
            }

    async def list_pricelabs_admin_data(self, page: int = 1, limit: int = 10,operator_id:str=None) -> dict:
        try:
            limit=limit
            total = await self.pricelabs_admin_model.collection.count_documents({"operatorId":operator_id})
            total_pages = (total + limit - 1) // limit
            number_to_skip = (page - 1) * limit
            pricelabs_admin_data = await self.pricelabs_admin_model.list_pricelabs_admin_data({"operatorId":operator_id}, number_to_skip, limit)
            
            # If no data found, return error message
            if not pricelabs_admin_data or len(pricelabs_admin_data) == 0:
                return {
                    "success": False,
                    "data": None,
                    "error": "Pricelab Cookies are expired. Please update cookies."
                }
            
            # Check if the data contains errors
            if pricelabs_admin_data and len(pricelabs_admin_data) > 0:
                first_item = pricelabs_admin_data[0]
                report_data = first_item.get("reportData", {})
                
                if report_data:
                    # Check if all dashboard methods have errors
                    has_data = False
                    has_error = False
                    error_message = "Pricelab Cookies are expired. Please update cookies."
                    
                    # Check each dashboard method in reportData
                    for key, value in report_data.items():
                        if value is not None:
                            if isinstance(value, dict):
                                # Check if this is an error response
                                if value.get("success") == False or value.get("error"):
                                    has_error = True
                                # Check if this is actual data (list or dict with data, not an error)
                                elif isinstance(value, (list, dict)) and len(value) > 0 and "error" not in value:
                                    has_data = True
                            elif isinstance(value, list) and len(value) > 0:
                                # This is actual data (list with items)
                                has_data = True
                    
                    # If all methods have errors or no data, return error
                    if has_error and not has_data:
                        return {
                            "success": False,
                            "data": None,
                            "error": error_message
                        }
            
            return {
                "success": True,
                "data": {
                    "pricelabs_admin_data": pricelabs_admin_data,
                    "pagination": {
                        "totalPages": total_pages,
                        "currentPage": page,
                        "limit": limit
                    }
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to list pricelabs admin data: {str(e)}"
            }

    async def create_analytics_report(self, operator_id: str, start_date: str, end_date: str) -> dict:
        try:
            operator = await self.operator_model.get_operator({"_id": ObjectId(operator_id)})
            if not operator:
                raise HTTPException(status_code=404, detail="Operator not found")

            # Check if PriceLabs cookies exist
            pricelabs_cookies = operator.priceLabs.cookies if operator.priceLabs and operator.priceLabs.cookies else None
            if not pricelabs_cookies or len(pricelabs_cookies) == 0:
                return {
                    "success": False,
                    "data": None,
                    "error": "No cookies found. Please sync data from chrome extension to get cookies"
                }

            price_labs_admin_helper = PriceLabsAdmin(pricelabs_cookies)

            # Use async method directly - no thread pool needed
            try:
                report_data = await price_labs_admin_helper.custom_range_dashboard(start_date, end_date)
            except asyncio.CancelledError:
                # Client disconnected - log and re-raise to properly clean up
                logging.warning(f"Analytics report creation cancelled for operator {operator_id}")
                raise
            finally:
                # Always close the client when done
                await price_labs_admin_helper.close()


            # Save report data as-is (enrichment happens on read using aggregation)
            to_save = {
                "operatorId": str(operator.id),
                "startDate": start_date,
                "endDate": end_date,
                "reportData": report_data,
                "syncStatus": False
            }

            await self.analytics_report_model.delete_reports_by_operator(str(operator.id))
            inserted_id = await self.analytics_report_model.save_report(to_save)

            return {
                "success": True,
                "data": str(inserted_id)
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to create analytics report: {str(e)}"
            }

    async def get_analytics_report_by_id(self, report_id: str) -> dict:
        try:
            if not ObjectId.is_valid(report_id):
                raise HTTPException(status_code=400, detail="Invalid Report ID")
            
            report = await self.analytics_report_model.get_one({"_id": ObjectId(report_id)})
            if not report:
                raise HTTPException(status_code=404, detail="Analytics report not found")
            
            # Run data filtering in thread pool to avoid blocking the event loop
            # If client disconnects, asyncio.CancelledError will be raised, but the thread will continue
            # The thread will complete but the result will be discarded
            try:
                filtered_report_data = await asyncio.to_thread(
                    self._filter_report_data,
                    report.get("reportData")
                )
            except asyncio.CancelledError:
                # Client disconnected - log and re-raise to properly clean up
                logging.warning(f"Analytics report retrieval cancelled for report {report_id}")
                raise

            async def enrich_listing_info(listing_id_value: str, operator_id_value: str) -> dict:
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

            async def recursively_enrich(data, operator_id_value: str):
                # Enrich dicts that contain "Listing ID"
                if isinstance(data, dict):
                    enriched = dict(data)
                    listing_id_val = None
                    for k, v in data.items():
                        if k == "Listing ID" and v is not None:
                            listing_id_val = v
                            break
                    # Recurse into children first
                    for k, v in data.items():
                        enriched[k] = await recursively_enrich(v, operator_id_value)
                    # Then add enrichment at this level if listing id found
                    if listing_id_val is not None:
                        enriched["listingDetails"] = await enrich_listing_info(str(listing_id_val), operator_id_value)
                    return enriched
                if isinstance(data, list):
                    return [await recursively_enrich(item, operator_id_value) for item in data]
                return data

            # Use operatorId from report for resolving the listing mapping
            operator_id_for_report = report.get("operatorId")
            enriched_report_data = await recursively_enrich(filtered_report_data, operator_id_for_report)

            return {
                "success": True,
                "data": {
                    "_id": str(report.get("_id")),
                    "operatorId": report.get("operatorId"),
                    "startDate": report.get("startDate"),
                    "endDate": report.get("endDate"),
                    "reportData": enriched_report_data,
                    "createdAt": report.get("createdAt")
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to get analytics report: {str(e)}"
            }


    async def update_pricelabs_admin_data(self, operator_id: str, data: dict) -> dict:
        try:
            if not ObjectId.is_valid(operator_id):
                raise HTTPException(status_code=400, detail="Invalid Operator ID")
            updated = await self.pricelabs_admin_model.update_pricelabs_admin_data(operator_id, data)
            if not updated:
                raise HTTPException(status_code=404, detail="Operator not found or not updated")
            return {
                "success": True,
                "data": "Pricelabs admin data updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to update pricelabs admin data: {str(e)}"
            }


    async def delete_pricelabs_admin_data(self, operator_id: str) -> dict:
        try:
            if not ObjectId.is_valid(operator_id):
                raise HTTPException(status_code=400, detail="Invalid Operator ID")
            data = await self.pricelabs_admin_model.delete_pricelabs_admin(operator_id)
            return {
                "success": True,
                "data":  "Pricelabs admin data deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to delete pricelabs admin data: {str(e)}"
            }
            
