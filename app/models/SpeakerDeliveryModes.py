"""
MongoDB model for delivery mode options (deliveryModes collection).
"""
from typing import Optional

from app.models.SpeakerOptionCatalog import SpeakerOptionCatalogModel

DELIVERY_MODES_COLLECTION = "deliveryModes"


class SpeakerDeliveryModesModel(SpeakerOptionCatalogModel):
    def __init__(self, db_name: Optional[str] = None):
        super().__init__(DELIVERY_MODES_COLLECTION, db_name)
