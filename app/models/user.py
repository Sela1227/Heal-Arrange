# -*- coding: utf-8 -*-
"""
用戶模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from ..database import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DISPATCHER = "dispatcher"
    COORDINATOR = "coordinator"
    PENDING = "pending"  # 等待授權


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    line_id = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    picture_url = Column(String(500), nullable=True)
    
    role = Column(String(20), default=UserRole.PENDING.value, nullable=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User {self.display_name} ({self.role})>"
    
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN.value
    
    @property
    def is_dispatcher(self) -> bool:
        return self.role == UserRole.DISPATCHER.value
    
    @property
    def is_coordinator(self) -> bool:
        return self.role == UserRole.COORDINATOR.value
    
    @property
    def is_pending(self) -> bool:
        return self.role == UserRole.PENDING.value
