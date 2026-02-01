from app.helpers.Database import MongoDB
from bson import ObjectId
from app.schemas.CompetitorProperty import CompetitorPropertySchema
from datetime import datetime
import os

class ExcelImportsForListing:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="ExcelImportsForListingQueue"):
        self.collection = MongoDB.get_database(db_name)[collection_name]
