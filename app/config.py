# -*- coding: utf-8 -*-
"""
高檢病人動態系統 - 環境設定
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 應用程式
    APP_NAME: str = "高檢病人動態系統"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 資料庫
    DATABASE_URL: str = "postgresql://localhost/patient_tracking"
    
    # LINE Login
    LINE_CHANNEL_ID: str = ""
    LINE_CHANNEL_SECRET: str = ""
    LINE_REDIRECT_URI: str = ""
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-this"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    
    # 時區
    TZ: str = "Asia/Taipei"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
