"""
MongoDB model for speaking format options (speakingFormats collection).
"""
from typing import Optional

from app.models.SpeakerOptionCatalog import SpeakerOptionCatalogModel

SPEAKING_FORMATS_COLLECTION = "speakingFormats"


class SpeakerSpeakingFormatsModel(SpeakerOptionCatalogModel):
    def __init__(self, db_name: Optional[str] = None):
        super().__init__(SPEAKING_FORMATS_COLLECTION, db_name)
