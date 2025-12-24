# -*- coding: utf-8 -*-
"""
設備狀態模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class EquipmentStatusType(str, enum.Enum):
    NORMAL = "normal"
    WARNING = "warning"
    DOWN = "down"


class EquipmentStatus(Base):
    """設備狀態"""
    __tablename__ = "equipment_status"
    
    id = Column(Integer, primary_key=True, index=True)
    exam_code = Column(String(50), nullable=False, index=True)  # 對應檢查項目
    
    status = Column(String(20), default=EquipmentStatusType.NORMAL.value)
    issue_description = Column(Text, nullable=True)
    
    reported_at = Column(DateTime, default=datetime.utcnow)
    reported_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 關聯
    reporter = relationship("User", foreign_keys=[reported_by])
    resolver = relationship("User", foreign_keys=[resolved_by])
    
    def __repr__(self):
        return f"<Equipment {self.exam_code} {self.status}>"
    
    @property
    def is_resolved(self) -> bool:
        return self.resolved_at is not None
