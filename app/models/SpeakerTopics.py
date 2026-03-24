"""
MongoDB model for Speaker Topics (used in onboarding topics step).
"""
from typing import Optional

from app.models.SpeakerOptionCatalog import SpeakerOptionCatalogModel

SPEAKER_TOPICS_COLLECTION = "speakerTopics"


class SpeakerTopicsModel(SpeakerOptionCatalogModel):
    """Fetches and creates topic options in speakerTopics collection."""

    def __init__(self, db_name: Optional[str] = None):
        super().__init__(SPEAKER_TOPICS_COLLECTION, db_name)
