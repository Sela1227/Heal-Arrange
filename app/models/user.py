# -*- coding: utf-8 -*-
"""
使用者模型 - 包含組長角色
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class UserRole(str, enum.Enum):
    """使用者角色"""
    ADMIN = "admin"           # 管理員 - 全部權限
    LEADER = "leader"         # 組長 - 調度員 + 專員
    DISPATCHER = "dispatcher" # 調度員
    COORDINATOR = "coordinator" # 專員（原個管師）
    PENDING = "pending"       # 待審核


# 兼容舊版 - 別名
Permission = UserRole
UserStatus = UserRole


# 角色顯示名稱
ROLE_DISPLAY_NAMES = {
    "admin": "管理員",
    "leader": "組長",
    "dispatcher": "調度員",
    "coordinator": "專員",
    "pending": "待審核",
}

# 所有權限列表（兼容舊版）
ALL_PERMISSIONS = [r.value for r in UserRole]


def get_role_display_name(role: str) -> str:
    """取得角色顯示名稱"""
    return ROLE_DISPLAY_NAMES.get(role, role)


class User(Base):
    """使用者"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    line_user_id = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=True)
    picture_url = Column(Text, nullable=True)
    
    role = Column(String(20), default=UserRole.LEADER.value)  # 預設組長（測試）
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User {self.display_name} ({self.role})>"
    
    @property
    def role_display_name(self) -> str:
        """取得角色顯示名稱"""
        return get_role_display_name(self.role)
    
    def can_access_dispatcher(self) -> bool:
        """是否可以存取調度台"""
        return self.role in [
            UserRole.ADMIN.value,
            UserRole.LEADER.value,
            UserRole.DISPATCHER.value,
        ]
    
    def can_access_coordinator(self) -> bool:
        """是否可以存取專員頁面"""
        return self.role in [
            UserRole.ADMIN.value,
            UserRole.LEADER.value,
            UserRole.COORDINATOR.value,
        ]
    
    def is_admin_role(self) -> bool:
        """是否為管理員"""
        return self.role == UserRole.ADMIN.value
