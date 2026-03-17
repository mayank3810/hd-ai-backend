"""Service for Opportunities CRUD operations and speaker-based matching via Pinecone."""

import asyncio
import os
from datetime import date, datetime
from typing import List

from app.models.Opportunity import OpportunityModel
from app.models.SpeakerProfile import SpeakerProfileModel
from app.models.MatchedOpportunities import MatchedOpportunitiesModel
from app.helpers.PineconeOpportunityStore import PineconeOpportunityStore, OpportunityTextBuilder
from app.agents.OpportunitySpeakerMatchAgent import OpportunitySpeakerMatchAgent


# Minimum similarity score (0–1) to consider a match; below 50% we do not consider it matching
MIN_SIMILARITY_THRESHOLD = 0.4


def _is_future_opportunity(opp: dict) -> bool:
    """True if opportunity has start_date on or after today; otherwise False."""
    start = opp.get("start_date")
    if not start or not str(start).strip():
        return False
    s = str(start).strip()[:10]
    try:
        start_date = datetime.strptime(s, "%Y-%m-%d").date()
        return start_date >= date.today()
    except ValueError:
        return False


class OpportunityService:
    def __init__(
        self,
        opportunity_model: OpportunityModel = None,
        speaker_profile_model: SpeakerProfileModel = None,
        pinecone_store: PineconeOpportunityStore = None,
        matched_opportunities_model: MatchedOpportunitiesModel = None,
    ):
        self.model = opportunity_model or OpportunityModel()
        self.speaker_profile_model = speaker_profile_model or SpeakerProfileModel()
        self.pinecone_store = pinecone_store or PineconeOpportunityStore()
        self.matched_opportunities_model = matched_opportunities_model or MatchedOpportunitiesModel()

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

    async def get_matched_opportunities_for_speaker(
        self,
        speaker_profile_id: str,
        min_results: int = 5,
        max_results: int = 10,
    ) -> List[dict]:
        """
        Get opportunities matched to a speaker profile via Pinecone vector search.
        Extracts topics, speaking_formats, delivery_mode, target_audiences, talk_description from profile,
        finds similar opportunities in Pinecone (min 5, max 10), returns full opportunity docs from MongoDB.
        Only opportunities with start_date on or after today are returned (no past opportunities).
        Only matches with similarity score >= min_score (env OPPORTUNITY_MIN_SIMILARITY_SCORE or 0.5) are included.
        """
        profile = await self.speaker_profile_model.get_profile(speaker_profile_id)
        if not profile:
            return []
        if not self.pinecone_store.is_configured():
            return []
        query_text = OpportunityTextBuilder.from_speaker_profile(profile)
        if not query_text:
            return []
        # Only consider matches with score >= 50%; env can override
        min_score = MIN_SIMILARITY_THRESHOLD
        try:
            env_val = os.getenv("OPPORTUNITY_MIN_SIMILARITY_SCORE")
            if env_val is not None:
                min_score = float(env_val)
        except (TypeError, ValueError):
            min_score = MIN_SIMILARITY_THRESHOLD
        # Query more than max_results so we have buffer after filtering by score and past opportunities
        # Run Pinecone (sync/blocking) in thread pool so the event loop is not blocked
        top_k = max(max_results * 3, 30)
        opportunity_ids, scores = await asyncio.to_thread(
            self.pinecone_store.query_similar_opportunity_ids,
            query_text,
            top_k,
            min_score,
        )
        if not opportunity_ids:
            return []
        id_to_score = dict(zip(opportunity_ids, scores))
        opportunities = await self.model.get_by_ids(opportunity_ids)
        # Keep only future opportunities (start_date >= today)
        future_opportunities = [o for o in opportunities if _is_future_opportunity(o)]
        # Return up to max_results, preserving similarity order; attach similarity_score to each
        result = future_opportunities[:max_results]
        for opp in result:
            if opp.get("_id") is not None:
                opp["_id"] = str(opp["_id"])
            opp["similarity_score"] = round(id_to_score.get(str(opp.get("_id")), 0.0), 4)
        return result

    async def run_matching_and_save(
        self,
        speaker_profile_id: str,
        match_agent: OpportunitySpeakerMatchAgent = None,
    ) -> None:
        """
        Run vector matching, then filter each opportunity with an AI agent (does it match the speaker?),
        and save only the agent-approved opportunity ids to matchedOpportunities.
        Intended to be run as a background job after match-by-speaker API is hit.
        """
        profile = await self.speaker_profile_model.get_profile(speaker_profile_id)
        if not profile:
            await self.matched_opportunities_model.upsert_by_speaker_id(speaker_profile_id, [])
            return
        opportunities = await self.get_matched_opportunities_for_speaker(speaker_profile_id)
        if not opportunities:
            await self.matched_opportunities_model.upsert_by_speaker_id(speaker_profile_id, [])
            return
        agent = match_agent or OpportunitySpeakerMatchAgent()
        filtered = []
        for opp in opportunities:
            is_match = await asyncio.to_thread(agent.is_match, profile, opp)
            if is_match:
                filtered.append(opp)
        opportunity_ids = [str(o.get("_id")) for o in filtered if o.get("_id") is not None]
        await self.matched_opportunities_model.upsert_by_speaker_id(speaker_profile_id, opportunity_ids)

    async def get_matched_opportunities_by_speaker_id(self, speaker_profile_id: str) -> List[dict]:
        """
        Get matched opportunities stored for this speaker (from matchedOpportunities collection).
        Returns full opportunity documents from MongoDB for all ids in the opportunities array.
        """
        doc = await self.matched_opportunities_model.get_by_speaker_id(speaker_profile_id)
        if not doc or not doc.get("opportunities"):
            return []
        opportunity_ids = doc["opportunities"]
        opportunities = await self.model.get_by_ids(opportunity_ids)
        for opp in opportunities:
            if opp.get("_id") is not None:
                opp["_id"] = str(opp["_id"])
        return opportunities
