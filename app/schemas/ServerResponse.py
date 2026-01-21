from pydantic import BaseModel
from typing import Any, Optional

class ServerResponse(BaseModel):
    data: Optional[Any] = None
    success: bool = True
    error: Optional[str] = None

