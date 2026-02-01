from pydantic import BaseModel
from typing import Any, Optional
from bson import ObjectId

class ServerResponse(BaseModel):
    data: Optional[Any] = None
    success: bool

    class Config:
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "data": {},
                "success": True
            }
        }
