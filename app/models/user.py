# -*- coding: utf-8 -*-
"""
使用者模型 - 支援多權限制
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class Permission(str, enum.Enum):
    """權限類型"""
    ADMIN = "admin"           # 管理員：帳號管理、系統設定
    DISPATCHER = "dispatcher" # 調度員：病人指派、即時監控
    COORDINATOR = "coordinator"  # 個管師：陪同病人、狀態回報


class UserStatus(str, enum.Enum):
    """帳號狀態"""
    PENDING = "pending"   # 待審核
    ACTIVE = "active"     # 已啟用
    DISABLED = "disabled" # 已停用


class User(Base):
    """使用者"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    # 資料庫欄位名稱是 line_id
    line_user_id = Column("line_id", String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=True)
    picture_url = Column(String(500), nullable=True)
    
    # 新權限系統：JSON 陣列存放多個權限
    # 例如: ["admin", "dispatcher"] 表示同時擁有管理員和調度員權限
    permissions = Column(JSON, default=list, nullable=True)
    
    # 保留 role 欄位用於向後兼容和顯示主要角色
    # 值為 "pending" | "active" | "disabled"
    role = Column(String(20), default=UserStatus.PENDING.value)
    
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    # 資料庫欄位名稱是 last_login_at
    last_login = Column("last_login_at", DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User {self.display_name}>"
    
    # ===== 權限檢查方法 =====
    
    def has_permission(self, permission: str) -> bool:
        """檢查是否擁有特定權限"""
        if not self.permissions:
            return False
        return permission in self.permissions
    
    def has_any_permission(self, *permissions: str) -> bool:
        """檢查是否擁有任一權限"""
        if not self.permissions:
            return False
        return any(p in self.permissions for p in permissions)
    
    def has_all_permissions(self, *permissions: str) -> bool:
        """檢查是否擁有所有指定權限"""
        if not self.permissions:
            return False
        return all(p in self.permissions for p in permissions)
    
    @property
    def is_admin(self) -> bool:
        """是否為管理員"""
        return self.has_permission(Permission.ADMIN.value)
    
    @property
    def is_dispatcher(self) -> bool:
        """是否為調度員"""
        return self.has_permission(Permission.DISPATCHER.value)
    
    @property
    def is_coordinator(self) -> bool:
        """是否為個管師"""
        return self.has_permission(Permission.COORDINATOR.value)
    
    @property
    def is_pending(self) -> bool:
        """是否待審核（無任何權限）"""
        return not self.permissions or len(self.permissions) == 0
    
    @property
    def is_approved(self) -> bool:
        """是否已核准（有任何權限）"""
        return self.permissions and len(self.permissions) > 0
    
    def add_permission(self, permission: str):
        """新增權限"""
        if self.permissions is None:
            self.permissions = []
        if permission not in self.permissions:
            self.permissions = self.permissions + [permission]
            # 有權限後，狀態改為 active
            if self.role == UserStatus.PENDING.value:
                self.role = UserStatus.ACTIVE.value
    
    def remove_permission(self, permission: str):
        """移除權限"""
        if self.permissions and permission in self.permissions:
            self.permissions = [p for p in self.permissions if p != permission]
    
    def set_permissions(self, permissions: list):
        """設定權限列表"""
        self.permissions = permissions or []
        # 更新狀態
        if self.permissions:
            self.role = UserStatus.ACTIVE.value
        else:
            self.role = UserStatus.PENDING.value
    
    @property
    def permission_labels(self) -> list:
        """取得權限的中文標籤"""
        labels = []
        if self.is_admin:
            labels.append("管理員")
        if self.is_dispatcher:
            labels.append("調度員")
        if self.is_coordinator:
            labels.append("個管師")
        return labels
    
    @property
    def primary_role_label(self) -> str:
        """取得主要角色標籤（用於顯示）"""
        if self.is_pending:
            return "待審核"
        if not self.is_active:
            return "已停用"
        return "、".join(self.permission_labels) or "無權限"


# ===== 保留舊的 UserRole 用於向後兼容 =====
class UserRole(str, enum.Enum):
    """舊角色定義（向後兼容）"""
    ADMIN = "admin"
    DISPATCHER = "dispatcher"
    COORDINATOR = "coordinator"
    PENDING = "pending"


# ===== 權限常數 =====
ALL_PERMISSIONS = [
    {"value": Permission.ADMIN.value, "label": "管理員", "description": "帳號管理、系統設定、檢查項目/設備管理"},
    {"value": Permission.DISPATCHER.value, "label": "調度員", "description": "病人指派、即時監控、報表查看"},
    {"value": Permission.COORDINATOR.value, "label": "個管師", "description": "陪同病人、狀態回報"},
]
