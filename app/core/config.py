from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    ADMIN_PHONE: Optional[str] = "09019244403"
    APP_NAME: str = "Venix Shop API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    MELI_USERNAME: str
    MELI_API_KEY: str
    MELI_BODY_ID: int
    
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://venixpodshop.com",
        "https://www.venixpodshop.com",
        "https://venixpodshop.ir",
        "https://www.venixpodshop.ir",
        "https://admin.venixpodshop.com",
        "https://admin.venixpodshop.ir",
        "https://api.venixpodshop.com",
        "https://api.venixpodshop.ir",
    ]

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

@lru_cache()
def get_settings() -> Settings:
    return Settings()
