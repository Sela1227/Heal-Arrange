# -*- coding: utf-8 -*-
"""
追蹤相關模型
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class TrackingStatus(str, enum.Enum):
    WAITING = "waiting"      # 等候中
    IN_EXAM = "in_exam"      # 檢查中
    MOVING = "moving"        # 移動中
    COMPLETED = "completed"  # 完成


class TrackingAction(str, enum.Enum):
    ASSIGN = "assign"        # 指派
    ARRIVE = "arrive"        # 到達
    START = "start"          # 開始
    COMPLETE = "complete"    # 完成
    HANDOVER = "handover"    # 交接


class CoordinatorAssignment(Base):
    """個管師-病人指派"""
    __tablename__ = "coordinator_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    exam_date = Column(Date, nullable=False, index=True)
    
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    coordinator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 指派的調度員
    
    is_active = Column(Boolean, default=True)  # 支援交接：舊的標 False
    
    # 關聯
    patient = relationship("Patient", foreign_keys=[patient_id])
    coordinator = relationship("User", foreign_keys=[coordinator_id])
    
    def __repr__(self):
        return f"<Assignment Patient#{self.patient_id} -> User#{self.coordinator_id}>"


# 補上 import
from sqlalchemy import Boolean


class PatientTracking(Base):
    """病人即時位置"""
    __tablename__ = "patient_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    exam_date = Column(Date, nullable=False, index=True)
    
    # 目前狀態
    current_location = Column(String(50), nullable=True)  # 'LOBBY' / 'CT' / 'MRI'...
    current_status = Column(String(20), default=TrackingStatus.WAITING.value)
    
    # 下一站（調度員指派）
    next_exam_code = Column(String(50), nullable=True)
    
    # 更新資訊
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 關聯
    patient = relationship("Patient")
    
    def __repr__(self):
        return f"<Tracking Patient#{self.patient_id} @ {self.current_location}>"


class TrackingHistory(Base):
    """追蹤歷程"""
    __tablename__ = "tracking_history"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    exam_date = Column(Date, nullable=False, index=True)
    
    location = Column(String(50), nullable=True)
    status = Column(String(20), nullable=True)
    action = Column(String(20), nullable=False)  # assign/arrive/start/complete/handover
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    notes = Column(Text, nullable=True)
    
    # 關聯
    patient = relationship("Patient")
    operator = relationship("User")
    
    def __repr__(self):
        return f"<History Patient#{self.patient_id} {self.action} @ {self.timestamp}>"
