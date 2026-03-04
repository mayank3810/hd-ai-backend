"""Service for Opportunities CRUD operations."""

from app.models.Opportunity import OpportunityModel


class OpportunityService:
    def __init__(self):
        self.model = OpportunityModel()

    async def list_opportunities(self, page: int = 1, limit: int = 10) -> dict:
        """List opportunities with pagination. page is 1-based."""
        skip = (page - 1) * limit
        opportunities = await self.model.get_list(skip=skip, limit=limit)
        total = await self.model.count()
        return {
            "opportunities": opportunities,
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit if limit > 0 else 0,
        }

    async def delete_opportunity(self, opportunity_id: str) -> bool:
        """Delete an opportunity by ID. Returns True if deleted."""
        return await self.model.delete_by_id(opportunity_id)
