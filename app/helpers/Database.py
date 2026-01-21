from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
import certifi

from dotenv import load_dotenv

load_dotenv()

class MongoDB:
    client: AsyncIOMotorClient = None
    sync_client: MongoClient = None

    @classmethod
    def connect(cls, uri: str):
        cls.client = AsyncIOMotorClient(uri, tlsCAFile=certifi.where())

    @classmethod
    def get_database(cls, db_name: str):
        """Returns async database - for backward compatibility, use get_async_database instead"""
        return cls.client[db_name]
    
    @classmethod
    def get_async_database(cls, db_name: str):
        return cls.client[db_name]
    
    @classmethod
    def sync_connect(cls, uri: str):
        cls.sync_client = MongoClient(uri, tlsCAFile=certifi.where())
    
    @classmethod
    def get_sync_database(cls, db_name: str):
        """Returns synchronous database using PyMongo"""
        return cls.sync_client[db_name]
    
    @classmethod
    async def connection_status(cls):
        try:
            await cls.client.admin.command('ping')
            return {"status": "connected", "db": os.getenv('DB_NAME')}
        except ConnectionFailure as e:
            return {"status": "disconnected", "db": os.getenv('DB_NAME')}
    
    @classmethod
    async def async_connection_status(cls):
        """Alias for connection_status for backward compatibility"""
        return await cls.connection_status()