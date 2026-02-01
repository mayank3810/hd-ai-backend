"""
Async MongoDB helper using Motor for improved performance.
Motor is the async driver for MongoDB in Python.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import os
import certifi
from dotenv import load_dotenv

load_dotenv()


class AsyncMongoDB:
    """Async MongoDB connection manager using Motor"""
    client: AsyncIOMotorClient = None

    @classmethod
    def connect(cls, uri: str):
        """Establish async MongoDB connection"""
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
    async def close(cls):
        """Close async MongoDB connection"""
        if cls.client:
            cls.client.close()

