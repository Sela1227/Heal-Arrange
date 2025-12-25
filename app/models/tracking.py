# -*- coding: utf-8 -*-
"""
追蹤模型 - 病人位置與狀態追蹤
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class TrackingStatus(str, enum.Enum):
    """追蹤狀態"""
    WAITING = "waiting"      # 等候中
    IN_EXAM = "in_exam"      # 檢查中
    MOVING = "moving"        # 移動中
    COMPLETED = "completed"  # 已完成


class TrackingAction(str, enum.Enum):
    """追蹤動作"""
    ARRIVE = "arrive"      # 到達
    START = "start"        # 開始檢查
    COMPLETE = "complete"  # 完成檢查
    ASSIGN = "assign"      # 指派


class PatientTracking(Base):
    """病人即時追蹤"""
    __tablename__ = "patient_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    exam_date = Column(Date, nullable=False, index=True)
    
    # 目前狀態
    current_status = Column(String(20), default=TrackingStatus.WAITING.value)
    current_location = Column(String(50), nullable=True)  # 目前位置（檢查站代碼）
    
    # 下一站
    next_exam_code = Column(String(20), nullable=True)
    
    # 更新資訊
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 關聯
    patient = relationship("Patient")
    
    def __repr__(self):
        return f"<PatientTracking {self.patient_id} @ {self.current_location}>"


class CoordinatorAssignment(Base):
    """個管師指派"""
    __tablename__ = "coordinator_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    coordinator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    exam_date = Column(Date, nullable=False, index=True)
    
    # 指派資訊
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    
    is_active = Column(Boolean, default=True)
    
    # 關聯
    patient = relationship("Patient", foreign_keys=[patient_id])
    coordinator = relationship("User", foreign_keys=[coordinator_id])
    
    def __repr__(self):
        return f"<CoordinatorAssignment {self.patient_id} -> {self.coordinator_id}>"


class TrackingHistory(Base):
    """追蹤歷程記錄"""
    __tablename__ = "tracking_history"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    exam_date = Column(Date, nullable=False, index=True)
    
    # 動作詳情
    action = Column(String(20), nullable=False)  # arrive, start, complete, assign
    location = Column(String(50), nullable=True)
    status = Column(String(20), nullable=True)
    
    # 操作者
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 備註
    notes = Column(Text, nullable=True)
    
    # 時間戳
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 關聯
    patient = relationship("Patient")
    operator = relationship("User")
    
    def __repr__(self):
        return f"<TrackingHistory {self.action} @ {self.timestamp}>"
