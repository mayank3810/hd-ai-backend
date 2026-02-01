from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    # MongoDB Settings
    MONGODB_URL: str
    MONGODB_DB_NAME: str

    # JWT Settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Email Settings
    FROM_EMAIL_ID: str
    POSTMARK_SERVER_API_TOKEN: str

    # Azure Storage Settings
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_CONTAINER_NAME: Optional[str] = None

    # CORS Settings
    CORS_ORIGINS: str = "*"
    CORS_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS"
    CORS_HEADERS: str = "*"
    
    # Image Processing Settings
    IMG_MAX_EDGE: int = 1024
    CACHE_DIR: str = "cache"

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache to prevent multiple reads of the .env file
    """
    return Settings()

