# -*- coding: utf-8 -*-
"""
系統設定模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from ..database import Base


class SystemSetting(Base):
    """系統設定"""
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<SystemSetting {self.key}={self.value}>"


# 預設設定值
DEFAULT_SETTINGS = {
    "default_user_role": {
        "value": "leader",
        "description": "新用戶預設角色（pending/coordinator/dispatcher/leader）"
    },
}
