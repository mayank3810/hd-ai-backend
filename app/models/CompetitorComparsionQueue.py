from app.helpers.Database import MongoDB
from bson import ObjectId
from app.schemas.CompetitorComparison import CompetitorComparisonViewSchema
from datetime import datetime
import os

class CompetitorComparisonQueue:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="CompetitorComparisonQueue"):
        self.collection = MongoDB.get_database(db_name)[collection_name]