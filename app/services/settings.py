# -*- coding: utf-8 -*-
"""
系統設定服務
"""

from typing import Optional
from sqlalchemy.orm import Session
from ..models.settings import SystemSetting, DEFAULT_SETTINGS


def get_setting(db: Session, key: str, default: str = None) -> Optional[str]:
    """取得設定值"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if setting:
        return setting.value
    
    # 回傳預設值
    if key in DEFAULT_SETTINGS:
        return DEFAULT_SETTINGS[key]["value"]
    
    return default


def set_setting(db: Session, key: str, value: str, updated_by: int = None) -> SystemSetting:
    """設定值"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    
    if setting:
        setting.value = value
        setting.updated_by = updated_by
    else:
        description = DEFAULT_SETTINGS.get(key, {}).get("description", "")
        setting = SystemSetting(
            key=key,
            value=value,
            description=description,
            updated_by=updated_by,
        )
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    return setting


def get_all_settings(db: Session) -> dict:
    """取得所有設定"""
    settings = db.query(SystemSetting).all()
    result = {}
    
    # 先填入預設值
    for key, info in DEFAULT_SETTINGS.items():
        result[key] = {
            "value": info["value"],
            "description": info["description"],
            "is_default": True,
        }
    
    # 覆蓋資料庫中的值
    for s in settings:
        result[s.key] = {
            "value": s.value,
            "description": s.description or DEFAULT_SETTINGS.get(s.key, {}).get("description", ""),
            "is_default": False,
            "updated_at": s.updated_at,
        }
    
    return result


def init_default_settings(db: Session) -> int:
    """初始化預設設定"""
    count = 0
    for key, info in DEFAULT_SETTINGS.items():
        existing = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not existing:
            setting = SystemSetting(
                key=key,
                value=info["value"],
                description=info["description"],
            )
            db.add(setting)
            count += 1
    
    db.commit()
    return count


def get_default_user_role(db: Session) -> str:
    """取得新用戶預設角色"""
    return get_setting(db, "default_user_role", "pending")
