from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import os
import certifi

from dotenv import load_dotenv

load_dotenv()

class MongoDB:
    """Async MongoDB client using Motor for better performance"""
    client: AsyncIOMotorClient = None

    @classmethod
    def connect(cls, uri: str):
        """Connect to MongoDB using Motor async client"""
        cls.client = AsyncIOMotorClient(uri, tlsCAFile=certifi.where())

    @classmethod
    def get_database(cls, db_name: str):
        """Get async database instance"""
        return cls.client[db_name]
    
    @classmethod
    async def connection_status(cls):
        """Check async connection status"""
        try:
            await cls.client.admin.command('ping')
            return {"status": "connected", "db": os.getenv('DB_NAME')}
        except ConnectionFailure as e:
            return {"status": "disconnected", "db": os.getenv('DB_NAME')}
    
    @classmethod
    async def async_connection_status(cls):
        """Alias for connection_status for backward compatibility"""
        return await cls.connection_status()