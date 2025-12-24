# -*- coding: utf-8 -*-
"""
設備狀態模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class EquipmentStatus(str, enum.Enum):
    NORMAL = "normal"      # 正常
    WARNING = "warning"    # 警告
    BROKEN = "broken"      # 故障


class Equipment(Base):
    """設備"""
    __tablename__ = "equipment"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    location = Column(String(50), nullable=False, index=True)  # 對應檢查站代碼
    equipment_type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    
    status = Column(String(20), default=EquipmentStatus.NORMAL.value)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Equipment {self.name} @ {self.location}>"


class EquipmentLog(Base):
    """設備操作日誌"""
    __tablename__ = "equipment_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    
    action = Column(String(50), nullable=False)  # report_failure, repair, maintenance
    old_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    equipment = relationship("Equipment")
    operator = relationship("User")
    
    def __repr__(self):
        return f"<EquipmentLog {self.action} @ {self.created_at}>"
