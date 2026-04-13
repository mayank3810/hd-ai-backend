import asyncio
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.models.SpeakerProfile import SpeakerProfileModel
from app.models.User import UserModel
from app.schemas.User import AdminCreateUserSchema, AdminUpdateUserSchema, UserSchema
from app.schemas.UserManagement import (
    SpeakerProfileSummary,
    UserPublic,
    UserWithSpeakerProfiles,
    UsersListPagination,
    UsersWithProfilesListData,
)
from datetime import datetime


def _user_to_public(user: UserSchema) -> UserPublic:
    d = user.model_dump(by_alias=True)
    d.pop("password", None)
    oid = d.pop("_id", None)
    return UserPublic(
        id=str(oid) if oid is not None else "",
        email=d["email"],
        fullName=d["fullName"],
        userType=d["userType"],
        address=d.get("address"),
        city=d.get("city"),
        country=d.get("country"),
        zip=d.get("zip"),
        profilePicture=d.get("profilePicture"),
        phone=d.get("phone"),
        adminId=str(d["adminId"]) if d.get("adminId") is not None else None,
        createdOn=d.get("createdOn"),
        updatedOn=d.get("updatedOn"),
    )


def _profile_to_summary(doc: dict) -> SpeakerProfileSummary:
    return SpeakerProfileSummary(
        id=str(doc.get("_id", "")),
        full_name=doc.get("full_name"),
        email=doc.get("email"),
        current_step=doc.get("current_step"),
        isCompleted=doc.get("isCompleted"),
        createdAt=doc.get("createdAt"),
        updatedAt=doc.get("updatedAt"),
    )


class UserManagementService:
    def __init__(self):
        self.user_model = UserModel()
        self.profile_model = SpeakerProfileModel()

    def _auth(self):
        from app.dependencies import get_auth_service

        return get_auth_service()

    async def list_users_with_profiles(
        self, page: int = 1, limit: int = 10
    ) -> Dict[str, Any]:
        try:
            filters: dict = {}
            skip = (page - 1) * limit
            total, users = await asyncio.gather(
                self.user_model.get_documents_count(filters),
                self.user_model.get_users(filters, skip, limit),
            )
            total_pages = (total + limit - 1) // limit if limit else 0
            user_ids: List[str] = []
            for u in users:
                ud = u.model_dump(by_alias=True)
                user_ids.append(str(ud.get("_id")))
            grouped = await self.profile_model.get_profiles_by_user_ids(user_ids)

            out: List[UserWithSpeakerProfiles] = []
            for u, uid in zip(users, user_ids):
                summaries = [
                    _profile_to_summary(p) for p in grouped.get(uid, [])
                ]
                out.append(
                    UserWithSpeakerProfiles(
                        user=_user_to_public(u),
                        speakerProfiles=summaries,
                    )
                )

            data = UsersWithProfilesListData(
                users=out,
                pagination=UsersListPagination(
                    total=total,
                    totalPages=total_pages,
                    currentPage=page,
                    limit=limit,
                ),
            )
            return {
                "success": True,
                "data": data.model_dump(mode="json"),
                "error": None,
            }
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def get_user_with_profiles(self, user_id: str) -> Dict[str, Any]:
        try:
            try:
                oid = ObjectId(user_id)
            except Exception:
                return {
                    "success": False,
                    "data": None,
                    "error": "User not found",
                }
            user = await self.user_model.get_user({"_id": oid})
            if not user:
                return {
                    "success": False,
                    "data": None,
                    "error": "User not found",
                }
            profiles = await self.profile_model.get_profiles_by_user_id(user_id)
            summaries = [_profile_to_summary(p) for p in profiles]
            payload = UserWithSpeakerProfiles(
                user=_user_to_public(user),
                speakerProfiles=summaries,
            )
            return {
                "success": True,
                "data": payload.model_dump(mode="json"),
                "error": None,
            }
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def create_user_by_admin(
        self, user_data: AdminCreateUserSchema, admin_id: str
    ) -> Dict[str, Any]:
        return await self._auth().create_user_by_admin(user_data, admin_id)

    async def update_user_admin(
        self, user_id: str, body: AdminUpdateUserSchema
    ) -> Dict[str, Any]:
        try:
            try:
                ObjectId(user_id)
            except Exception:
                return {
                    "success": False,
                    "data": None,
                    "error": "User not found",
                }
            update_data = body.model_dump(exclude_unset=True)
            if not update_data:
                return {
                    "success": False,
                    "data": None,
                    "error": "No data provided for update.",
                }
            user = await self.user_model.get_user({"_id": ObjectId(user_id)})
            if not user:
                return {
                    "success": False,
                    "data": None,
                    "error": "User not found",
                }
            if "userType" in update_data and update_data["userType"] is not None:
                update_data["userType"] = (
                    update_data["userType"].value
                    if hasattr(update_data["userType"], "value")
                    else update_data["userType"]
                )
            update_data["updatedOn"] = datetime.utcnow()
            await self.user_model.update_user(user_id, update_data)
            return await self.get_user_with_profiles(user_id)
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def delete_user(self, user_id: str) -> Dict[str, Any]:
        return await self._auth().delete_user(user_id)
