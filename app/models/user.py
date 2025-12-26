# -*- coding: utf-8 -*-
"""
使用者模型 - 匹配現有資料庫結構
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
    """使用者 - 匹配現有資料庫結構"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # ⚠️ 使用現有欄位名稱 line_id（不是 line_user_id）
    line_id = Column(String(100), unique=True, nullable=True, index=True)
    
    display_name = Column(String(100), nullable=True)
    picture_url = Column(Text, nullable=True)
    
    role = Column(String(20), default=UserRole.LEADER.value)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # ⚠️ 使用現有欄位名稱 last_login_at（不是 last_login）
    last_login_at = Column(DateTime, nullable=True)
    
    # ⚠️ 保留現有 permissions 欄位
    permissions = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<User {self.display_name} ({self.role})>"
    
    @property
    def role_display_name(self) -> str:
        """取得角色顯示名稱"""
        return get_role_display_name(self.role)
    
    # 兼容性別名
    @property
    def line_user_id(self):
        """兼容舊程式碼"""
        return self.line_id
    
    @line_user_id.setter
    def line_user_id(self, value):
        self.line_id = value
    
    @property
    def last_login(self):
        """兼容舊程式碼"""
        return self.last_login_at
    
    @last_login.setter
    def last_login(self, value):
        self.last_login_at = value
    
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
