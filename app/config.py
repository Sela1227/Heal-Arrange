# -*- coding: utf-8 -*-
"""
設定檔 - 環境變數
新增 LINE Messaging API 設定
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """應用程式設定"""
    
    # 應用程式
    APP_NAME: str = "高檢病人動態系統"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 資料庫
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    
    # Session / JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    
    # LINE Login OAuth
    LINE_CHANNEL_ID: str = os.getenv("LINE_CHANNEL_ID", "")
    LINE_CHANNEL_SECRET: str = os.getenv("LINE_CHANNEL_SECRET", "")
    LINE_REDIRECT_URI: str = os.getenv("LINE_REDIRECT_URI", "http://localhost:8000/auth/callback")
    
    # LINE Messaging API（推播用）
    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    
    # 通知設定
    NOTIFY_ON_ASSIGNMENT: bool = os.getenv("NOTIFY_ON_ASSIGNMENT", "true").lower() == "true"
    NOTIFY_ON_NEXT_STATION: bool = os.getenv("NOTIFY_ON_NEXT_STATION", "true").lower() == "true"
    NOTIFY_ON_EQUIPMENT_FAILURE: bool = os.getenv("NOTIFY_ON_EQUIPMENT_FAILURE", "true").lower() == "true"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
