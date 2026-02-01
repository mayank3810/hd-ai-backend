from datetime import datetime
from pydantic import BaseModel,Field
from typing import Optional
from bson import ObjectId

class ReportData(BaseModel):
    revenueOnTheBooks:Optional[list]=None
    leaderboard:Optional[list]=None
    segmentOccupancyPacing:Optional[list]=None
    opportunities:Optional[list]=None
    thirtyDaysOutlook:Optional[list]=None
    pacing:Optional[list]=None
    forecastRentalRevenueOccupancy:Optional[list]=None
    thisMonthDashboard:Optional[list]=None
    lastMonthDashboard:Optional[list]=None
    nextMonthDashboard:Optional[list]=None
    lastSevenDaysDashboard:Optional[list]=None
    lastThirtyDaysDashboard:Optional[list]=None
    lastYearThisMonthDashboard:Optional[list]=None
    pricingDashboard:Optional[list]=None
    lastYearThisMonthDashboard:Optional[list]=None


class PricelabsAdminData(BaseModel):
    operatorId: str
    reportData:ReportData
    createdAt:datetime = Field(default_factory=datetime.utcnow)
    updatedAt:datetime = Field(default_factory=datetime.utcnow)    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        populate_by_name = True
        use_enum_values = True
