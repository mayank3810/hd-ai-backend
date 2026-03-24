"""
MongoDB model for Speaker Target Audience (used in onboarding target_audiences step).
Collection name matches seed script: speakerTargetAudeince.
"""
from typing import Optional

from app.models.SpeakerOptionCatalog import SpeakerOptionCatalogModel

SPEAKER_TARGET_AUDIENCE_COLLECTION = "speakerTargetAudeince"


class SpeakerTargetAudienceModel(SpeakerOptionCatalogModel):
    """Fetches and creates target audience options in speakerTargetAudeince collection."""

    def __init__(self, db_name: Optional[str] = None):
        super().__init__(SPEAKER_TARGET_AUDIENCE_COLLECTION, db_name)
