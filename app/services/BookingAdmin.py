from datetime import datetime, timezone
from app.models.BookingAdminData import BookingAdminDataModel
from app.models.DataSyncQueue import DataSyncQueueModel
from app.schemas.BookingAdminData import BookingAdminData
from typing import List, Optional
from bson import ObjectId
from fastapi import HTTPException
from app.helpers.BookingAdmin import BookingAdmin
from app.models.Operator import OperatorModel

from copy import deepcopy

class BookingAdminService:
    def __init__(self):
        self.booking_admin_model = BookingAdminDataModel()
        self.operator_model = OperatorModel()
        self.data_sync_queue_model = DataSyncQueueModel()
        
        self.IDENTIFIER_KEYS = ["propertyId", "hotel_id"]


    def merge_json(self, original, updates):
        """
        Recursively merges `updates` into `original`:
        - Replaces 'last_review_data' entirely.
        - Merges dicts recursively.
        - Merges lists with identifier matching (e.g., propertyId or hotel_id).
        - Replaces primitive values.
        """
        # Case 1: Both are dicts
        if isinstance(original, dict) and isinstance(updates, dict):
            for key, value in updates.items():
                # ✅ Force replace for these keys
                if key in ['last_review_data']:
                    original[key] = deepcopy(value)
                    continue

                if key in original:
                    original[key] = self.merge_json(original[key], value)
                else:
                    original[key] = deepcopy(value)
            return original

        # Case 2: Both are lists
        elif isinstance(original, list) and isinstance(updates, list):
            for update_item in updates:
                if isinstance(update_item, dict):
                    matched = False
                    for identifier in self.IDENTIFIER_KEYS:
                        if identifier in update_item:
                            for orig_item in original:
                                if (
                                    isinstance(orig_item, dict) and
                                    orig_item.get(identifier) == update_item[identifier]
                                ):
                                    self.merge_json(orig_item, update_item)
                                    matched = True
                                    break
                            if not matched:
                                original.append(deepcopy(update_item))
                            break
                    else:
                        # No identifier found, just append
                        original.append(deepcopy(update_item))
                else:
                    if update_item not in original:
                        original.append(deepcopy(update_item))
            return original

        # Case 3: Primitive → overwrite
        else:
            return deepcopy(updates)



    #refactor this method to check duplicate based on propertyId
    async def save_booking_admin_data(self, operator_id: str) -> dict:
        try:

            operator = await self.operator_model.get_operator({"_id": ObjectId(operator_id)})
            if not operator:
                raise HTTPException(status_code=404, detail="Operator not found")
            
            self.booking_admin_helper = BookingAdmin(
                operator.booking.cookies,
                operator.booking.session_id,
                account_id=operator.booking.account_id
            )

            hotels_performance_resp = self.booking_admin_helper.hotels_performance_metrics()
            properties_resp = self.booking_admin_helper.get_all_properties()

            # Parse properties and build operations data
            operations_data = []
            property_ids = []
            try:
                data = properties_resp.get("data", {})
                group = data.get("partnerProperty", {}).get("groupHomeListPropertiesV2", {})
                props = group.get("properties", [])
                for p in props:
                    pid = str(p.get("id"))
                    property_ids.append(pid)
                    operations_data.append({
                        "propertyId": pid,
                        "address": p.get("address"),
                        "cityName": p.get("cityName"),
                        "countryCode": p.get("countryCode"),
                        "propertyName": p.get("name"),
                        "status": p.get("status"),
                        "arrivvalsInFortyEightHours": 0,
                        "departuresInFortyEightHours": 0,
                        "guestMessages": 0,
                        "bookingDotComMessages": 0,
                    })
            except Exception as e:
                print(e)
                pass

            # Fetch arrivals counts and merge
            if property_ids:
                try:
                    arrivals_map = self.booking_admin_helper.get_arrivals_data(property_ids=property_ids)
                    for item in operations_data:
                        pid = item.get("propertyId")
                        if pid in arrivals_map:
                            item["arrivvalsInFortyEightHours"] = arrivals_map.get(pid, 0)
                except Exception as e:
                    print(e)
                    pass

            # Fetch departures counts and merge
            if property_ids:
                try:
                    departures_resp = self.booking_admin_helper.departures_count(property_ids=property_ids)
                    dep_map = {}
                    try:
                        ddata = departures_resp.get("data", {})
                        dep_items = ddata.get("partnerReservation", {}).get("departuresCount", [])
                        for di in dep_items:
                            dep_map[str(di.get("propertyId"))] = int(di.get("count", 0))
                    except Exception as e:
                        print(e)
                        pass
                    for item in operations_data:
                        pid = item.get("propertyId")
                        if pid in dep_map:
                            item["departuresInFortyEightHours"] = dep_map.get(pid, 0)
                except Exception as e:
                    print(e)
                    pass

            # Fetch partner messages counts and merge
            if property_ids:
                try:
                    messages_resp = self.booking_admin_helper.partner_messages_count(property_ids=property_ids)
                    msg_map = {}
                    try:
                        mdata = messages_resp.get("data", {})
                        msg_items = mdata.get("partnerMessaging", {}).get("getPartnerMessagesCount", [])
                        for mi in msg_items:
                            pid = str(mi.get("propertyId"))
                            msg_map[pid] = {
                                "bookingMessagesCount": int(mi.get("bookingMessagesCount", 0)),
                                "guestMessagesCount": int(mi.get("guestMessagesCount", 0)),
                            }
                    except Exception as e:
                        print(e)
                        pass
                    for item in operations_data:
                        pid = item.get("propertyId")
                        if pid in msg_map:
                            item["bookingDotComMessages"] = msg_map[pid]["bookingMessagesCount"]
                            item["guestMessages"] = msg_map[pid]["guestMessagesCount"]
                except Exception as e:
                    print(e)
                    pass

            # Parse hotels performance metrics to expected shape
            hotels_metrics_list = []
            try:
                hp_data = hotels_performance_resp.get("data", {})
                hp = hp_data.get("partnerMetrics", {}).get("hotelsPerformanceMetrics", {})
                metrics_items = hp.get("hotelsPerformanceMetrics", [])
                for it in metrics_items:
                    hotels_metrics_list.append({
                        "propertyId": str(it.get("propertyId")),
                        "metrics": it.get("metrics", []),
                    })
            except Exception as e:
                print(e)
                pass

            # Fetch settings data (genius, preferred, minLos, geoRates, mobileRates, propertyScore)
            settings_map = {pid: {
                "propertyId": pid,
                "geniusData": None,
                "preferredDetails": None,
                "minLosDetails": None,
                "settingsGeoRates": None,
                "settingsMobileRates": None,
                "propertyScoreDetails": None,
            } for pid in property_ids}

            try:
                genius_resp = self.booking_admin_helper.settings_genius()
                gdata = genius_resp.get("data", {})
                items = gdata.get("partnerProperty", {}).get("settingsGenius", {}).get("data", [])
                for it in items:
                    pid = str(it.get("propertyId"))
                    if pid in settings_map:
                        settings_map[pid]["geniusData"] = it
            except Exception as e:
                print(e)
                pass

            try:
                preferred_resp = self.booking_admin_helper.preferred_details()
                pdata = preferred_resp.get("data", {})
                items = pdata.get("partnerProperty", {}).get("preferredDetails", {}).get("data", [])
                for it in items:
                    pid = str(it.get("propertyId"))
                    if pid in settings_map:
                        settings_map[pid]["preferredDetails"] = it
            except Exception as e:
                print(e)
                pass

            try:
                minlos_resp = self.booking_admin_helper.min_los_details()
                mldata = minlos_resp.get("data", {})
                items = mldata.get("partnerProperty", {}).get("minLosDetails", {}).get("data", [])
                for it in items:
                    pid = str(it.get("propertyId"))
                    if pid in settings_map:
                        settings_map[pid]["minLosDetails"] = it
            except Exception as e:
                print(e)
                pass

            try:
                geo_resp = self.booking_admin_helper.settings_geo_rates()
                gldata = geo_resp.get("data", {})
                items = gldata.get("partnerProperty", {}).get("settingsGeoRates", {}).get("data", [])
                for it in items:
                    pid = str(it.get("propertyId"))
                    if pid in settings_map:
                        settings_map[pid]["settingsGeoRates"] = it
            except Exception as e:
                print(e)
                pass

            try:
                mobile_resp = self.booking_admin_helper.settings_mobile_rates()
                mrdata = mobile_resp.get("data", {})
                items = mrdata.get("partnerProperty", {}).get("settingsMobileRates", {}).get("data", [])
                for it in items:
                    pid = str(it.get("propertyId"))
                    if pid in settings_map:
                        settings_map[pid]["settingsMobileRates"] = it
            except Exception as e:
                print(e)
                pass

            try:
                pscore_resp = self.booking_admin_helper.property_score_details()
                psdata = pscore_resp.get("data", {})
                items = psdata.get("partnerProperty", {}).get("propertyScoreDetails", {}).get("data", [])
                for it in items:
                    pid = str(it.get("propertyId"))
                    if pid in settings_map:
                        settings_map[pid]["propertyScoreDetails"] = it
            except Exception as e:
                print(e)
                pass

            settings_list = list(settings_map.values()) if settings_map else []

            booking_admin_data = {
                "operatorId": str(operator.id),
                "groupHomePage": {
                    "operationsData": operations_data,
                    "hotelsPerformanceMetrics": hotels_metrics_list,
                    "settingsData": settings_list,
                }
            }
            
            existing_data = await self.booking_admin_model.collection.find_one({"operatorId": operator_id})
            if existing_data:
                booking_admin_data = self.merge_json(existing_data, booking_admin_data)
            
            
            await self.booking_admin_model.save_or_update_booking_admin_data(operator_id,booking_admin_data)
            return {
                "success": True,
                "data": None
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to create booking admin data: {str(e)}"
            }

    async def list_booking_admin_data(self, page: int = 1, limit: int = 10,operator_id:str=None) -> dict:
        try:
            limit=limit
            total = await self.booking_admin_model.collection.count_documents({"operatorId":operator_id})
            total_pages = (total + limit - 1) // limit
            number_to_skip = (page - 1) * limit
            booking_admin_data = await self.booking_admin_model.list_booking_admin_data({"operatorId":operator_id}, number_to_skip, limit)
            return {
                "success": True,
                "data": {
                    "booking_admin_data": booking_admin_data,
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
                "error": f"Unable to list booking admin data: {str(e)}"
            }

    async def get_booking_admin_data_by_id(self, operator_id: str) -> dict:
        try:
            if not ObjectId.is_valid(operator_id):
                raise HTTPException(status_code=400, detail="Invalid Operator ID")
            booking_admin_data = await self.booking_admin_model.get_booking_admin_data({"operatorId": operator_id})
            if not booking_admin_data:
                raise HTTPException(status_code=404, detail="Operator not found")
            return {
                "success": True,
                "data": booking_admin_data.model_dump()
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to get booking admin data: {str(e)}"
            }

#refactor this method to check duplicate based on propertyId
    async def update_booking_admin_data(self, operator_id: str, data: dict) -> dict:
        try:
            if not ObjectId.is_valid(operator_id):
                raise HTTPException(status_code=400, detail="Invalid Operator ID")
            
            existing_data = await self.booking_admin_model.collection.find_one({"operatorId": operator_id})
            if existing_data:
                data = self.merge_json(existing_data, data) 
            
            updated = await self.booking_admin_model.update_booking_admin_data(operator_id, data)
            # if not updated:
            #     raise HTTPException(status_code=404, detail="Operator not found or not updated")
            
            self.data_sync_queue_model.collection.find_one_and_update(
                {"operatorId": operator_id},
                {"$set": {"bookingStatus": "pending","bookingLastSyncDate": datetime.now(timezone.utc)}}
                ,upsert=True)
            
            return {
                "success": True,
                "data": "Booking admin data updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to update booking admin data: {str(e)}"
            }

    async def delete_booking_admin_data(self, operator_id: str) -> dict:
        try:
            if not ObjectId.is_valid(operator_id):
                raise HTTPException(status_code=400, detail="Invalid Operator ID")
            data = await self.booking_admin_model.delete_booking_admin_data(operator_id)
            return {
                "success": True,
                "data":  "Booking admin data deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to delete booking admin data: {str(e)}"
            }
            
            
            
    async def get_adult_child_config(self, operator_id:str,property_id: str) -> dict:
        try:
            operator = await self.operator_model.get_operator({"_id": ObjectId(operator_id)})
            if not operator:
                raise HTTPException(status_code=404, detail="Operator not found")
                        
            self.booking_admin_helper = BookingAdmin(
                operator.booking.cookies,
                operator.booking.session_id,
                account_id=operator.booking.account_id
            )
            data=self.booking_admin_helper.get_adult_child_configuration(property_id)
            return {
                "success": True,
                "data": data
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to get adult child config: {str(e)}"
            }
            
            
    #refactor this method to check duplicate based on propertyId
    async def map_and_save_booking_admin_data(self, operator_id: str, admin_data: dict) -> dict:
        try:
            # Validate operator exists
            operator = await self.operator_model.get_operator({"_id": ObjectId(operator_id)})
            if not operator:
                raise HTTPException(status_code=404, detail="Operator not found")
            
            # Extract data from admin_data dict
            properties_resp = admin_data.get("properties", {})
            hotels_performance_resp = admin_data.get("hotelsPerformanceMetrics", {})
            arrivals_map = admin_data.get("arrivalsCount", {})
            departures_resp = admin_data.get("departuresCount", {})
            messages_resp = admin_data.get("partnerMessagesCount", {})
            genius_resp = admin_data.get("propertiesSettingsGenius", {})
            preferred_resp = admin_data.get("propertiesPreferredDetails", {})
            minlos_resp = admin_data.get("propertiesMinLosDetails", {})
            geo_resp = admin_data.get("propertiesSettingsGeoRates", {})
            mobile_resp = admin_data.get("propertiesSettingsMobileRates", {})
            pscore_resp = admin_data.get("propertiesPropertyScoreDetails", {})

            # Parse properties and build operations data
            operations_data = []
            property_ids = []
            try:
                data = properties_resp.get("data", {})
                group = data.get("partnerProperty", {}).get("groupHomeListPropertiesV2", {})
                props = group.get("properties", [])
                for p in props:
                    pid = str(p.get("id"))
                    property_ids.append(pid)
                    operations_data.append({
                        "propertyId": pid,
                        "address": p.get("address"),
                        "cityName": p.get("cityName"),
                        "countryCode": p.get("countryCode"),
                        "propertyName": p.get("name"),
                        "status": p.get("status"),
                        "arrivvalsInFortyEightHours": 0,
                        "departuresInFortyEightHours": 0,
                        "guestMessages": 0,
                        "bookingDotComMessages": 0,
                    })
            except Exception as e:
                print(e)
                pass

            # Merge arrivals counts
            if property_ids and arrivals_map:
                try:
                    for item in operations_data:
                        pid = item.get("propertyId")
                        if pid in arrivals_map:
                            item["arrivvalsInFortyEightHours"] = arrivals_map.get(pid, 0)
                except Exception as e:
                    print(e)
                    pass

            # Merge departures counts
            if property_ids and departures_resp:
                try:
                    dep_map = {}
                    ddata = departures_resp.get("data", {})
                    dep_items = ddata.get("partnerReservation", {}).get("departuresCount", [])
                    for di in dep_items:
                        dep_map[str(di.get("propertyId"))] = int(di.get("count", 0))
                    
                    for item in operations_data:
                        pid = item.get("propertyId")
                        if pid in dep_map:
                            item["departuresInFortyEightHours"] = dep_map.get(pid, 0)
                except Exception as e:
                    print(e)
                    pass

            # Merge partner messages counts
            if property_ids and messages_resp:
                try:
                    msg_map = {}
                    mdata = messages_resp.get("data", {})
                    msg_items = mdata.get("partnerMessaging", {}).get("getPartnerMessagesCount", [])
                    for mi in msg_items:
                        pid = str(mi.get("propertyId"))
                        msg_map[pid] = {
                            "bookingMessagesCount": int(mi.get("bookingMessagesCount", 0)),
                            "guestMessagesCount": int(mi.get("guestMessagesCount", 0)),
                        }
                    
                    for item in operations_data:
                        pid = item.get("propertyId")
                        if pid in msg_map:
                            item["bookingDotComMessages"] = msg_map[pid]["bookingMessagesCount"]
                            item["guestMessages"] = msg_map[pid]["guestMessagesCount"]
                except Exception as e:
                    print(e)
                    pass

            # Parse hotels performance metrics to expected shape
            hotels_metrics_list = []
            try:
                hp_data = hotels_performance_resp.get("data", {})
                hp = hp_data.get("partnerMetrics", {}).get("hotelsPerformanceMetrics", {})
                metrics_items = hp.get("hotelsPerformanceMetrics", [])
                for it in metrics_items:
                    hotels_metrics_list.append({
                        "propertyId": str(it.get("propertyId")),
                        "metrics": it.get("metrics", []),
                    })
            except Exception as e:
                print(e)
                pass

            # Process settings data (genius, preferred, minLos, geoRates, mobileRates, propertyScore)
            settings_map = {pid: {
                "propertyId": pid,
                "geniusData": None,
                "preferredDetails": None,
                "minLosDetails": None,
                "settingsGeoRates": None,
                "settingsMobileRates": None,
                "propertyScoreDetails": None,
            } for pid in property_ids}

            # Process genius data
            try:
                gdata = genius_resp.get("data", {})
                items = gdata.get("partnerProperty", {}).get("settingsGenius", {}).get("data", [])
                for it in items:
                    pid = str(it.get("propertyId"))
                    if pid in settings_map:
                        settings_map[pid]["geniusData"] = it
            except Exception as e:
                print(e)
                pass

            # Process preferred data
            try:
                pdata = preferred_resp.get("data", {})
                items = pdata.get("partnerProperty", {}).get("preferredDetails", {}).get("data", [])
                for it in items:
                    pid = str(it.get("propertyId"))
                    if pid in settings_map:
                        settings_map[pid]["preferredDetails"] = it
            except Exception as e:
                print(e)
                pass

            # Process minLos data
            try:
                mldata = minlos_resp.get("data", {})
                items = mldata.get("partnerProperty", {}).get("minLosDetails", {}).get("data", [])
                for it in items:
                    pid = str(it.get("propertyId"))
                    if pid in settings_map:
                        settings_map[pid]["minLosDetails"] = it
            except Exception as e:
                print(e)
                pass

            # Process geo rates data
            try:
                gldata = geo_resp.get("data", {})
                items = gldata.get("partnerProperty", {}).get("settingsGeoRates", {}).get("data", [])
                for it in items:
                    pid = str(it.get("propertyId"))
                    if pid in settings_map:
                        settings_map[pid]["settingsGeoRates"] = it
            except Exception as e:
                print(e)
                pass

            # Process mobile rates data
            try:
                mrdata = mobile_resp.get("data", {})
                items = mrdata.get("partnerProperty", {}).get("settingsMobileRates", {}).get("data", [])
                for it in items:
                    pid = str(it.get("propertyId"))
                    if pid in settings_map:
                        settings_map[pid]["settingsMobileRates"] = it
            except Exception as e:
                print(e)
                pass

            # Process property score data
            try:
                psdata = pscore_resp.get("data", {})
                items = psdata.get("partnerProperty", {}).get("propertyScoreDetails", {}).get("data", [])
                for it in items:
                    pid = str(it.get("propertyId"))
                    if pid in settings_map:
                        settings_map[pid]["propertyScoreDetails"] = it
            except Exception as e:
                print(e)
                pass

            settings_list = list(settings_map.values()) if settings_map else []

            # Create the final booking admin data structure
            booking_admin_data = {
                "operatorId": str(operator.id),
                "groupHomePage": {
                    "operationsData": operations_data,
                    "hotelsPerformanceMetrics": hotels_metrics_list,
                    "settingsData": settings_list,
                }
            }
            
            existing_data = await self.booking_admin_model.collection.find_one({"operatorId": operator_id})
            if existing_data:
                booking_admin_data = self.merge_json(existing_data, booking_admin_data)
            
            # Save to database
            await self.booking_admin_model.save_or_update_booking_admin_data(operator_id,booking_admin_data)
            return {
                "success": True,
                "data": None
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to map and save booking admin data: {str(e)}"
            }
