# -*- coding: utf-8 -*-
"""
資料庫連線與初始化 - Phase 7 更新：自動遷移
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """取得資料庫 session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations():
    """執行資料庫遷移"""
    with engine.connect() as conn:
        # Phase 7: 新增 capacity 欄位
        try:
            # 檢查欄位是否存在
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'exams' AND column_name = 'capacity'
            """))
            
            if result.fetchone() is None:
                # 欄位不存在，新增它
                conn.execute(text("""
                    ALTER TABLE exams ADD COLUMN capacity INTEGER DEFAULT 5 NOT NULL
                """))
                conn.commit()
                print("✅ 已新增 exams.capacity 欄位")
            else:
                print("✅ exams.capacity 欄位已存在")
                
        except Exception as e:
            print(f"⚠️ 遷移檢查: {e}")


def init_db():
    """初始化資料庫"""
    # 導入所有 models 以便建立表格
    from .models import user, patient, exam, tracking, equipment
    
    # 建立表格（如果不存在）
    Base.metadata.create_all(bind=engine)
    
    # 執行遷移
    run_migrations()
    
    print("✅ 資料庫初始化完成")
