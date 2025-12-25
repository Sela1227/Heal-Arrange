# -*- coding: utf-8 -*-
"""
資料庫遷移腳本 - 權限系統升級
將舊的單一 role 轉換為新的多權限 permissions

使用方式：
    python -m app.migrations.migrate_permissions

或在 Python shell 中執行：
    from app.migrations.migrate_permissions import run_migration
    run_migration()
"""

import os
import sys
from sqlalchemy import text
from sqlalchemy.orm import Session

# 確保可以匯入 app 模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal, engine


def check_permissions_column_exists(db: Session) -> bool:
    """檢查 permissions 欄位是否存在"""
    try:
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'permissions'
        """))
        return result.fetchone() is not None
    except Exception:
        return False


def add_permissions_column(db: Session):
    """新增 permissions 欄位"""
    print("📦 新增 permissions 欄位...")
    try:
        db.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS permissions JSON DEFAULT '[]'
        """))
        db.commit()
        print("✅ permissions 欄位已新增")
    except Exception as e:
        print(f"⚠️ 新增欄位時發生錯誤（可能已存在）: {e}")
        db.rollback()


def migrate_roles_to_permissions(db: Session):
    """將舊的 role 轉換為 permissions"""
    print("\n🔄 開始遷移使用者權限...")
    
    # 取得所有使用者
    result = db.execute(text("SELECT id, role, permissions FROM users"))
    users = result.fetchall()
    
    migrated = 0
    skipped = 0
    
    for user in users:
        user_id, role, permissions = user
        
        # 如果已經有 permissions 且不為空，跳過
        if permissions and permissions != [] and permissions != '[]':
            skipped += 1
            continue
        
        # 根據 role 決定 permissions
        if role == 'admin':
            new_permissions = '["admin", "dispatcher", "coordinator"]'
        elif role == 'dispatcher':
            new_permissions = '["dispatcher"]'
        elif role == 'coordinator':
            new_permissions = '["coordinator"]'
        else:  # pending 或其他
            new_permissions = '[]'
        
        # 更新
        db.execute(text("""
            UPDATE users 
            SET permissions = :permissions,
                role = CASE 
                    WHEN :role IN ('admin', 'dispatcher', 'coordinator') THEN 'active'
                    ELSE 'pending'
                END
            WHERE id = :id
        """), {"permissions": new_permissions, "role": role, "id": user_id})
        
        migrated += 1
        print(f"  ✓ 使用者 ID {user_id}: {role} → {new_permissions}")
    
    db.commit()
    print(f"\n✅ 遷移完成！已更新 {migrated} 個使用者，跳過 {skipped} 個")


def run_migration():
    """執行遷移"""
    print("=" * 50)
    print("🚀 權限系統遷移工具")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        # 1. 檢查並新增欄位
        if not check_permissions_column_exists(db):
            add_permissions_column(db)
        else:
            print("✓ permissions 欄位已存在")
        
        # 2. 遷移資料
        migrate_roles_to_permissions(db)
        
        print("\n" + "=" * 50)
        print("🎉 遷移完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 遷移失敗: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def rollback_migration():
    """回滾遷移（如需要）"""
    print("⚠️ 回滾遷移...")
    db = SessionLocal()
    try:
        # 根據 permissions 還原 role
        result = db.execute(text("SELECT id, permissions FROM users"))
        users = result.fetchall()
        
        for user in users:
            user_id, permissions = user
            
            if permissions is None:
                permissions = []
            elif isinstance(permissions, str):
                import json
                permissions = json.loads(permissions)
            
            if 'admin' in permissions:
                new_role = 'admin'
            elif 'dispatcher' in permissions:
                new_role = 'dispatcher'
            elif 'coordinator' in permissions:
                new_role = 'coordinator'
            else:
                new_role = 'pending'
            
            db.execute(text("UPDATE users SET role = :role WHERE id = :id"),
                       {"role": new_role, "id": user_id})
        
        db.commit()
        print("✅ 回滾完成")
        
    except Exception as e:
        print(f"❌ 回滾失敗: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="權限系統遷移工具")
    parser.add_argument("--rollback", action="store_true", help="回滾遷移")
    args = parser.parse_args()
    
    if args.rollback:
        rollback_migration()
    else:
        run_migration()
