# -*- coding: utf-8 -*-
"""
資料庫連線與初始化 - Phase 7 更新：完整欄位遷移
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


def check_and_add_column(conn, table_name: str, column_name: str, column_type: str, default_value=None):
    """檢查並新增欄位"""
    try:
        result = conn.execute(text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' AND column_name = '{column_name}'
        """))
        
        if result.fetchone() is None:
            # 欄位不存在，新增它
            if default_value is not None:
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT {default_value}"
            else:
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            
            conn.execute(text(sql))
            conn.commit()
            print(f"✅ 已新增 {table_name}.{column_name} 欄位")
            return True
        return False
    except Exception as e:
        print(f"⚠️ 檢查 {table_name}.{column_name}: {e}")
        return False


def run_migrations():
    """執行資料庫遷移"""
    with engine.connect() as conn:
        print("🔄 檢查資料庫欄位...")
        
        # exams 表欄位
        check_and_add_column(conn, 'exams', 'duration_minutes', 'INTEGER', '15')
        check_and_add_column(conn, 'exams', 'capacity', 'INTEGER', '5')
        check_and_add_column(conn, 'exams', 'location', 'VARCHAR(100)', "''")
        check_and_add_column(conn, 'exams', 'is_active', 'BOOLEAN', 'true')
        check_and_add_column(conn, 'exams', 'created_at', 'TIMESTAMP', 'NOW()')
        check_and_add_column(conn, 'exams', 'updated_at', 'TIMESTAMP', 'NOW()')
        
        # users 表欄位
        check_and_add_column(conn, 'users', 'line_id', 'VARCHAR(100)', 'NULL')
        check_and_add_column(conn, 'users', 'last_login_at', 'TIMESTAMP', 'NULL')
        check_and_add_column(conn, 'users', 'permissions', 'TEXT', 'NULL')
        
        # patients 表欄位
        check_and_add_column(conn, 'patients', 'vip_level', 'INTEGER', '0')
        check_and_add_column(conn, 'patients', 'is_active', 'BOOLEAN', 'true')
        
        # equipment 表欄位
        check_and_add_column(conn, 'equipment', 'description', 'TEXT', 'NULL')
        
        print("✅ 欄位檢查完成")


def init_db():
    """初始化資料庫"""
    # 導入所有 models 以便建立表格
    from .models import user, patient, exam, tracking, equipment
    
    # 建立表格（如果不存在）
    Base.metadata.create_all(bind=engine)
    
    # 執行遷移
    run_migrations()
    
    print("✅ 資料庫初始化完成")
