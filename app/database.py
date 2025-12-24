# -*- coding: utf-8 -*-
"""
高檢病人動態系統 - 資料庫連線
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# 建立引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Session 工廠
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基礎模型類別
Base = declarative_base()


def get_db():
    """取得資料庫 Session（用於 FastAPI Depends）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化資料庫（建立所有資料表）"""
    # 匯入所有模型以確保它們被註冊
    from .models import user, patient, exam, tracking, equipment
    
    Base.metadata.create_all(bind=engine)
    print("✅ 資料庫初始化完成")
