from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class ExportFormat(str, Enum):
    CSV = "csv"
    # Can add more formats in future like EXCEL = "xlsx"

class ExportResponse(BaseModel):
    file_url: str
    expiry_time: Optional[int] = None  # Time in seconds until the URL expires
