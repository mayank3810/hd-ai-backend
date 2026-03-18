"""Class-based service to send matched opportunities to a speaker's email via Postmark."""

import os
from typing import List

from postmarker.core import PostmarkClient

from app.config import get_settings
from app.models.SpeakerProfile import SpeakerProfileModel
from app.services.Opportunity import OpportunityService


class MatchedOpportunitiesEmailService:
    """Sends matched opportunities (event_name + link) to the speaker's email from their profile."""

    def __init__(
        self,
        opportunity_service: OpportunityService = None,
        speaker_profile_model: SpeakerProfileModel = None,
    ):
        self.opportunity_service = opportunity_service or OpportunityService()
        self.speaker_profile_model = speaker_profile_model or SpeakerProfileModel()

    def _get_postmark_client(self) -> PostmarkClient | None:
        """Build Postmark client from env. Returns None if config missing."""
        token = os.getenv("POSTMARK-SERVER-API-TOKEN", None) 
        if not token:
            return None
        return PostmarkClient(token)

    def _get_from_email(self) -> str | None:
        """From address from env."""
        return os.getenv("FROM_EMAIL_ID", None)

    def _get_opportunity_link(self, opportunity_id: str) -> str:
        """Build URL for opening this opportunity (GET opportunity by id API)."""
        base = os.getenv("API_BASE_URL", None)
        base = (base or "").rstrip("/")
        return f"{base}/api/v1/opportunities/{opportunity_id}" if base else f"/api/v1/opportunities/{opportunity_id}"

    def _build_html_body(self, opportunities: List[dict]) -> str:
        """Build HTML email body with only event_name and link per opportunity."""
        rows = []
        for opp in opportunities:
            oid = str(opp.get("_id") or "")
            event_name = (opp.get("event_name") or "").strip() or "Opportunity"
            link = self._get_opportunity_link(oid)
            rows.append(f'<li>{event_name} — <a href="{link}">{link}</a></li>')
        list_html = "\n".join(rows)
        return f"<html><body><ul>\n{list_html}\n</ul></body></html>"

    async def send_matched_opportunities_email(self, speaker_profile_id: str) -> bool:
        """
        Get email from speaker profile, fetch matched opportunities, send one email
        with event_name and link per opportunity via Postmark. Uses FROM_EMAIL_ID and
        POSTMARK-SERVER-API-TOKEN from env.
        Returns True if email was sent, False otherwise (missing profile/email, no opportunities, or Postmark failure).
        """
        profile = await self.speaker_profile_model.get_profile(speaker_profile_id)
        if not profile:
            return False
        to_email = (profile.get("email") or "").strip()
        if not to_email:
            return False
        opportunities, status = await self.opportunity_service.get_matched_opportunities_by_speaker_id(
            speaker_profile_id
        )
        if status != "completed" or not opportunities:
            return False
        from_email = self._get_from_email()
        client = self._get_postmark_client()
        if not from_email or not client:
            return False
        html_body = self._build_html_body(opportunities)
        try:
            client.emails.send(
                From=from_email,
                To=to_email,
                Subject="Your matched speaking opportunities",
                HtmlBody=html_body,
            )
            return True
        except Exception:
            return False
